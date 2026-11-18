# Xray local shutdown observations (core, listeners, tun2socks, TUN owner)

This narrowly hardens **legacy Xray local Stop Success and in-process restart**
without introducing an authoritative cross-process native completion receipt.

## Previously

`V2RayServiceManager.stopV2rayPoint()` observed that `stopLoop()`
returned and that the Xray core was no longer running, then reported
`MSG_STATE_STOP_SUCCESS`. The optional `backServ` fragmentor's HTTPS and
TLS listener stop methods request socket closure but do not await their
listener `Thread` objects' exit. The stop methods also swallow internal
exceptions. A lingering listener could still own a listening socket during
a replacement start.

## Local exit observation

- The asynchronous IO teardown still requests native Xray `stopLoop()`.
- `backServ.stopAndAwaitListeners()` asks **both** optional listener services
  to stop before waiting for listener threads to exit.
- `FragmentorListenerExit.allExitedWithin()` requires observed listener
  thread termination. Both TLS and optional HTTPS fragmentors also register
  every accepted-client upstream/downstream Java Thread in an instance-local
  `FragmentorForwardingWorkers` gate before starting it. The gate retains
  client/backend sockets; Stop rejects new workers and closes registered
  sockets to unblock I/O. A backend arriving after Stop is closed immediately.
- `backServ.stopAndAwaitListeners()` now requires **both listener exit and all
  per-client forwarding Thread exits**. It uses one shared three-second
  deadline for the listener and worker observations. Invalid/unbounded waits,
  self-joins, timed-out workers and interrupted waits cannot prove completion.
  Optional DoH fragmentor worker evidence is included when that disabled
  configuration becomes available.
- If the native core did not confirm its non-running state, or any listener or
  forwarding worker remains alive, Xray does not report local Stop Success.
  `CoreStopGate` retains its failed-stop quarantine, preventing new starts.
- A fragmentor whose listener exit was not observed remains referenced in the
  manager instead of losing the only handle. The incomplete-teardown path
  also avoids announcing `MSG_STATE_NOT_RUNNING` when the core itself has
  stopped but a listener may still own resources.
- The Xray VPN service now accounts for **every** native tun2socks subprocess
  before adoption, including children created after a Stop raced
  `ProcessBuilder.start()`. `TunnelProcessExitTracker` tracks launches in
  flight and each exact child identity. The existing child watcher only
  marks completion when its blocking `Process.waitFor()` actually returns.
  A call to `destroy()` is not considered an exit.
- `onDestroy()`, `onRevoke()` and explicit Stop request termination
  without joining the subprocess on the Android lifecycle thread. The
  manager's IO cleanup waits at most three seconds for **all** tracked
  subprocesses and pending launches to exit. If this cannot be established,
  it withholds local Stop Success and PR #51's `CoreStopGate` remains
  quarantined. A proxy-only service does not own the tun2socks child;
  an unknown service owner cannot supply affirmative child-exit evidence.
- Because Android's timed `Process.waitFor(timeout, unit)`,
  `isAlive()` and `destroyForcibly()` were introduced at API 26,
  the implementation uses only `Process.waitFor()` on a dedicated
  watcher, plus a bounded observer on the existing IO cleanup coroutine,
  for compatibility with the app's lower supported Android API levels.

- The Xray VPN service now also tracks its **owned TUN
  `ParcelFileDescriptor` objects** by identity using
  `TunDescriptorCloseTracker`. It reserves every `Builder.establish()`
  operation **before** attempting it. A descriptor returned after Stop is
  recorded but cannot be published as the active VPN interface; the late
  descriptor must still be closed successfully.
- Replacing a TUN closes its previous descriptor before publishing the
  replacement. A close failure is retained as pending ownership and prevents
  local Stop Success. `onDestroy()`, forced Stop and the manager's IO teardown
  request closure of all tracked descriptors. Only a successfully returned
  `ParcelFileDescriptor.close()` removes a descriptor from the outstanding
  set. The manager waits up to three seconds for closure and all in-flight
  establishments, separately from waiting for the tun2socks child to exit.
- The existing `stopSelf()`-before-TUN-close ordering is preserved in forced
  Stop. A proxy-only service has no VPN TUN and cannot substitute a success
  claim for an unknown VPN owner.

## Trust and recovery boundaries

**Not a VPN-session native receipt.** Observed tun2socks child exit,
fragmentor listener and forwarding-worker exit, and successful close of the Java-owned VPN TUN
`ParcelFileDescriptor` do *not* prove that every per-client forwarding
thread stopped, all socket or duplicated native FD aliases were released,
the kernel VPN packet path was safely terminated, or same-generation Psiphon
native shutdown was acknowledged. The trackers belong to one Android service
instance, **not** an authoritative cross-process VPN session generation.

These observations MUST NOT be used as a complete
`VpnNativeStopEvidence` receipt or as authority to release a persisted
`VpnSessionRecordStore` member. The live cross-process coordinator remains
unwired. The lockout after unverified cleanup is intentionally conservative:
a future separately reviewed native-recovery path must prove all resources
are released, not simply wait for a TTL or trust an Android `stopService()`
request.

Pure Kotlin/JUnit covers timeout, listener/forwarder and subprocess exit,
late forwarding sockets, TUN-establishment races, failed descriptor closure,
and interruption. Python contracts check the live source ordering and the
fail-closed local Stop Success gate. GitHub Android 35 emulator CI checks build
compatibility and debug two-process fencing, **not** physical Xray teardown,
VPN packet routing, or Wi-Fi/cellular handover.

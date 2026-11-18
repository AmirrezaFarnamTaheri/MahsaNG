# Xray local fragmentor listener shutdown evidence

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
- `FragmentorListenerExit.allExitedWithin()` requires observed thread
  termination under one bounded timeout (3 seconds in production). It rejects
  invalid or unbounded timeouts, self-joins and interrupted waits.
- If the native core did not confirm its non-running state **or** an optional
  fragmentor listener remains alive, Xray does not report local Stop Success.
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

## Trust and recovery boundaries

**Not a VPN-session native receipt.** An observed tun2socks child exit and
fragmentor listener exits do *not* prove that every per-client forwarding
thread stopped, all sockets closed, the VPN TUN file descriptor was closed,
or a same-generation Psiphon process acknowledged native shutdown.
The local tracker is tied to one Android service instance, **not** an
authoritative cross-process VPN session generation.

These observations MUST NOT be used as a complete
`VpnNativeStopEvidence` receipt or as authority to release a persisted
`VpnSessionRecordStore` member. The live cross-process coordinator remains
unwired. The lockout after unverified cleanup is intentionally conservative:
a future separately reviewed native-recovery path must prove all resources
are released, not simply wait for a TTL or trust an Android `stopService()`
request.

Pure Kotlin/JUnit covers timeout, multiple listeners, process-launch races,
interruption and actual child-exit accounting. Python source contracts check
live Stop Success ordering, retained uncertainty and API compatibility. GitHub Android 35 emulator CI checks build
compatibility and debug two-process fencing, **not** physical Xray teardown,
VPN packet routing, or Wi-Fi/cellular handover.

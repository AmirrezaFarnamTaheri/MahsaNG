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

## Trust and recovery boundaries

**Not a VPN-session native receipt.** Listener thread exit does *not* prove
that per-client forwarding threads stopped, all sockets are closed, the
Android tun2socks child exited, a TUN file descriptor was closed, or
a same-generation Psiphon process acknowledged shutdown.

These observations MUST NOT be used as `VpnStopCommandGate`'s
`nativeStopped = true` value or as authority to release a persisted
`VpnSessionRecordStore` member. The live cross-process coordinator remains
unwired. The lockout after unverified cleanup is intentionally conservative:
a future separately reviewed native-recovery path must prove all resources
are released, not simply wait for a TTL or trust an Android `stopService()`
request.

Pure Kotlin/JUnit covers timeout, multiple listeners, interrupts and
non-running threads. Python source contracts check live Stop Success ordering
and retained uncertainty. GitHub Android 35 emulator CI checks build
compatibility and debug two-process fencing, **not** physical Xray teardown,
VPN packet routing, or Wi-Fi/cellular handover.

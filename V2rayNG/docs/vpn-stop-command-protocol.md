# Generation-fenced Stop command protocol (QA only)

This is an **unwired protocol contract** for a future replacement of the
shared `MSG_STATE_STOP` broadcast. Today both `V2RayServiceManager` and
`PsiphonVpnService` consume that data-less broadcast independently; a local
Xray-only check cannot prevent a delayed Psiphon stop. **Do not enable the
new protocol in production yet.** PRs #45 and #46 provided the session policy
and an isolated native-MMKV record transaction, and #47 guarded Psiphon's own
notification Stop action.

## Proposed coordinator sequence

1. A trusted controller uses a dedicated, versioned, durable cross-process
   record, validated and updated under the native MMKV lock, to issue an
   opaque session ID and a monotonic generation **before** launching either
   engine. Persisted data must never be implicitly bootstrapped by a missing,
   malformed or locked record.
2. Each participant validates the exact ID/generation before attaching and
   starting its native work. Chained mode requires separate Xray and Psiphon
   roles. The legacy proxy-only mode must be explicitly modeled before
   migration (the current policy has only VPN modes).
3. The controller encodes `VpnStopCommand(sessionId, generation)` with the
   canonical `v1|ID|GENERATION` codec and atomically applies
   `VpnStopCommandGate.requestStop()` inside
   `VpnSessionRecordStore.apply()` **before** dispatching any Stop intent.
   Missing or corrupt records and stale/ambiguous commands fail closed.
4. Each service re-reads the authoritative STOPPING record under the native
   lease. `mayStopNative(snapshot, command, itsRole)` requires a matching
   session, generation and attached role. An old broadcast, unowned role or
   misordered start/stop callback cannot authorize native shutdown.
5. Once an authorized participant has **actually** completed native shutdown,
   it can submit `acknowledgeStopped(..., nativeStopped = true)` as another
   atomic MMKV transaction. Failure, timeout, uncertainty or interrupted
   shutdown must retain the participant in STOPPING. The next session cannot
   begin until the last member has released.
6. On service/process death, a stale membership cannot expire by wall-clock
   time. A separately reviewed controller must confirm the old TUN, native
   workers and sockets are gone before any recovery transition clears a
   stranded STOPPING record. Tokens are *fencing identifiers*, not secrets or
   origin authentication; Android IPC must be private/permission restricted.

## Native acknowledgement prerequisites

The `nativeStopped` flag is **only an API contract**. Do not infer true from
a returned Android `stopService()`, an inactive notification, a PID change
or a 3-second `Thread.join()`. Real integration requires all of the
following for the right generation:

- Xray: successful `stopLoop()` completion and native core no longer running;
  all owned tun2socks and fragmentor workers fully terminated and descriptors
  closed, plus the correct service owner's foreground lifecycle.
- Psiphon: the JNI tun2socks worker has actually exited, Psiphon tunnel
  shutdown succeeded, the VPN TUN was closed, and its same-generation Xray
  proxy dependency has stopped (or has a separate pending acknowledgement).
- Cross-process: scoped start/stop intents must carry the same generation
  and be directed to the correct private recipients. The present
  global `MSG_STATE_STOP` broadcast, existing app UI Stop, Android
  `onRevoke()`, notifications and Android sticky service restarts all need
  a jointly reviewed migration and failure-path design.
- Verify against actual processes, worker crashes, late broadcasts,
  duplicate commands, native shutdown failures and controller death,
  then complete physical Wi-Fi/cellular VPN and packet-path QA.

## What CI verifies today

`VpnStopCommandGateTest` runs on the real pure Kotlin/JUnit build. The
`test-vpn-stop-command-emulator.sh` gate runs in two **debug QA** Android
processes and a **disposable** `VPN_SESSION_FENCE_DEBUG_QA_V1` MMKV namespace.
The shell's `--ez complete true` value is a **simulated assertion**, not a JNI
or VPN-engine receipt. The test proves policy wiring and shared-record
observability only. The production Xray and Psiphon services remain unchanged.

The Android emulator smoke and Python contracts must not be described as
physical-device handover, leak-safety verification, zero dropped packets,
native termination proof or complete cross-process VPN ownership.

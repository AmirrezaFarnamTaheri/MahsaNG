# VPN session fencing protocol — policy only (not live)

The pure Kotlin `VpnSessionFence` model defines an **unwired** lifecycle for a future
cross-process VPN coordinator. Xray's normal VPN service and the experimental
Psiphon-via-Xray mode use separate Android processes; in-process
`V2RayServiceManager.serviceControl` checks do not establish shared ownership.

**Do not use this helper directly from live Android services.** It does not
persist state, lock other processes, issue Android intents, own a TUN, prove
network routing, recover crashed workers, or acknowledge native shutdown.
Existing transport/proxy behavior is unchanged.

## State and actors

Each snapshot carries a monotonically increasing `generation`, an opaque
`sessionId`, the requested mode, a phase, and attached member roles.

- `IDLE`: no session token or attached roles; retains the last generation.
- `STARTING`: the controller issued a token, and required members are joining.
- `ACTIVE`: all roles for that mode have attached. This means **membership
  only**, not verified packet routing or tunnel readiness.
- `STOPPING`: stop has been requested; membership persists until every attached
  member has completed native teardown.

`XRAY_VPN` requires `XRAY`. `PSIPHON_VIA_XRAY` requires both `XRAY`
and `PSIPHON`, in either join order. Standalone proxy-only mode is deliberately
outside this initial VPN policy.

`begin` refuses overlapping sessions and increments the generation;
`attach`, `stop` and `release` require both the matching token and
generation. A duplicate attach is rejected. A repeated stop is idempotent.
No participant may release its role unless the session is `STOPPING`; an
unattached session can stop directly to `IDLE`. Old callbacks cannot act on
a replacement, even if an opaque token is accidentally reused at a different
generation. Invalid state and generation overflow fail closed.

## Required before integration

1. **Atomic persistence:** implement one authoritative, dedicated cross-process
   MMKV record with an explicit schema/version, native inter-process lock and
   read-modify-write inside a single critical section. Use
   `MMKV.MULTI_PROCESS_MODE`, check every read/write, and release in `finally`.
   A missing, corrupt or locked record must not silently become `IDLE` or
   authorize a new session. Verify fencing using *separate Android process*
   instrumentation, not two objects in a single JVM.
2. **Controller-issued generation:** the app controller must generate a fresh
   opaque ID and persist the new generation *before* launching services. Send
   the same ID/generation and expected role with each explicit start/stop
   request. A delayed old start must not claim the new session; a stale Psiphon
   `stopService` must not terminate a successor Xray proxy.
3. **Native completion boundary:** attach before starting native work, block
   new work once STOPPING begins, and release only after verified TUN close,
   native Xray `stopLoop` completion and (for Psiphon) JNI worker / tunnel
   shutdown. If stopping fails, retain STOPPING rather than declaring
   ownership free. Do not treat a connected UI message or daemon PID as
   proof of packet forwarding.
4. **Crash recovery:** process death can leave a persisted participant.
   No TTL or time-of-day based automatic takeover is permitted. A trusted
   controller must confirm the old Android VPN/TUN/native workers are gone
   before a separately reviewed recovery transition can clear the fence.
5. **Privacy and threat boundary:** session IDs are fencing identifiers, not
   authentication credentials. Keep internal messages non-exported or
   permission restricted. Do not log session identifiers, proxy profiles,
   network endpoints or VPN configuration.
6. **Validation:** add real Android two-process fencing tests with concurrent
   start/stop and deliberately delayed old callbacks; exercise forced revoke,
   worker crash, start failure and stop failure. Run the existing
   [physical handover QA](../pure-tests/PHYSICAL_HANDOVER_QA.md) on a real
   handset in both VPN modes and separately verify the actual routed packet
   path, fail-closed behavior and leak safety before enabling integration.

The 12 `VpnSessionFenceTest` JUnit tests exercise the **pure transition
policy only**. A passing build and the Android-35 emulator smoke test do not
establish a functioning cross-process VPN session coordinator.

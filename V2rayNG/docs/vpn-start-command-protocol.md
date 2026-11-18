# Controller-issued VPN Start envelopes — preparatory policy (not live)

This candidate introduces a **pure Kotlin reservation policy** for Start
commands that a future trusted controller may send to Xray and Psiphon. It
builds on `VpnSessionFence` and the locked `VpnSessionRecordStore` from merged
PRs #45–#46, and complements the Stop policy added in PR #48. It **does not**
change the running Android services, send real intents, initialize MMKV, or
start JNI/TUN workers.

## Wire contract

`VpnStartCommand(sessionId, generation, mode, role)` encodes as:

`v1.SESSION_ID.GENERATION.MODE.ROLE`

The version and enums must be exact. IDs are canonical ASCII identifiers of
32–80 characters; generations are positive, canonical decimal `Long` values.
Malformed, overlong, mixed-mode, unsupported role, unknown version, and
noncanonical encodings fail closed. Neither Start nor Stop command IDs are
authentication credentials; Android delivery must use a private or restricted
IPC channel.

`XRAY_VPN` accepts only the `XRAY` participant. `PSIPHON_VIA_XRAY` requires
separate `XRAY` and `PSIPHON` reservations in either order. Proxy-only mode is
not yet represented and **must not** be silently mapped to `XRAY_VPN`.

## Required lifecycle handoff before live integration

1. The trusted controller creates the session ID and increments the
   generation **inside one atomic native-MMKV transaction**. Missing, corrupt,
   or locked records must never cause implicit first-run bootstrapping or
   replacement of a possibly active VPN.
2. Only after the controller has durably recorded `STARTING` may it dispatch
   an explicit private Start intent with the same `sessionId`, `generation`,
   `mode`, and intended `role`.
3. A recipient must decode the envelope and call
   `VpnSessionRecordStore.apply { VpnStartCommandGate.reserve(it, command) }`
   under the real cross-process lock. A rejected or unavailable transaction
   must **not** start native work. Repeated delivery of the same envelope must
   not re-run a worker.
4. Reservation only records membership; it is **not native readiness**. The
   existing `ACTIVE` phase in `VpnSessionFence` means all participants have
   attached, not that the tunnel forwards traffic. Add an independently
   verified native-start/readiness barrier and re-check the generation at
   the actual native-work boundary. A lock release followed by asynchronous
   native startup can race a Stop transition; `stillAttached()` alone is not
   a safe cross-process critical section.
5. Stop must first persist the matching generation as `STOPPING`, then issue
   role-scoped private Stop intents. Each participant's native completion
   acknowledgment must be based on actual TUN, JNI, socket and worker shutdown,
   not a Boolean supplied by an intent. An interrupted/failed stop leaves
   the participant attached and blocks a successor.
6. Process death, onRevoke, sticky restarts and legacy unscoped UI broadcasts
   require a separate comprehensive migration. No time-based automatic lease
   expiration is permitted without proving the native tunnel has stopped.

## Test boundary

`VpnStartCommandGateTest` specifies canonical wire behavior, denied stale
commands, role/mode matching, duplicate reservation, delayed starts after
STOPPING, token reuse with higher generation, and MMKV lease refusal through a
fake store. These are **pure-policy tests**. Passing them neither verifies
native Android process behavior nor qualifies the feature to be wired into
`V2RayServiceManager`, `V2RayVpnService`, or `PsiphonVpnService`.

Before any live integration, add two-process Android tests using private
commands, actual native-start/shutdown acknowledgments, crash/revoke recovery,
notification Stop compatibility and physical-device Wi-Fi/cellular handover
checks. Do not claim leak safety or a fully coordinated tunnel from unit tests.

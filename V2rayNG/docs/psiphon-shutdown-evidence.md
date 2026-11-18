# Psiphon shutdown evidence and honest Stop reporting

This change narrows **legacy local-service Stop Success** to observable
teardown results. It does **not** implement a persisted native-completion
receipt or coordinated session ownership for the two VPN engines.

## Previous risk

`PsiphonVpnService.stopAll()` sends a JNI termination signal, joins the
routing worker for up to three seconds, and previously cleared
`tun2socksThread` and reported `MSG_STATE_STOP_SUCCESS` regardless of
whether the worker had actually exited. A bounded join is a timeout,
not evidence of native termination. The immediate upstream
`stopService(V2RayProxyOnlyService)` is a request, not an Xray `stopLoop`
completion acknowledgment.

## New observed local boundary

- Termination is still requested even if JNI is missing. Failure does not
  skip Psiphon tunnel cleanup or VPN TUN closure.
- After the existing bounded join, the service checks the worker's actual
  `isAlive` state. It **retains the worker handle** if that worker is still
  alive, and its existing process-wide native lease remains occupied until
  the worker's `finally` block releases it.
- The service observes whether synchronous `PsiphonTunnel.stop()` and
  `ParcelFileDescriptor.close()` calls returned without throwing.
- `PsiphonTeardownEvidence.localStopReportable` requires all these local
  observations before the legacy `MSG_STATE_STOP_SUCCESS` message is
  emitted. Failure or uncertainty suppresses that success message. When the
  TUN was closed, the UI can receive `MSG_STATE_NOT_RUNNING` instead; this
  describes local service connectivity, **not** native worker completion.
- `wholeChainCompletionEligible` remains false in the live service:
  neither `PsiphonTunnel.stop()` returning nor a returned upstream `stopService`
  request is an independently verified native completion receipt. Both
  `psiphonNativeStopAcknowledged` and `xrayNativeStopAcknowledged` remain false.
  A future coordinator needs independent native acknowledgments for both roles.

The local policy observes synchronous results and an exited JNI thread.
It does **not** prove that all asynchronous Psiphon internals or Xray sockets
have stopped, that traffic never leaked, or that a native generation-scoped
release may be committed. In particular, `MSG_STATE_STOP_SUCCESS` remains
a legacy UI event, not an IPC-safe shutdown receipt.

## Remaining integration and release gates

A future live session coordinator must require exact session and generation
validation, native exit/worker completion, TUN ownership cleanup, and an
independent Xray `stopLoop` acknowledgment before releasing either role in
`VpnSessionRecordStore`. It must handle stopped-but-still-live JNI workers,
crash recovery, revoked VPN permissions, delayed callbacks and sticky
service restarts without clock-based takeover.

The pure Kotlin tests exercise the conservative evidence logic. Python source
contracts require the live service to check worker exit and gate its success
message. Android CI compiles and starts the app, but the emulator does not
start a live Psiphon tunnel or simulate a worker that ignores JNI termination.
A physical-device run with Wi-Fi/cellular handover and intentional JNI
shutdown failures is still required before making end-to-end guarantees.

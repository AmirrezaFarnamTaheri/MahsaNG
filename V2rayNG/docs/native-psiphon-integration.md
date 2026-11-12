# Native Psiphon/Xray AAR integration (release gate)

This application builds Xray from the pinned
[GFW-knocker/AndroidLibXrayLite commit 48f35be868ee247e53a8036e284a8c2f97c80068](https://github.com/GFW-knocker/AndroidLibXrayLite/commit/48f35be868ee247e53a8036e284a8c2f97c80068)
using Go/mobile. Its legacy `ca.psiphon.PsiphonTunnel` Java adapter explicitly requests
`System.loadLibrary("psiphon")`. Stock Psiphon Go/mobile AARs use
`libgojni.so` plus `go.Seq` runtime classes, overlapping Xray's.

The candidate is the [mahsanet/aar Psiphon NKR release
`psiphon-nkr-2026-06-21`](https://github.com/mahsanet/aar/releases/tag/psiphon-nkr-2026-06-21),
downloaded only at build time and checked against this immutable SHA-256:

```
a8eddfa98b2321793035211cfc27da0f2966f69653682aa46dbc74bfcf331086
```

The [public build workflow](https://github.com/mahsanet/aar/blob/main/.github/workflows/build-psiphon-aar.yaml)
records `GFW-knocker/psiphon-tunnel-core@nkr` and
[mahsanet/gomobile](https://github.com/mahsanet/gomobile) with
`gomobile bind -soname psiphon`.
The modified Go/mobile generator namespaces the native SONAME and Java/JNI
runtime support classes, rather than using Gradle `pickFirst` to select
one incompatible `libgojni.so`. The release metadata does not record an
exact source commit, so the checksum pins the distributed bytes, not a
reproducible source-to-binary attestation.

CI downloads the artifact into `app/libs` only after building the pinned
Xray AAR, validates its checksum, compares both AARs for duplicate classes,
colliding per-ABI native library names, missing provider interfaces and ABIs,
then performs **real** Android APK assembly and full Android module tests.
The checked-in `PsiphonTunnel.java` must not also be bundled in the AAR.

**The release remains blocked until** all build checks pass AND a device
verifies both Xray and Psiphon VPN start/stop, process isolation, lifecycle
transitions, traffic routing, DNS behavior, IPv6, API-level foreground service
requirements and no traffic leaks. A successful AAR audit alone never
establishes a working or secure tunnel.

For any update, use a reviewed source version and new checksum; do not
silently change the artifact, suppress compiler tasks, invent JNI bindings,
or force Gradle packaging overrides.

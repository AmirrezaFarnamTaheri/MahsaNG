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

## Psiphon-specific tun2socks JNI library

The V2Ray app bundles `libtun2socks.so` as a **standalone executable**.
That cannot satisfy the Java `ca.psiphon.Tun2SocksJniLoader` native methods,
which explicitly load `libtun2socks_psiphon.so`. Compiling the Java wrapper
without supplying this JNI library produced a misleadingly successful APK
whose Psiphon VPN traffic path could not start.

The workflow now obtains the **official upstream Psiphon-Inc Android source**
at immutable commit
[`c2c043da1208b34d28c3fdeef72b43dcd470dacb`](https://github.com/Psiphon-Inc/psiphon-android/commit/c2c043da1208b34d28c3fdeef72b43dcd470dacb)
(GPLv3, compatible with this repo's GPLv3 license). It builds the upstream
`app/src/main/jni/badvpn/Android.mk` with NDK 27.2. In the temporary CI
checkout, the workflow renames `LOCAL_MODULE` to `tun2socks_psiphon`
and applies the checked-in, fail-closed `pure-tests/patch_psiphon_tun2socks.py`
change to the pinned `tun2socks.c`. The patch adds a native
`prepareTun2Socks()` entry point and moves the termination-flag reset out
of the native worker's entry path, where the upstream code could erase a
concurrent stop. A process-wide worker lease prevents re-arming while a
previous worker remains alive. The test suite checks the native patch anchors
and the start/stop interleaving. Any upstream-source drift rejects the build.
It verifies exported `JNI_OnLoad`, copies the four ABI outputs into the
application build, and requires their presence in the universal APK.

This proves binary presence and symbol export, **not** that tunnel handoff,
DNS forwarding, IPv6 or device reconnect work. Complete native/physical
VPN validation and source-to-binary provenance review remain mandatory.

# Integration review — MahsaNG

This branch combines draft PRs #1–#7 into a single reviewable change based on master without modifying master.

## Conflict resolution

- `MmkvManager.kt`: PR #4 staged subscription writer plus PR #1 confirmed scoped deletion, PR #2 per-test-run result clearing, and PR #7 stable sort; measured delay updates and clears share the in-process synchronized writer lock.
- `MainActivity.kt`: PR #4 asynchronous subscription import plus PR #1 scoped deletion confirmation and PR #7 background sorting.
- All other modified paths are pinned to their corresponding individual PR head SHAs.

## Build and verification

- Gradle wrapper updated from 7.5 to 8.6 to match Android Gradle Plugin 8.4.2 (JDK 17 minimum).
- Declared SDK: compileSdk 33 and Build Tools 33.0.2; see `V2rayNG/gradle.properties`.
- Build command after restoring missing dependencies: `cd V2rayNG && ./gradlew :app:assembleDevDebug :app:testDevDebugUnitTest`.
- 42 focused pure Kotlin/JVM regression tests pass together under local `kotlinc`; they are not a full Android build.
- Full Android build **not verified**: the public repository lacks source for GFW types such as `my_preference_storage`, `config_pkg_reader`, and other referenced features. Native and SDK dependencies also require verification. Do not add guessed networking stubs.

## Mandatory QA before merging

- Restore missing sources with provenance and compatible licensing, compile the full app with JDK 17 and Android SDK, run Gradle unit/instrumented tests.
- Exercise failed/untested deletion under filters, reconnect, concurrent subscription refresh and crash/rollback paths, and native JNI cancellation.
- Device-test rapid start/stop, tun2socks restart, VPN revocation, TLS/DoH fragmentation and route correctness. No release or defaults changed.

This integration PR is intended to supersede seven independent draft PRs after review; the individual PRs remain open for auditing.

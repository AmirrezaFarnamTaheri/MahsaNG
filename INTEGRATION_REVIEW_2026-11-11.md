# MahsaNG integrated safety fixes — review and build status (2026-11-11)

This draft integrates original PRs #1–#7 plus one new GUID-based filtered reorder fix. The default `master` branch remains unchanged.

## Integrated behavior

- PR #1: explicit negative-only, scope-limited failed-profile removal with confirmation.
- PR #2: immutable test targets, native generation tokens and test-run-scoped result clearing.
- PR #3: guaranteed TCP socket cleanup on error, cancellation and normal completion.
- PR #4: stage/validate subscription replacements before retiring old profiles; coordinate in-process storage writes.
- PR #5: tun2socks native process ownership and bounded restart.
- PR #6: validated optional fragmentor lifecycle and core stop acknowledgement ordering.
- PR #7: stable sorted delay snapshot off the main thread.
- Integration-only: `MainViewModel.swapServer` delegates filtered list drag/drop to synchronized GUID-based `MmkvManager.swapServerPositions`. Previously it rewrote the full index by filtered list positions.

`MmkvManager.kt` reconciles #1/#2/#4/#7; `MainActivity.kt` reconciles #1/#4/#7 and replaces the unavailable RxPermissions dependency with AndroidX Activity Result contracts. Android's document URI access uses the picker-provided read grant.

- Duplicate removal is now confirmed and restricted to the exact visible GUIDs, keeps the active selected profile even if it appears later in an equal-outbound group, recomputes candidates at commit time, and uses a single synchronized index publication instead of O(n^2) pairwise UI comparisons and per-profile index writes. Seven isolated JUnit4 cases cover this policy (expected isolated suite total: **54**).

- TLS certificate security: corrected the preference key to the existing `pref_allow_insecure` checkbox, default off. Four imports no longer unconditionally set `allowInsecure=true`; legacy flags cannot override the user setting. Non-custom managed profiles recheck TLS and Reality bypass flags at configuration generation time, including profiles previously saved with insecure flags. Explicitly user-authored raw custom JSON is not rewritten. Seven pure JUnit tests cover the secure policy; expected isolated suite count after this change: **61** (awaiting hosted CI).

## Actual CI results (not a claimed APK build)

**54/54 isolated Kotlin/JUnit4 tests passed** in [run 42916109776](https://github.com/AmirrezaFarnamTaheri/MahsaNG/actions/runs/42916109776); the seven new TLS tests await the next run. in the GitHub-hosted `Pure Kotlin regressions (real JUnit)` job (for example, run [42913620208](https://github.com/AmirrezaFarnamTaheri/MahsaNG/actions/runs/42913620208)). This isolated test project compiles ten production helpers, but does **not** build Android services, native JNI, UI or an APK.

The GitHub-hosted `Android source build (no suppressed errors)` job advances through SDK installation, dependencies and resource processing but **fails** during Android resource linking. It is not marked optional, so the integration remains red/not release-ready.

The build preflight has already exposed and corrected:
1. Incompatible Gradle wrapper 7.5 and obsolete Java 17 `-XX:MaxPermSize`.
2. Non-executable wrapper invocation and an obsolete SDK setup-action package request.
3. An unavailable legacy `com.tbruyelle.rxpermissions:rxpermissions:0.9.4` artifact (migrated to existing AndroidX contracts).
4. Two byte-for-byte duplicate XML color definitions (kept the `res/values` copies).
5. Android 15 style attributes requiring modern compilation tools (now **AGP 8.6.1, Gradle 8.7, compileSdk 35, Build Tools 34.0.0, JDK 17**). **targetSdk remains 33**; no targeting upgrade was made.
6. Orphaned About-page reference names. A limited compatibility shim uses *existing* checked-in theme colors, the actual `ic_banner` image and explanatory vector fallbacks. This is not a restoration of unpublished artwork or translations; visual QA is mandatory.

### Current Android blocker — missing MASQUE/WARP screen resources

The last Android compilation in run [42913620208](https://github.com/AmirrezaFarnamTaheri/MahsaNG/actions/runs/42913620208) failed in `:app:processDevDebugResources`, before Kotlin compilation, because `res/layout/activity_add_masque.xml` refers to untracked resources including:

- Drawables: `bg_button_theme`, `bg_card`, `bg_edit_field`, `ic_shield_guard_filled`, `ic_key`, `ic_clipboard_filled_import`.
- Colors: `red`, `donor_link`.
- Strings: `warp_gen_new_ip`, `warp_gen_new_key`, `warp_gen_paste`, `warp_clear`, `warp_section_endpoint_keys`, `warp_ip`, `masque_gen_description`, `masque_hint_ip`.

This is an observed, non-exhaustive first batch of missing references. The authoring/layout source for this security-sensitive feature must be restored or intentionally redesigned, not filled with fake labels/icons solely for a green build.

### Additional source-provenance blocker

The tracked source still references `my_preference_storage`, `config_pkg_reader` and `GFW_client_ip`, but their definitions are absent from the fork and from the original `GFW-knocker/MahsaNG` tracked trees on `master`, `EMS` and `1.8.9`. These could cause later Java/Kotlin compilation errors once resources link. Do **not** create guessed network code or import code from an unrelated project without licensing/provenance review.

## How to reproduce

```sh
cd V2rayNG
bash ./gradlew -p pure-tests --no-daemon test
bash ./gradlew --no-daemon :app:compileDevDebugKotlin
```

Requires Android SDK platform 35, Build Tools 34.0.0 and JDK 17; Maven repositories needed for dependency resolution.

## Required before merging/release

1. Obtain the original MASQUE/WARP drawables, strings, colors and GFW source dependencies with authorship and license verification (or approve a separately designed replacement with UX and security review).
2. Run full Android compilation, APK packaging, app/instrumented tests, and manual visual review of both English/Persian layouts and RTL.
3. Device-test failed/untested deletion, selected and filtered subscriptions, process death and cross-process MMKV writers, stale JNI callbacks, native stop/start, tun2socks restart, VPN revocation and tunnel privacy.
4. Review the combined integration PR before marking it ready; never merge independent draft PRs #1–#7 and this integrated PR on top of each other without conflict reconciliation.

No claim of an Android APK or VPN-device verification has been made.

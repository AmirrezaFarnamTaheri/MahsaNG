# MahsaNG regression tests and physical-device QA

The separate `pure-tests` Gradle project compiles a curated list of pure Kotlin
production helpers from `../app/src/main/kotlin` alongside their real JUnit4
tests. It does **not** compile Android services, JNI, MMKV stores or UI classes.

```sh
cd V2rayNG
./gradlew -p pure-tests --no-daemon test
```

The repository safety workflow also runs Python source/behavior contracts and
an independent Android job that builds pinned native dependencies, assembles
the devDebug APK, runs Android module unit tests, and launches a real Android
35 emulator. This proves **app build and smoke behavior**, not a live VPN
tunnel or a physical Wi-Fi-to-cellular handover.

```sh
python3 -m unittest discover -s V2rayNG/pure-tests -p 'test_*.py'
```

Requirements for isolated JVM tests: JDK 17, the repository's Gradle wrapper,
and Maven Central access. See `build.gradle.kts` for the current helper list;
do not rely on a hard-coded count.

**Physical device handover:** see [PHYSICAL_HANDOVER_QA.md](PHYSICAL_HANDOVER_QA.md)
for the opt-in operator-run ADB gate and its limitations. The runner's fake-ADB
unit tests are part of the Python suite, but CI does not and cannot claim
live Wi-Fi/cellular tunnel validation.

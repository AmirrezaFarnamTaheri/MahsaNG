# Isolated JVM regression suite

This *separate Gradle project* compiles only ten pure Kotlin production helpers
from `../app/src/main/kotlin` and their existing corresponding JUnit4 tests.
It does not compile Android services, JNI wrappers, MMKV stores or UI classes.

```sh
cd V2rayNG
./gradlew -p pure-tests --no-daemon test
```

The root Android app is intentionally **not** a dependency. A green result here
never proves that the Android application builds. The companion GitHub Actions
job runs `./gradlew :app:compileDevDebugKotlin` independently and does **not**
suppress failures (missing GFW source files remain an explicit blocker).

Requires JDK 17, Gradle 8.6 from the wrapper, and Maven Central access on CI.
The tests run against real JUnit4 rather than an in-house imitation.

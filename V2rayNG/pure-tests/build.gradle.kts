plugins {
    kotlin("jvm") version "1.9.23"
}

repositories {
    mavenCentral()
}

kotlin {
    jvmToolchain(17)
}

val productionHelpers = listOf(
    "FailedServerSelection",
    "TestRunTracker",
    "SocketConnectTimer",
    "SubscriptionReplacementPlan",
    "TunnelProcessOwner",
    "CoreStopGate",
    "FragmentorOptions",
    "FragmentorSocketBinding",
    "ProfileDelayOrder",
    "ProfileIndexSwap",
)

sourceSets {
    main {
        kotlin.srcDir("../app/src/main/kotlin")
        kotlin.include(productionHelpers.map { "**/${it}.kt" })
    }
    test {
        kotlin.srcDir("../app/src/test/kotlin")
        kotlin.include(productionHelpers.map { "**/${it}Test.kt" })
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    useJUnit()
    testLogging {
        events("passed", "skipped", "failed")
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
}

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
    "LocalSubscriptionSelection",
    "SubscriptionItem",
    "wget_module",
    "SafeAssetFilename",
    "PortAndFragmentInput",
    "ServerEditorInputRules",
    "TestRunTracker",
    "SocketConnectTimer",
    "SubscriptionReplacementPlan",
    "TunnelProcessOwner",
    "CoreStopGate",
    "PsiphonStartGate",
    "PsiphonRouteGate",
    "FragmentorOptions",
    "FragmentorNumericSettings",
    "EConfigType",
    "GfwPreferenceArrayCodec",
    "GFW_client_ip",
    "StringWhitespace",
    "FragmentorSocketBinding",
    "ProfileDelayOrder",
    "ProfileIndexSwap",
    "DuplicateProfileSelection",
    "TlsCertificatePolicy",
)

sourceSets {
    main {
        kotlin.srcDir("../app/src/main/kotlin")
        kotlin.include(*productionHelpers.map { "**/${it}.kt" }.toTypedArray())
    }
    test {
        kotlin.srcDir("../app/src/test/kotlin")
        kotlin.include(*productionHelpers.map { "**/${it}Test.kt" }.toTypedArray())
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

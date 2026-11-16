package com.v2ray.ang.util

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.Proxy
import java.net.URL
import java.nio.file.Files

class AppFetchFileDownloaderTest {
    private val dir = Files.createTempDirectory("mahsa-fetch-test").toFile()

    @After fun cleanUp() {
        dir.deleteRecursively()
    }

    private class Response(code: Int, private val payload: ByteArray) :
        HttpURLConnection(URL("https://example.test/asset")) {
        var disconnected = false
        init { responseCode = code }
        override fun connect() = Unit
        override fun disconnect() { disconnected = true }
        override fun usingProxy(): Boolean = false
        override fun getInputStream(): InputStream = ByteArrayInputStream(payload)
    }

    @Test fun failedStatusPreservesExistingAssetAndRemovesStagingFile() {
        val target = dir.resolve("geoip.dat").apply { writeText("old") }
        val connection = Response(404, "not found".toByteArray())
        val saved = AppFetchFileDownloader.download(
            URL("https://example.test/geoip.dat"),
            target,
            AppFetchRoutePolicy.Route.ViaProxy(10809),
            openConnection = { _, _ -> connection },
        )
        assertFalse(saved)
        assertEquals("old", target.readText())
        assertTrue(connection.disconnected)
        assertEquals(listOf("geoip.dat"), dir.listFiles().orEmpty().map { it.name })
    }

    @Test fun successfulProxyDownloadReplacesTarget() {
        val target = dir.resolve("geoip.dat").apply { writeText("old") }
        val connection = Response(200, "new".toByteArray())
        var chosenProxy: Proxy? = null
        val saved = AppFetchFileDownloader.download(
            URL("https://example.test/geoip.dat"),
            target,
            AppFetchRoutePolicy.Route.ViaProxy(10809),
            openConnection = { _, proxy -> chosenProxy = proxy; connection },
        )
        assertTrue(saved)
        assertEquals("new", target.readText())
        assertEquals(Proxy.Type.HTTP, chosenProxy?.type())
        assertTrue(connection.disconnected)
    }

    @Test fun zeroLengthResponseCannotOverwriteExistingTarget() {
        val target = dir.resolve("geoip.dat").apply { writeText("old") }
        val saved = AppFetchFileDownloader.download(
            URL("https://example.test/geoip.dat"),
            target,
            AppFetchRoutePolicy.Route.Direct,
            openConnection = { _, _ -> Response(200, byteArrayOf()) },
        )
        assertFalse(saved)
        assertEquals("old", target.readText())
    }

    @Test fun failedProxyAttemptNeverOpensDirectConnection() {
        val target = dir.resolve("geoip.dat")
        var connections = 0
        val saved = AppFetchFileDownloader.download(
            URL("https://example.test/geoip.dat"),
            target,
            AppFetchRoutePolicy.Route.ViaProxy(10809),
            openConnection = { _, proxy ->
                connections += 1
                if (proxy.type() == Proxy.Type.DIRECT) error("Unexpected direct fallback")
                throw IOException("unreachable local proxy")
            },
        )
        assertFalse(saved)
        assertEquals(1, connections)
        assertFalse(target.exists())
    }

    @Test fun blockedRequestPerformsZeroNetworkOperations() {
        var contacted = false
        val saved = AppFetchFileDownloader.download(
            URL("https://example.test/geoip.dat"),
            dir.resolve("geoip.dat"),
            AppFetchRoutePolicy.Route.Blocked,
            openConnection = { _, _ ->
                contacted = true
                throw IOException("should not connect")
            },
        )
        assertFalse(saved)
        assertFalse(contacted)
    }
}

package com.v2ray.ang.gfwknocker

import java.io.ByteArrayInputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class wget_moduleTest {
    private class FakeConnection(
        url: URL,
        private val code: Int,
        private val text: String = "announcement",
        private val location: String? = null,
        private val throwOnBody: Boolean = false,
    ) : HttpURLConnection(url) {
        var disconnected = false
        override fun getResponseCode() = code
        override fun getInputStream(): ByteArrayInputStream {
            if (throwOnBody) throw IOException("unavailable")
            return ByteArrayInputStream(text.toByteArray(Charsets.UTF_8))
        }
        override fun getHeaderField(name: String?): String? =
            if (name.equals("Location", ignoreCase = true)) location else null
        override fun connect() = Unit
        override fun disconnect() { disconnected = true }
        override fun usingProxy() = false
    }

    @Test fun rejectsPlainHttpWithoutOpeningConnection() {
        var opened = false
        assertNull(wget_module.fetch("http://example.com/news") {
            opened = true
            FakeConnection(it, 200)
        })
        assertTrue(!opened)
    }

    @Test fun rejectsCredentialsOrFragmentsInAnnouncementUrl() {
        var opened = false
        for (url in listOf("https://user:password@example.com/help", "https://example.com/help#fragment")) {
            assertNull(wget_module.fetch(url) { opened = true; FakeConnection(it, 200) })
        }
        assertTrue(!opened)
    }

    @Test fun readsHttpsTextAndAlwaysDisconnects() {
        val connection = FakeConnection(URL("https://example.com/info"), 200, "Hello VPN")
        assertEquals("Hello VPN", wget_module.fetch("https://example.com/info") { connection })
        assertTrue(connection.disconnected)
    }

    @Test fun rejectsRedirectToUnencryptedHttp() {
        val connection = FakeConnection(
            URL("https://example.com/start"), 302, location = "http://example.com/unsafe"
        )
        assertNull(wget_module.fetch("https://example.com/start") { connection })
        assertTrue(connection.disconnected)
    }

    @Test fun followsRelativeHttpsRedirectWithinLimit() {
        val requested = mutableListOf<String>()
        val result = wget_module.fetch("https://example.com/start") { url ->
            requested.add(url.toString())
            if (requested.size == 1) FakeConnection(url, 302, location = "/new")
            else FakeConnection(url, 200, "updated")
        }
        assertEquals("updated", result)
        assertEquals(listOf("https://example.com/start", "https://example.com/new"), requested)
    }

    @Test fun refusesOversizedAnnouncementEvenWhenContentLengthUnknown() {
        val connection = FakeConnection(URL("https://example.com/info"), 200, "x".repeat(262145))
        assertNull(wget_module.fetch("https://example.com/info") { connection })
        assertTrue(connection.disconnected)
    }

    @Test fun refusesFailedResponsesAndBodyReadErrors() {
        val missing = FakeConnection(URL("https://example.com/404"), 404)
        val broken = FakeConnection(URL("https://example.com/broken"), 200, throwOnBody = true)
        assertNull(wget_module.fetch("https://example.com/404") { missing })
        assertNull(wget_module.fetch("https://example.com/broken") { broken })
        assertTrue(missing.disconnected && broken.disconnected)
    }

    @Test fun boundsRedirectChains() {
        var opened = 0
        assertNull(wget_module.fetch("https://example.com/start") { url ->
            opened++
            FakeConnection(url, 302, location = "/another")
        })
        assertEquals(4, opened)
    }
}

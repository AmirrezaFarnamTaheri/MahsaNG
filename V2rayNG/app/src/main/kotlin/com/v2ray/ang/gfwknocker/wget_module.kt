package com.v2ray.ang.gfwknocker

import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL

/**
 * Fetch bounded HTTPS announcement text using Android's system networking.
 * A running VPN is applied by the OS; no certificate-bypass or private proxy
 * is introduced. Kept named for compatibility with the existing Java UI.
 */
object wget_module {
    private const val MAX_ANNOUNCEMENT_BYTES = 256 * 1024

    @JvmStatic
    fun auto_routed_fetch_remote_text(url: String): String = fetch(url).orEmpty()

    internal fun fetch(
        rawUrl: String,
        open: (URL) -> HttpURLConnection = { it.openConnection() as HttpURLConnection },
    ): String? {
        var uri = secureUri(rawUrl) ?: return null
        for (redirectCount in 0..3) {
            val connection = try { open(uri.toURL()) } catch (_: Exception) { return null }
            try {
                connection.connectTimeout = 7000
                connection.readTimeout = 10000
                connection.instanceFollowRedirects = false
                connection.useCaches = false
                val status = connection.responseCode
                if (status in listOf(301, 302, 303, 307, 308)) {
                    if (redirectCount == 3) return null
                    val location = connection.getHeaderField("Location") ?: return null
                    uri = secureUri(uri.resolve(location).toString()) ?: return null
                    continue
                }
                if (status !in 200..299) return null
                if (connection.contentLengthLong > MAX_ANNOUNCEMENT_BYTES) return null
                val result = ByteArrayOutputStream()
                connection.inputStream.use { input ->
                    val chunk = ByteArray(8192)
                    while (true) {
                        val count = input.read(chunk)
                        if (count < 0) break
                        if (result.size() + count > MAX_ANNOUNCEMENT_BYTES) return null
                        result.write(chunk, 0, count)
                    }
                }
                return result.toString(Charsets.UTF_8.name())
            } catch (_: Exception) {
                return null
            } finally {
                connection.disconnect()
            }
        }
        return null
    }

    private fun secureUri(raw: String): URI? = try {
        val uri = URI(raw.trim())
        if (!uri.scheme.equals("https", ignoreCase = true) ||
            uri.host.isNullOrBlank() || uri.userInfo != null || uri.fragment != null ||
            uri.port > 65535 || uri.port == 0) null else uri
    } catch (_: Exception) { null }
}

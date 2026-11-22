package com.v2ray.ang.util

import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.InetSocketAddress
import java.net.Proxy
import java.net.URL

/**
 * Download an app-owned asset via one explicitly chosen route.
 * HTTP failures, redirects to unsupported schemes, oversized responses, and
 * incomplete downloads must not replace a working asset.
 */
object AppFetchFileDownloader {
    const val DEFAULT_MAX_BYTES = 128L * 1024L * 1024L
    private const val MAX_REDIRECTS = 5

    fun download(
        url: URL,
        target: File,
        route: AppFetchRoutePolicy.Route,
        timeoutMs: Int = 60_000,
        maxBytes: Long = DEFAULT_MAX_BYTES,
        openConnection: (URL, Proxy) -> HttpURLConnection = { source, proxy ->
            source.openConnection(proxy) as HttpURLConnection
        },
    ): Boolean {
        if (url.protocol != "http" && url.protocol != "https") return false
        if (timeoutMs !in 1..120_000 || maxBytes <= 0L) return false
        val parent = target.absoluteFile.parentFile?.takeIf { it.isDirectory } ?: return false

        var connection: HttpURLConnection? = null
        var staging: File? = null
        try {
            var currentUrl = url
            for (hop in 0..MAX_REDIRECTS) {
                connection?.disconnect()
                connection = AppFetchRoutePolicy.dispatch(
                    route = route,
                    direct = { openConnection(currentUrl, Proxy.NO_PROXY) },
                    viaProxy = { port ->
                        openConnection(
                            currentUrl,
                            Proxy(Proxy.Type.HTTP, InetSocketAddress("127.0.0.1", port)),
                        )
                    },
                )
                connection.connectTimeout = timeoutMs
                connection.readTimeout = timeoutMs
                connection.instanceFollowRedirects = false
                connection.useCaches = false
                val code = connection.responseCode
                if (code in listOf(301, 302, 303, 307, 308)) {
                    if (hop == MAX_REDIRECTS) return false
                    val location = connection.getHeaderField("Location") ?: return false
                    val next = URL(currentUrl, location)
                    if (next.protocol != "http" && next.protocol != "https") return false
                    // Never silently downgrade an HTTPS asset download to plain HTTP.
                    if (currentUrl.protocol == "https" && next.protocol != "https") return false
                    currentUrl = next
                    continue
                }
                if (code != HttpURLConnection.HTTP_OK) return false
                break
            }

            val active = connection ?: return false
            if (active.contentLength > maxBytes) return false

            val temporary = File.createTempFile("${target.name}.", ".download", parent)
            staging = temporary
            var total = 0L
            active.inputStream.use { input ->
                FileOutputStream(temporary).use { output ->
                    val buffer = ByteArray(16 * 1024)
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        if (read == 0) continue
                        total += read
                        if (total > maxBytes) return false
                        output.write(buffer, 0, read)
                    }
                }
            }
            if (total <= 0L || temporary.length() == 0L) return false
            if (temporary.renameTo(target)) return true
            // On POSIX/Android, same-directory renameTo atomically replaces target.
            // On Windows JVM tests, renameTo fails when target exists.
            return target.exists() && target.delete() && temporary.renameTo(target)
        } catch (_: Exception) {
            // Never log the remote URL: it may contain embedded credentials.
            return false
        } finally {
            connection?.disconnect()
            staging?.delete()
        }
    }
}

package com.v2ray.ang.util

import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.InetSocketAddress
import java.net.Proxy
import java.net.URL

/**
 * Download an app-owned asset via one explicitly chosen route.
 * HTTP failures and incomplete downloads must not replace a working asset.
 */
object AppFetchFileDownloader {
    fun download(
        url: URL,
        target: File,
        route: AppFetchRoutePolicy.Route,
        timeoutMs: Int = 60_000,
        openConnection: (URL, Proxy) -> HttpURLConnection = { source, proxy ->
            source.openConnection(proxy) as HttpURLConnection
        },
    ): Boolean {
        if (url.protocol != "http" && url.protocol != "https") return false
        if (timeoutMs !in 1..120_000) return false
        val parent = target.absoluteFile.parentFile?.takeIf { it.isDirectory } ?: return false

        var connection: HttpURLConnection? = null
        var staging: File? = null
        try {
            connection = AppFetchRoutePolicy.dispatch(
                route = route,
                direct = { openConnection(url, Proxy.NO_PROXY) },
                viaProxy = { port ->
                    openConnection(url, Proxy(Proxy.Type.HTTP, InetSocketAddress("127.0.0.1", port)))
                },
            )
            connection.connectTimeout = timeoutMs
            connection.readTimeout = timeoutMs
            connection.useCaches = false
            if (connection.responseCode != HttpURLConnection.HTTP_OK) return false

            val temporary = File.createTempFile("${target.name}.", ".download", parent)
            staging = temporary
            connection.inputStream.use { input ->
                FileOutputStream(temporary).use { output -> input.copyTo(output) }
            }
            if (temporary.length() == 0L) return false
            return temporary.renameTo(target)
        } catch (_: Exception) {
            // Never log the remote URL: it may contain embedded credentials.
            return false
        } finally {
            connection?.disconnect()
            staging?.delete()
        }
    }
}

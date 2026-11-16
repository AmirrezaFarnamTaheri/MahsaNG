package com.v2ray.ang.util

import java.io.IOException

/** Where one app-owned HTTP request may leave the device. Never retry a failed proxy request directly. */
internal object AppFetchRoutePolicy {
    enum class Trigger { USER, BACKGROUND }

    sealed interface Route {
        data class ViaProxy(val port: Int) : Route
        object Direct : Route
        object Blocked : Route
    }

    /** A user-triggered offline import can bootstrap without a tunnel. Background work cannot. */
    fun choose(proxyExpected: Boolean, configuredHttpPort: Int?, trigger: Trigger): Route {
        if (proxyExpected) {
            val port = configuredHttpPort?.takeIf { it in 1..65535 }
            return if (port != null) Route.ViaProxy(port) else Route.Blocked
        }
        return if (trigger == Trigger.USER) Route.Direct else Route.Blocked
    }

    /** Deliberately makes only one connection attempt; a proxy error must propagate unchanged. */
    @Throws(IOException::class)
    fun <T> dispatch(route: Route, direct: () -> T, viaProxy: (Int) -> T): T = when (route) {
        Route.Direct -> direct()
        is Route.ViaProxy -> viaProxy(route.port)
        Route.Blocked -> throw IOException("No permitted route for app-owned request")
    }
}

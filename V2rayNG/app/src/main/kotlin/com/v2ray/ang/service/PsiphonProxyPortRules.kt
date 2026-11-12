package com.v2ray.ang.service

data class PsiphonProxyPorts(val socks: Int, val http: Int)

/** Port zero lets Psiphon allocate a free local port. */
object PsiphonProxyPortRules {
    @JvmStatic
    fun isValid(socks: String?, http: String?): Boolean = parse(socks, http) != null

    fun parse(socks: String?, http: String?): PsiphonProxyPorts? {
        val s = socks?.trim()?.toIntOrNull() ?: return null
        val h = http?.trim()?.toIntOrNull() ?: return null
        if (s !in 0..65534 || h !in 0..65534) return null
        if (s != 0 && s == h) return null
        if (s == 10808 || s == 10809 || h == 10808 || h == 10809) return null
        return PsiphonProxyPorts(s, h)
    }
}

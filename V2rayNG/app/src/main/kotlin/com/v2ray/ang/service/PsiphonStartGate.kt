package com.v2ray.ang.service

/** Prevents duplicate VPN startups and invalidates workers on stop/revoke. */
internal class PsiphonStartGate {
    private var epoch = 0L
    private var active = false

    @Synchronized fun beginStart(): Long? {
        if (active) return null
        epoch += 1
        active = true
        return epoch
    }

    @Synchronized fun isCurrent(token: Long): Boolean = active && epoch == token

    @Synchronized fun isActive(): Boolean = active

    @Synchronized fun stop() {
        epoch += 1
        active = false
    }
}

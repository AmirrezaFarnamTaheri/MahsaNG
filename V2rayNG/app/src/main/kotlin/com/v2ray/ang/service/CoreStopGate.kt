package com.v2ray.ang.service

/** A short, synchronized gate around asynchronous native shutdown. */
internal class CoreStopGate {
    private var revision = 0L
    private var stopping = false
    private var activeStop: Long? = null
    private var pendingStart = false

    @Synchronized
    fun requestStart(): Boolean {
        if (!stopping) return true
        pendingStart = true
        return false
    }

    /** Returns a stop token only to the caller responsible for starting native cleanup. */
    @Synchronized
    fun beginStop(): Long? {
        // Duplicate native shutdown callbacks are idempotent. Only the first
        // stop may invalidate the previous session or its pending start.
        if (stopping) return null
        revision++
        pendingStart = false
        stopping = true
        activeStop = revision
        return revision
    }

    /** A successful completed stop may return one deferred restart token. */
    @Synchronized
    fun completeStop(stopToken: Long, success: Boolean): Long? {
        if (activeStop != stopToken || !stopping) return null
        stopping = false
        activeStop = null
        val restart = if (success && pendingStart) revision else null
        pendingStart = false
        return restart
    }

    @Synchronized
    fun canResume(token: Long): Boolean = !stopping && revision == token
}

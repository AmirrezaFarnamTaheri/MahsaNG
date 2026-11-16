package com.v2ray.ang.viewmodel

import androidx.lifecycle.ViewModel
import com.v2ray.ang.util.TargetDiscoveryResult

/**
 * Ephemeral scan evidence survives rotation but never backs up or auto-restarts.
 * The Activity owns and closes the actual sockets and network observer.
 */
internal class TargetDiscoveryViewModel : ViewModel() {
    val observations = mutableListOf<TargetDiscoveryResult>()
    var generation = 0L
    var running = false
    var stopped = false
    var networkChanged = false
    var total = 0
    var lastStartMillis = 0L
    var verifiedOnly = false
    var lastModeTls = false

    fun interrupt() {
        generation++
        running = false
        stopped = true
    }
}

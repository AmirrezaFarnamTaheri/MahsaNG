package com.v2ray.ang.service

/** Native stop state is process-wide, so a new service cannot re-arm JNI
 * while an older native routing worker may still be alive. */
internal object PsiphonNativeWorkerGate {
    private var workerInFlight = false

    @Synchronized
    fun acquire(prepareNative: () -> Unit): Boolean {
        if (workerInFlight) return false
        workerInFlight = true
        try {
            prepareNative()
        } catch (failure: Throwable) {
            workerInFlight = false
            throw failure
        }
        return true
    }

    @Synchronized
    fun release() {
        workerInFlight = false
    }
}

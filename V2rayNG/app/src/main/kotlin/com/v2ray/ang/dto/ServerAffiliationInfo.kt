package com.v2ray.ang.dto

/**
 * observationId identifies one accepted test-result write. Older affiliations
 * deserialize with null and must be retested before destructive failed removal.
 */
data class ServerAffiliationInfo(
    var testDelayMillis: Long = 0L,
    var observationId: String? = null,
) {
    fun getTestDelayString(): String {
        if (testDelayMillis == 0L) {
            return ""
        }
        return testDelayMillis.toString() + "ms"
    }
}

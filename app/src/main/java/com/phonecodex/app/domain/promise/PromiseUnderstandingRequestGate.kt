package com.phonecodex.app.domain.promise

/**
 * Invalidates compiler results when the promise changes while a request is in flight.
 */
internal class PromiseUnderstandingRequestGate {
    private var version: Long = 0

    fun begin(): Long = ++version

    fun invalidate() {
        version++
    }

    fun isCurrent(requestVersion: Long): Boolean = requestVersion == version
}

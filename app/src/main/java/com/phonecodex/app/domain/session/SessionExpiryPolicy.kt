package com.phonecodex.app.domain.session

import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.SessionStatus

object SessionExpiryPolicy {

    const val EXPIRED_EVENT_MESSAGE = "Study World ended because timer expired"

    fun isExpired(session: FocusSession, nowMillis: Long): Boolean {
        if (session.status != SessionStatus.ACTIVE && session.status != SessionStatus.LOCKED) {
            return false
        }
        return nowMillis >= session.deadlineMillis
    }
}

package com.phonecodex.app.domain.session

import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.SessionStatus
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

object SessionExpiryPolicy {

    const val EXPIRED_EVENT_MESSAGE = "Study World ended because timer expired"

    fun isExpired(
        session: FocusSession,
        nowMillis: Long,
        shortFormDailyQuotaLimit: Int? = null,
        zoneId: ZoneId = ZoneId.systemDefault()
    ): Boolean {
        if (session.status != SessionStatus.ACTIVE && session.status != SessionStatus.LOCKED) {
            return false
        }
        return nowMillis >= effectiveDeadlineMillis(session, nowMillis, shortFormDailyQuotaLimit, zoneId)
    }

    /**
     * A shorts-count quota without "today" was being stored as a 30-minute
     * session. Quota law lasts until local midnight.
     */
    fun effectiveDeadlineMillis(
        session: FocusSession,
        nowMillis: Long,
        shortFormDailyQuotaLimit: Int?,
        zoneId: ZoneId = ZoneId.systemDefault()
    ): Long {
        if (shortFormDailyQuotaLimit == null || shortFormDailyQuotaLimit <= 0) {
            return session.deadlineMillis
        }
        val endOfDay = LocalDate.ofInstant(Instant.ofEpochMilli(nowMillis), zoneId)
            .plusDays(1)
            .atStartOfDay(zoneId)
            .toInstant()
            .toEpochMilli()
        return maxOf(session.deadlineMillis, endOfDay)
    }
}

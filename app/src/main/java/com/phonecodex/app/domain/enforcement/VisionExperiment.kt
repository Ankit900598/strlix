package com.phonecodex.app.domain.enforcement

import java.time.Instant
import java.time.ZoneOffset
import java.time.ZonedDateTime

/**
 * Time-boxed vision counsel. Debug builds default ON until flipped; release OFF.
 * Hard kill date — never silent forever-on capture. AI is counsel; PolicyEngine is law.
 *
 * Window: 2026-09-19 consent → 2026-09-29 00:00 Asia/Kolkata (IST).
 */
object VisionExperiment {

    const val KILL_DATE_LABEL = "29 Sep 2026 00:00 IST"

    private val IST: ZoneOffset = ZoneOffset.ofHoursMinutes(5, 30)

    /**
     * 2026-09-29 00:00:00 IST = 2026-09-28 18:30:00 UTC.
     */
    val END_EPOCH_MS: Long = ZonedDateTime.of(
        2026,
        9,
        29,
        0,
        0,
        0,
        0,
        IST
    ).toInstant().toEpochMilli()

    fun isCalendarWindowOpen(nowEpochMs: Long): Boolean =
        nowEpochMs < END_EPOCH_MS

    /**
     * True only while the hardcoded window is open **and** the Home toggle is on.
     */
    fun isActive(nowEpochMs: Long, visionExperimentEnabled: Boolean): Boolean =
        visionExperimentEnabled && isCalendarWindowOpen(nowEpochMs)

    fun instantAtEnd(): Instant = Instant.ofEpochMilli(END_EPOCH_MS)
}

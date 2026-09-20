package com.phonecodex.app.domain.enforcement

/**
 * Advisory labels from the vision classify path.
 * Never become MEDIA_BLOCK_OVER_MAX / MEDIA_BLOCK_UNDER_MIN — those need a clock.
 */
object VisionAdvisoryKinds {
    const val LIKELY_SHORT_FORM = "likely_short_form"
    const val LIKELY_LONG_FORM = "likely_long_form"
    const val LIKELY_MOVIE = "likely_movie"
    const val UNKNOWN = "unknown"
    const val ADULT_SIGNAL = "adult_signal"

    fun normalize(raw: String?): String {
        val value = raw?.trim()?.lowercase().orEmpty()
        return when (value) {
            LIKELY_SHORT_FORM,
            LIKELY_LONG_FORM,
            LIKELY_MOVIE,
            ADULT_SIGNAL -> value
            else -> UNKNOWN
        }
    }
}

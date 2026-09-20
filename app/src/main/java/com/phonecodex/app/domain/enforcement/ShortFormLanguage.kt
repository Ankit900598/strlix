package com.phonecodex.app.domain.enforcement

/**
 * Messy spoken/typed short-form quota language.
 * People say shots, sorts, "up to max 10" — not only "at most 10 shorts".
 */
object ShortFormLanguage {

    const val NOUN = """shorts?|shots?|sorts?|reels?|short\s+videos?"""

    val HAS_QUOTA: Regex = Regex(
        """\b(?:at\s+most|up\s*to(?:\s+max(?:imum)?)?|only(?:\s+up\s*to)?(?:\s+max(?:imum)?)?|""" +
            """max(?:imum)?|allow|watch)?\s*(\d+)\s*(?:$NOUN)\b"""
    )

    val PREFIXED_LIMIT: Regex = Regex(
        """\b(?:at\s+most|up\s*to(?:\s+max(?:imum)?)?|only(?:\s+up\s+to)?(?:\s+max(?:imum)?)?|""" +
            """max(?:imum)?|allow|watch)\s+(\d+)\s*(?:$NOUN)\b"""
    )

    fun parseLimit(goal: String): Int? {
        val normalized = goal.lowercase()
        PREFIXED_LIMIT.find(normalized)?.groupValues?.getOrNull(1)
            ?.toIntOrNull()
            ?.takeIf { it in 1..500 }
            ?.let { return it }
        return HAS_QUOTA.find(normalized)?.groupValues?.getOrNull(1)
            ?.toIntOrNull()
            ?.takeIf { it in 1..500 }
    }
}

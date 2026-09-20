package com.phonecodex.app.domain.enforcement

/**
 * Reads Play Store listing text already on screen (accessibility).
 * No Google API. Genre chips are developer-chosen; GAME and DATING are
 * high-precision. SOCIAL / COMMUNICATION are labels, not truth.
 */
object PlayListingCategoryParser {

    fun infer(screenText: String): AppClass {
        val text = screenText.lowercase()
        if (text.isBlank()) return AppClass.UNKNOWN
        if (DATING_MARKERS.any { marker -> text.contains(marker) }) return AppClass.DATING
        if (looksLikeGameListing(text)) return AppClass.GAME
        if (SOCIAL_MARKERS.any { marker -> text.contains(marker) }) return AppClass.SOCIAL
        if (COMMUNICATION_MARKERS.any { marker -> text.contains(marker) }) {
            return AppClass.COMMUNICATION
        }
        if (MUSIC_MARKERS.any { marker -> text.contains(marker) }) return AppClass.MUSIC
        if (EDUCATION_MARKERS.any { marker -> text.contains(marker) }) return AppClass.EDUCATION
        if (UTILITY_MARKERS.any { marker -> text.contains(marker) }) return AppClass.UTILITY
        if (MEDIA_MARKERS.any { marker -> text.contains(marker) }) return AppClass.MEDIA
        return AppClass.UNKNOWN
    }

    fun isPlayStorePackage(packageName: String): Boolean {
        val lower = packageName.lowercase()
        return lower == "com.android.vending" || lower == "com.android.vending.tv"
    }

    private fun looksLikeGameListing(text: String): Boolean {
        if (GAME_HEAD_MARKERS.any { marker -> text.contains(marker) }) return true
        return GAME_SUBGENRES.any { genre -> text.contains(genre) } &&
            (text.contains("contains ads") ||
                text.contains("in-app purchases") ||
                text.contains("install"))
    }

    private val DATING_MARKERS = listOf("dating")

    private val GAME_HEAD_MARKERS = listOf(
        "category games",
        "games •",
        "games casual",
        "games action",
        "action game",
        "battle royale",
        "multiplayer game"
    )

    private val GAME_SUBGENRES = listOf(
        "arcade",
        "casual",
        "puzzle",
        "racing",
        "simulation",
        "strategy",
        "board",
        "casino",
        "role playing",
        "adventure",
        "trivia"
    )

    private val SOCIAL_MARKERS = listOf("social")

    private val COMMUNICATION_MARKERS = listOf("communication")

    private val MUSIC_MARKERS = listOf("music & audio", "music and audio")

    private val EDUCATION_MARKERS = listOf("education", "educational")

    private val UTILITY_MARKERS = listOf("productivity", "tools", "finance")

    private val MEDIA_MARKERS = listOf("video players", "entertainment")
}

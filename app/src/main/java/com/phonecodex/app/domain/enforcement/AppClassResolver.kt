package com.phonecodex.app.domain.enforcement

/**
 * Resolves a package + screen into [AppClass] without a cloud model.
 * Play listing text wins on the store page. Local detectors win in-app.
 * Azure / web research is later counsel for SOCIAL leftovers, not this file.
 */
object AppClassResolver {

    fun resolve(packageName: String, screenText: String): AppClass {
        if (packageName.isBlank()) return AppClass.UNKNOWN
        if (EntertainmentClassDetector.isMonkExemptPackage(packageName)) {
            return AppClass.UTILITY
        }
        if (PlayListingCategoryParser.isPlayStorePackage(packageName)) {
            return PlayListingCategoryParser.infer(screenText)
        }
        if (EntertainmentClassDetector.looksLikeDatingLiveCall(packageName, screenText)) {
            return AppClass.DATING
        }
        if (EntertainmentClassDetector.looksLikeGame(packageName, screenText)) {
            return AppClass.GAME
        }
        if (isMusicPackage(packageName)) {
            return AppClass.MUSIC
        }
        val kind = VideoPlatformRegistry.platformKind(packageName)
        if (kind == VideoPlatformKind.INSTAGRAM ||
            kind == VideoPlatformKind.FACEBOOK ||
            kind == VideoPlatformKind.TIKTOK ||
            kind == VideoPlatformKind.SNAPCHAT
        ) {
            return AppClass.SOCIAL
        }
        if (VideoPlatformRegistry.enforcesMediaSurfaces(packageName) ||
            VideoPlatformRegistry.isVideoOrStreamingPackage(packageName)
        ) {
            return AppClass.MEDIA
        }
        return AppClass.UNKNOWN
    }

    private fun isMusicPackage(packageName: String): Boolean {
        val lower = packageName.lowercase()
        return lower in MUSIC_PACKAGES ||
            MUSIC_SUBSTRINGS.any { hint -> lower.contains(hint) }
    }

    private val MUSIC_PACKAGES = setOf(
        "com.spotify.music",
        "com.google.android.apps.youtube.music",
        "com.gaana",
        "com.jio.media.jiobeats",
        "com.bsbportal.music",
        "com.amazon.mp3"
    )

    private val MUSIC_SUBSTRINGS = listOf(
        "spotify",
        "youtubemusic",
        "youtube.music",
        "jiosaavn",
        "gaana"
    )
}

package com.phonecodex.app.domain.enforcement

/**
 * Known video / short-form platforms for enforcement.
 * Extension point: add aliases here before scattering package strings.
 */
enum class VideoPlatformKind {
    OFFICIAL_YOUTUBE,
    CHROME_WEB,
    NEWPIPE,
    INSTAGRAM,
    FACEBOOK,
    TIKTOK,
    SNAPCHAT,
    OTHER_VIDEO,
    MOVIE_STREAMING,
    UNKNOWN_CLONE
}

data class VideoPlatformEntry(
    val packageName: String,
    val label: String,
    val kind: VideoPlatformKind,
    /** When true, media-length / surface / short-form quota runs for this package. */
    val enforcesMediaSurfaces: Boolean = true,
    val participatesInShortFormQuota: Boolean = true
)

object VideoPlatformRegistry {

    const val YOUTUBE = "com.google.android.youtube"
    const val CHROME = "com.android.chrome"
    const val NEWPIPE = "org.schabi.newpipe"
    const val INSTAGRAM = "com.instagram.android"
    const val FACEBOOK = "com.facebook.katana"
    const val TIKTOK = "com.zhiliaoapp.musically"
    const val SNAPCHAT = "com.snapchat.android"
    const val NETMIRROR = "app.netmirror.newtv"

    private val entriesByPackage: Map<String, VideoPlatformEntry> = listOf(
        VideoPlatformEntry(YOUTUBE, "YouTube", VideoPlatformKind.OFFICIAL_YOUTUBE),
        VideoPlatformEntry(CHROME, "Chrome", VideoPlatformKind.CHROME_WEB),
        VideoPlatformEntry(NEWPIPE, "NewPipe", VideoPlatformKind.NEWPIPE),
        VideoPlatformEntry(
            packageName = "org.schabi.newpipe.legacy",
            label = "NewPipe Legacy",
            kind = VideoPlatformKind.NEWPIPE
        ),
        VideoPlatformEntry(INSTAGRAM, "Instagram", VideoPlatformKind.INSTAGRAM),
        VideoPlatformEntry(FACEBOOK, "Facebook", VideoPlatformKind.FACEBOOK),
        VideoPlatformEntry(TIKTOK, "TikTok", VideoPlatformKind.TIKTOK),
        VideoPlatformEntry(SNAPCHAT, "Snapchat", VideoPlatformKind.SNAPCHAT),
        VideoPlatformEntry(
            packageName = "com.vanced.android.youtube",
            label = "YouTube Vanced",
            kind = VideoPlatformKind.OTHER_VIDEO
        ),
        VideoPlatformEntry(
            packageName = NETMIRROR,
            label = "NetMirror",
            kind = VideoPlatformKind.MOVIE_STREAMING,
            enforcesMediaSurfaces = true,
            participatesInShortFormQuota = false
        )
    ).associateBy { it.packageName }

    fun entry(packageName: String): VideoPlatformEntry? = entriesByPackage[packageName]

    fun platformKind(packageName: String): VideoPlatformKind =
        entry(packageName)?.kind ?: VideoPlatformKind.UNKNOWN_CLONE

    fun isRegistered(packageName: String): Boolean = packageName in entriesByPackage

    fun isKnownVideoPlatform(packageName: String): Boolean = isRegistered(packageName)

    fun isOfficialYouTube(packageName: String): Boolean =
        entry(packageName)?.kind == VideoPlatformKind.OFFICIAL_YOUTUBE

    fun isChrome(packageName: String): Boolean =
        entry(packageName)?.kind == VideoPlatformKind.CHROME_WEB

    fun isNewPipe(packageName: String): Boolean =
        entry(packageName)?.kind == VideoPlatformKind.NEWPIPE

    fun isInstagram(packageName: String): Boolean =
        entry(packageName)?.kind == VideoPlatformKind.INSTAGRAM

    /** Packages that should run surface + media-length local law. */
    fun enforcesMediaSurfaces(packageName: String): Boolean =
        entry(packageName)?.enforcesMediaSurfaces == true ||
            looksLikeUnknownStreamingPackage(packageName)

    fun participatesInShortFormQuota(packageName: String): Boolean =
        entry(packageName)?.participatesInShortFormQuota == true

    /**
     * Registered video platform or an unlisted movie/OTT/player package.
     * Shared by SurfaceDetector, coordinator, and Accessibility.
     */
    fun isVideoOrStreamingPackage(packageName: String): Boolean =
        entry(packageName)?.enforcesMediaSurfaces == true ||
            looksLikeUnknownStreamingPackage(packageName)

    /**
     * Package-name heuristic for unknown movie/TV/OTT/player apps.
     * Token match for short hints (`tv`); substring for compound names (`newtv`, `netmirror`).
     */
    fun looksLikeUnknownStreamingPackage(packageName: String): Boolean {
        val lower = packageName.lowercase().trim()
        if (lower.isEmpty()) return false
        val tokens = lower.split('.', '_', '-', '/')
        if (tokens.any { it in STREAMING_TOKEN_HINTS }) return true
        return STREAMING_SUBSTRING_HINTS.any { hint -> lower.contains(hint) }
    }

    /**
     * Unregistered package that looks like a video/entertainment clone.
     * Must WARN, never silent ALLOW-as-harmless.
     */
    fun isUnknownVideoCloneCandidate(packageName: String, screenText: String): Boolean {
        if (isRegistered(packageName)) return false
        if (looksLikeUnknownStreamingPackage(packageName)) return true
        val normalized = screenText.lowercase()
        val nameHint = packageName.lowercase()
        val packageLooksVideo =
            nameHint.contains("media") ||
                nameHint.contains("reel") ||
                nameHint.contains("tiktok") ||
                nameHint.contains("newpipe")
        val textLooksVideo =
            normalized.contains("play") &&
                (
                    normalized.contains("video") ||
                        CLOCK_HINT.containsMatchIn(normalized) ||
                        normalized.contains("subscribe") ||
                        normalized.contains("channel")
                    )
        return packageLooksVideo || textLooksVideo
    }

    fun isInEnforcementScope(
        packageName: String,
        enforcementScopePackages: Collection<String>
    ): Boolean {
        val scope = enforcementScopePackages.map { it.trim() }.filter { it.isNotEmpty() }.toSet()
        if (scope.isEmpty()) return true
        return packageName in scope
    }

    fun isInEnforcementScope(
        packageName: String,
        screenText: String,
        enforcementScopePackages: Collection<String>,
        contentBrands: Collection<String> = emptyList()
    ): Boolean = EnforcementScopeLaw.matches(
        packageName = packageName,
        screenText = screenText,
        scopePackages = enforcementScopePackages,
        contentBrands = contentBrands
    )

    fun canonicalizeNamedPackage(raw: String): String? {
        val lower = raw.lowercase().trim()
        if (lower.isEmpty()) return null
        if (lower.contains("netmirror") || lower.contains("newtv")) return NETMIRROR
        if (isRegistered(lower)) return lower
        return null
    }

    fun knownPackages(): Set<String> = entriesByPackage.keys

    fun shortFormQuotaPackages(): Set<String> =
        entriesByPackage.filterValues { it.participatesInShortFormQuota }.keys

    fun defaultAiDecidePackages(): List<Pair<String, String>> =
        listOf(
            YOUTUBE to "YouTube",
            CHROME to "Chrome",
            NEWPIPE to "NewPipe",
            INSTAGRAM to "Instagram",
            FACEBOOK to "Facebook",
            TIKTOK to "TikTok",
            SNAPCHAT to "Snapchat"
        )

    private val CLOCK_HINT = Regex("""\b\d{1,2}:\d{2}\b""")

    private val STREAMING_TOKEN_HINTS = setOf(
        "movie",
        "movies",
        "mirror",
        "tv",
        "ott",
        "stream",
        "streaming",
        "player",
        "video",
        "videos",
        "tube",
        "cinema",
        "anime",
        "watch",
        "newtv"
    )

    private val STREAMING_SUBSTRING_HINTS = listOf(
        "movie",
        "mirror",
        "ott",
        "stream",
        "player",
        "video",
        "tube",
        "cinema",
        "anime",
        "newtv",
        "watch"
    )
}

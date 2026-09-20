package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.model.StudyWorldSettings
import com.phonecodex.app.domain.promise.PromiseIntentRules

/**
 * Content brand / surface vs package membership.
 *
 * "YouTube video/content" is a brand: official app, browser youtube.com,
 * NewPipe / Vanced / future clients, embeds. Package-exclusive scope is only
 * for an explicit "YouTube app only" (or rematerialized youtube_only).
 *
 * Empty package list AND empty brand list = unrestricted (legacy clocks).
 */
object EnforcementScopeLaw {

    const val BRAND_YOUTUBE = "youtube"

    const val SCOPE_YOUTUBE_CONTENT = "youtube_content"
    const val SCOPE_YOUTUBE_APP_ONLY = "youtube_app_only"
    const val SCOPE_YOUTUBE_ONLY = "youtube_only"
    const val SCOPE_YOUTUBE_SHORTS_ONLY = "youtube_shorts_only"

    fun matches(
        packageName: String,
        screenText: String,
        settings: StudyWorldSettings
    ): Boolean = matches(
        packageName = packageName,
        screenText = screenText,
        scopePackages = settings.enforcementScopePackages,
        contentBrands = settings.enforcementContentBrands
    )

    fun matches(
        packageName: String,
        screenText: String,
        scopePackages: Collection<String>,
        contentBrands: Collection<String>
    ): Boolean {
        val packages = scopePackages.map { it.trim() }.filter { it.isNotEmpty() }.toSet()
        val brands = contentBrands.map { normalizeBrand(it) }.filter { it.isNotEmpty() }.toSet()
        if (packages.isEmpty() && brands.isEmpty()) return true
        if (packageName in packages) return true
        if (BRAND_YOUTUBE in brands && isYouTubeSurface(packageName, screenText)) return true
        return false
    }

    fun isYouTubeAppOnlyScopeKind(scopeKind: String?): Boolean {
        val kind = scopeKind?.trim()?.lowercase().orEmpty()
        return kind == SCOPE_YOUTUBE_APP_ONLY ||
            kind == SCOPE_YOUTUBE_ONLY ||
            kind == SCOPE_YOUTUBE_SHORTS_ONLY
    }

    fun isYouTubeContentScopeKind(scopeKind: String?): Boolean =
        scopeKind?.trim()?.lowercase() == SCOPE_YOUTUBE_CONTENT

    fun isYouTubeSurface(packageName: String, screenText: String): Boolean {
        if (isYouTubeClientPackage(packageName)) return true
        if (AccessibilityUrlExtractor.containsYouTubeUrl(screenText)) return true
        if (YOUTUBE_HOST_INLINE.containsMatchIn(screenText.lowercase())) return true
        if (
            looksLikeBrowserPackage(packageName) &&
            YOUTUBE_BRAND_TOKEN.containsMatchIn(screenText.lowercase()) &&
            SurfaceDetector.detect(packageName, screenText).isActivePlayer
        ) {
            return true
        }
        return false
    }

    fun isYouTubeClientPackage(packageName: String): Boolean {
        if (VideoPlatformRegistry.isOfficialYouTube(packageName)) return true
        if (VideoPlatformRegistry.isNewPipe(packageName)) return true
        val lower = packageName.lowercase()
        return YOUTUBE_CLIENT_NAME_HINTS.any { hint -> lower.contains(hint) }
    }

    fun looksLikeBrowserPackage(packageName: String): Boolean {
        if (VideoPlatformRegistry.isChrome(packageName)) return true
        val lower = packageName.lowercase()
        return BROWSER_NAME_HINTS.any { hint -> lower.contains(hint) }
    }

    fun normalizeBrand(raw: String): String {
        val lower = raw.trim().lowercase()
        if (lower.isEmpty()) return ""
        if (lower == BRAND_YOUTUBE || lower.contains("youtube") || lower == "yt") {
            return BRAND_YOUTUBE
        }
        return lower
    }

    fun resolveContentBrands(
        explicitBrands: Collection<String>,
        scopeKind: String?,
        rawText: String
    ): List<String> {
        if (isYouTubeAppOnlyScopeKind(scopeKind) || PromiseIntentRules.namesYouTubeAppOnly(rawText)) {
            return emptyList()
        }
        val explicit = explicitBrands.map { normalizeBrand(it) }.filter { it.isNotEmpty() }.distinct()
        if (explicit.isNotEmpty()) return explicit
        if (isYouTubeContentScopeKind(scopeKind) || PromiseIntentRules.namesYouTubeContentBrand(rawText)) {
            return listOf(BRAND_YOUTUBE)
        }
        return emptyList()
    }

    fun resolvePackageScope(
        rawPackages: Collection<String>,
        contentBrands: Collection<String>,
        scopeKind: String?,
        rawText: String
    ): List<String> {
        val packages = rawPackages.map { it.trim() }.filter { it.isNotEmpty() }.distinct()
        if (isYouTubeAppOnlyScopeKind(scopeKind) || PromiseIntentRules.namesYouTubeAppOnly(rawText)) {
            return if (packages.isNotEmpty()) {
                packages
            } else {
                listOf(VideoPlatformRegistry.YOUTUBE)
            }
        }
        val brands = contentBrands.map { normalizeBrand(it) }.toSet()
        val youtubeContent =
            BRAND_YOUTUBE in brands ||
                isYouTubeContentScopeKind(scopeKind) ||
                PromiseIntentRules.namesYouTubeContentBrand(rawText)
        if (!youtubeContent) return packages
        val withoutYoutubeClients = packages.filterNot { isYouTubeClientPackage(it) }
        val onlyYoutubeClients = packages.isNotEmpty() && withoutYoutubeClients.isEmpty()
        return if (onlyYoutubeClients) emptyList() else withoutYoutubeClients
    }

    private val YOUTUBE_HOST_INLINE = Regex(
        """(?:^|[^\w])(?:(?:m|music|www)\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)\b"""
    )

    private val YOUTUBE_BRAND_TOKEN = Regex("""\byoutube\b""")

    private val YOUTUBE_CLIENT_NAME_HINTS = listOf(
        "youtube",
        "vanced",
        "revanced"
    )

    private val BROWSER_NAME_HINTS = listOf(
        "chrome",
        "browser",
        "firefox",
        "fenix",
        "sbrowser",
        "brave",
        "opera",
        "duckduckgo",
        "microsoft.emmx"
    )
}

package com.phonecodex.app.domain.guardrail

import com.phonecodex.app.domain.enforcement.OverlayLifecycleGate
import com.phonecodex.app.domain.enforcement.VideoPlatformKind
import com.phonecodex.app.domain.enforcement.VideoPlatformRegistry

/**
 * One adult-content matcher for guardrail, Chrome signals, and short-form quota.
 *
 * Substring `contains("porn")` / `contains("xxx")` is illegal here: YouTube video IDs
 * and smashed overlay copy ("BlockkPornn") are false strong hits.
 */
object AdultContentLaw {

    enum class Decision {
        NONE,
        WARN,
        BLOCK
    }

    data class Verdict(
        val decision: Decision,
        val strongSites: List<String>,
        val weakWords: List<String>
    ) {
        val isHardBlock: Boolean get() = decision == Decision.BLOCK
    }

    fun inspect(packageName: String, screenText: String): Verdict {
        if (shouldSkipPackage(packageName)) {
            return Verdict(Decision.NONE, emptyList(), emptyList())
        }
        val cleaned = stripSelfEcho(screenText).lowercase()
        val strongSites = STRONG_SITES.mapNotNull { signal ->
            signal.label.takeIf { signal.pattern.containsMatchIn(cleaned) }
        }
        val weakWords = WEAK_WORDS.mapNotNull { signal ->
            signal.label.takeIf { signal.pattern.containsMatchIn(cleaned) }
        }
        if (strongSites.isNotEmpty()) {
            return Verdict(Decision.BLOCK, strongSites, weakWords)
        }
        if (weakWords.size >= 2) {
            return Verdict(Decision.BLOCK, emptyList(), weakWords)
        }
        if (weakWords.size == 1) {
            // Chrome/YouTube comments and related-video trees mention words once.
            // STRICT WARN has no Continue, so one word must not become an overlay.
            if (isCommentNoisy(packageName)) {
                return Verdict(Decision.NONE, emptyList(), weakWords)
            }
            return Verdict(Decision.WARN, emptyList(), weakWords)
        }
        return Verdict(Decision.NONE, emptyList(), emptyList())
    }

    fun isHardBlock(screenText: String): Boolean {
        val cleaned = stripSelfEcho(screenText).lowercase()
        if (STRONG_SITES.any { it.pattern.containsMatchIn(cleaned) }) {
            return true
        }
        return WEAK_WORDS.count { it.pattern.containsMatchIn(cleaned) } >= 2
    }

    fun shouldSkipPackage(packageName: String): Boolean {
        if (packageName.isBlank()) return true
        return OverlayLifecycleGate.isOwnPackage(packageName) ||
            OverlayLifecycleGate.isSystemUi(packageName) ||
            OverlayLifecycleGate.isLauncher(packageName)
    }

    fun stripSelfEcho(screenText: String): String {
        var text = screenText
        SELF_ECHO_PATTERNS.forEach { pattern ->
            text = pattern.replace(text, " ")
        }
        return text.replace(Regex("""\s+"""), " ").trim()
    }

    private fun isCommentNoisy(packageName: String): Boolean {
        return when (VideoPlatformRegistry.platformKind(packageName)) {
            VideoPlatformKind.CHROME_WEB,
            VideoPlatformKind.OFFICIAL_YOUTUBE,
            VideoPlatformKind.NEWPIPE,
            VideoPlatformKind.INSTAGRAM,
            VideoPlatformKind.FACEBOOK,
            VideoPlatformKind.TIKTOK,
            VideoPlatformKind.SNAPCHAT,
            VideoPlatformKind.OTHER_VIDEO -> true
            VideoPlatformKind.MOVIE_STREAMING,
            VideoPlatformKind.UNKNOWN_CLONE -> false
        }
    }

    private data class Signal(
        val label: String,
        val pattern: Regex
    )

    private fun word(token: String): Signal {
        val escaped = Regex.escape(token)
        return Signal(token, Regex("\\b$escaped\\b"))
    }

    private fun phrase(label: String): Signal {
        val body = label.split(Regex("\\s+")).joinToString("\\s+") { part ->
            Regex.escape(part)
        }
        return Signal(label, Regex("\\b$body\\b"))
    }

    private val STRONG_SITES = listOf(
        word("pornhub"),
        word("xvideos"),
        word("xhamster"),
        word("onlyfans"),
        word("redtube"),
        word("xnxx")
    )

    private val WEAK_WORDS = listOf(
        word("porn"),
        word("xxx"),
        word("nsfw"),
        word("nude"),
        word("naked"),
        word("pornography"),
        phrase("adult video"),
        phrase("adult content"),
        phrase("sex tape")
    )

    private val SELF_ECHO_PATTERNS = listOf(
        Regex("""(?i)permanent\s*guardrail[\s\S]{0,120}"""),
        Regex("""(?i)block\s*porn"""),
        Regex("""(?i)matched\s*:\s*(?:strong|weak)[\s\S]{0,80}"""),
        Regex("""(?i)outside\s*your\s*promise"""),
        Regex("""(?i)you\s*promised\s*this""")
    )
}

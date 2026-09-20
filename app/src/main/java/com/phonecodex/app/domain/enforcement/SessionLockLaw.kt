package com.phonecodex.app.domain.enforcement

/**
 * LOCKED means "no easy way back into the forbidden surface".
 * It is not a phone brick. Calls, contacts, ChatGPT, calendar, search,
 * and banking stay usable. Unknown chat apps do not.
 */
object SessionLockLaw {

    fun shouldKeepLockingPackage(
        packageName: String,
        screenText: String = "",
        goal: String = ""
    ): Boolean {
        if (packageName.isBlank()) return false
        if (EntertainmentClassDetector.isMonkExemptPackage(packageName)) return false
        if (PromiseCategoryLaw.shouldBlock(packageName, screenText, goal)) return true
        if (goal.isNotBlank()) return false
        return VideoPlatformRegistry.enforcesMediaSurfaces(packageName) ||
            VideoPlatformRegistry.isVideoOrStreamingPackage(packageName) ||
            EntertainmentClassDetector.looksLikeDatingLiveCall(packageName, screenText) ||
            EntertainmentClassDetector.looksLikeGame(packageName, screenText) ||
            EntertainmentClassDetector.looksLikeBlockedInstallSurface(packageName, screenText) ||
            packageName.contains("packageinstaller", ignoreCase = true)
    }

    fun mayUseAppWhileLocked(
        packageName: String,
        screenText: String = "",
        goal: String = ""
    ): Boolean = !shouldKeepLockingPackage(packageName, screenText, goal)

    fun isContactsPhoneOrMessaging(packageName: String): Boolean {
        val tokens = packageName.lowercase().split('.', '_', '-')
        return tokens.any { it in CONTACT_PHONE_TOKENS }
    }

    fun isAssistantPackage(packageName: String): Boolean {
        val lower = packageName.lowercase()
        return ASSISTANT_PACKAGES.contains(lower) ||
            lower.contains("chatgpt") ||
            lower.endsWith(".grok") ||
            lower.contains("anthropic.claude")
    }

    private val CONTACT_PHONE_TOKENS = setOf(
        "contacts",
        "dialer",
        "mms",
        "messaging",
        "emergency",
        "incallui"
    )

    private val ASSISTANT_PACKAGES = setOf(
        "com.openai.chatgpt",
        "com.xai.grok",
        "ai.x.grok"
    )
}

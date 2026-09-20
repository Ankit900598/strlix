package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.safeapps.SafeAppsCatalog

/**
 * Local heuristics for entertainment-class apps that sit outside the named
 * YouTube/Chrome/social registry: dating, live-cam, video-call, hostess,
 * live-girls, casual games, and Play Store / package-installer confirmation.
 *
 * Package tokens + screen phrases. Not a cloud model. Emergency / contacts /
 * dialer / SMS / settings / ChatGPT stay exempt at [EntertainmentBanGate].
 */
object EntertainmentClassDetector {

    const val JOLA_VIDEO = "com.jola.video.app"
    const val FACHAT_FREECHAT = "com.fachat.freechat"

    fun looksLikeDatingLiveCall(packageName: String, screenText: String): Boolean {
        val lower = packageName.lowercase().trim()
        if (lower.isEmpty() || isCameraOrSystemCall(lower)) return false
        if (lower in KNOWN_DATING_LIVE_CALL_PACKAGES) return true
        val tokens = tokenize(lower)
        if (tokens.any { it in DATING_LIVE_CALL_TOKENS }) return true
        if (DATING_LIVE_CALL_SUBSTRINGS.any { hint -> lower.contains(hint) }) return true
        val text = screenText.lowercase()
        if (text.isBlank()) return false
        val phraseHits = DATING_LIVE_CALL_PHRASES.count { phrase -> text.contains(phrase) }
        if (phraseHits >= 2) return true
        return phraseHits >= 1 &&
            (tokens.any { it == "video" || it == "live" || it == "chat" } ||
                lower.contains("video") ||
                lower.contains("live"))
    }

    fun looksLikeGame(packageName: String, screenText: String): Boolean {
        val lower = packageName.lowercase().trim()
        if (lower.isEmpty() || isCameraOrSystemCall(lower)) return false
        if (lower in KNOWN_GAME_PACKAGES) return true
        val tokens = tokenize(lower)
        if (tokens.any { it in GAME_TOKENS }) return true
        if (GAME_SUBSTRINGS.any { hint -> lower.contains(hint) }) return true
        val text = screenText.lowercase()
        if (text.isBlank()) return false
        return GAME_SCREEN_PHRASES.count { phrase -> text.contains(phrase) } >= 2
    }

    /**
     * Install / permission / payment confirmation — not Play Store browsing.
     */
    fun looksLikeBlockedInstallSurface(packageName: String, screenText: String): Boolean {
        val lower = packageName.lowercase().trim()
        if (lower.contains("packageinstaller")) return true
        val detection = SurfaceDetector.detect(packageName, screenText)
        return detection.surface == SurfaceDetectionResult.INSTALL_FLOW ||
            detection.surface == SurfaceDetectionResult.PAYMENT_FLOW
    }

    fun isMonkExemptPackage(packageName: String): Boolean {
        if (packageName.isBlank()) return true
        if (SafeAppsCatalog.isDefaultPackage(packageName)) return true
        if (SessionLockLaw.isContactsPhoneOrMessaging(packageName)) return true
        if (SessionLockLaw.isAssistantPackage(packageName)) return true
        if (OverlayLifecycleGate.isLauncher(packageName)) return true
        if (OverlayLifecycleGate.isSystemUi(packageName)) return true
        return isUtilityWorkOrBanking(packageName)
    }

    /**
     * Clock, calendar, files, search, camera, UPI — not girls-chat.
     * Unknown leftover apps stay fail-closed during monk.
     */
    fun isUtilityWorkOrBanking(packageName: String): Boolean {
        val lower = packageName.lowercase().trim()
        if (lower.isEmpty()) return false
        if (lower in UTILITY_OR_WORK_PACKAGES) return true
        if (isCameraOrSystemCall(lower)) return true
        val tokens = tokenize(lower)
        if (tokens.any { it in UTILITY_OR_WORK_TOKENS }) return true
        return BANKING_SUBSTRINGS.any { hint -> lower.contains(hint) }
    }

    private fun isCameraOrSystemCall(lower: String): Boolean {
        val tokens = tokenize(lower)
        return tokens.any { it in CAMERA_OR_SYSTEM_CALL_TOKENS } ||
            lower.contains("android.camera") ||
            lower.endsWith(".camera") ||
            lower.contains("incallui")
    }

    private fun tokenize(packageName: String): List<String> =
        packageName.split('.', '_', '-', '/')

    private val KNOWN_DATING_LIVE_CALL_PACKAGES = setOf(
        JOLA_VIDEO,
        FACHAT_FREECHAT,
        "com.tinder",
        "com.bumble.app",
        "com.okcupid.okcupid",
        "com.p1.mobile.putong",
        "com.sgiggle.production",
        "com.imo.android.imoim",
        "com.live.me",
        "com.hkfuliao.chamet",
        "com.azarlive.android"
    )

    private val DATING_LIVE_CALL_TOKENS = setOf(
        "dating",
        "tinder",
        "bumble",
        "hinge",
        "happn",
        "okcupid",
        "chamet",
        "livu",
        "liveme",
        "azar",
        "hago",
        "mico",
        "tango",
        "jola",
        "fachat",
        "freechat",
        "fchat",
        "flirt",
        "hookup",
        "camgirl",
        "hostess",
        "videochat",
        "videocall",
        "livechat",
        "livecam"
    )

    private val DATING_LIVE_CALL_SUBSTRINGS = listOf(
        "dating",
        "tinder",
        "bumble",
        "chamet",
        "livu",
        "videochat",
        "videocall",
        "livechat",
        "livecam",
        "camgirl",
        "hostess",
        "hookup",
        "azarlive",
        "fachat",
        "freechat",
        "fchat"
    )

    private val DATING_LIVE_CALL_PHRASES = listOf(
        "video call",
        "live call",
        "live girls",
        "live girl",
        "video chat",
        "random match",
        "start matching",
        "hot girls",
        "live cam",
        "cam girls",
        "hostess",
        "private show",
        "chat with girls",
        "talk to girls",
        "meet girls",
        "girls chat",
        "find girls",
        "nearby girls",
        "hot chat"
    )

    private val UTILITY_OR_WORK_PACKAGES = setOf(
        "com.google.android.googlequicksearchbox",
        "com.google.android.calendar",
        "com.android.calendar",
        "com.android.providers.calendar",
        "com.android.deskclock",
        "com.google.android.deskclock",
        "com.android.calculator2",
        "com.google.android.calculator",
        "com.miui.calculator",
        "com.android.documentsui",
        "com.google.android.documentsui"
    )

    private val UTILITY_OR_WORK_TOKENS = setOf(
        "calendar",
        "deskclock",
        "calculator",
        "documentsui",
        "filemanager"
    )

    private val BANKING_SUBSTRINGS = listOf(
        "phonepe",
        "paytm",
        "bhim",
        "nbu.paisa"
    )

    private val KNOWN_GAME_PACKAGES = setOf(
        "com.dts.freefireth",
        "com.pubg.imobile",
        "com.tencent.ig",
        "com.roblox.client",
        "com.mojang.minecraftpe"
    )

    private val GAME_TOKENS = setOf(
        "game",
        "games",
        "gaming",
        "gameloft",
        "pubg",
        "bgmi",
        "freefire",
        "roblox",
        "minecraft"
    )

    private val GAME_SUBSTRINGS = listOf(
        "gameloft",
        "unity3d",
        "play.games",
        "freefire",
        "pubgmobile"
    )

    private val GAME_SCREEN_PHRASES = listOf(
        "play now",
        "multiplayer",
        "leaderboard",
        "battle pass",
        "continue game"
    )

    private val CAMERA_OR_SYSTEM_CALL_TOKENS = setOf(
        "camera",
        "camera2",
        "cameraserver",
        "dialer",
        "incallui",
        "telecom"
    )
}

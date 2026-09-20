package com.phonecodex.app.domain.enforcement

/**
 * Coarse app family for one screen snapshot. Derived from [VideoPlatformRegistry]
 * plus [SurfaceDetector] — never from one-off package string checks at call sites.
 */
enum class SurfaceFamily {
    LAUNCHER,
    BROWSER,
    YOUTUBE,
    VIDEO_CLIENT,
    SOCIAL_FEED,
    MESSAGING,
    SETTINGS,
    PLAY_STORE,
    SYSTEM,
    UNKNOWN
}

/**
 * What the user is actually doing on this snapshot.
 * Only the three ACTIVE_*_PLAYER states may ever justify a media-length BLOCK.
 */
enum class ActivityState {
    PASSIVE,
    ACTIVE_PLAYER,
    ACTIVE_SHORT_PLAYER,
    ACTIVE_LONG_PLAYER,
    INSTALL_FLOW,
    SETTINGS_TAMPER,
    MESSAGING_THREAD,
    UNKNOWN
}

/**
 * Where the visible duration came from. Mirrors [DurationSource] but adds
 * [AMBIGUOUS]: clock-like text parsed as a player clock on a surface that is
 * NOT an active player (e.g. NewPipe history rows with `12:00 / 45:00`).
 * AMBIGUOUS must never drive a BLOCK.
 */
enum class EnforcementDurationSource {
    CURRENT_PLAYER,
    RECOMMENDATION,
    NONE,
    AMBIGUOUS
}

enum class DecisionSource {
    DETERMINISTIC,
    LOCAL_HEURISTIC,
    BACKEND_AI
}

/**
 * One immutable snapshot object per screen, composed from [SurfaceDetector],
 * [VideoDurationParser] and [VideoPlatformRegistry]. Single source of truth for
 * "may this snapshot legally produce a media-length BLOCK?".
 */
data class EnforcementContext(
    val packageName: String,
    val surfaceFamily: SurfaceFamily,
    val activityState: ActivityState,
    val durationSource: EnforcementDurationSource,
    val currentPlayerDurationSeconds: Int?,
    val evidence: List<String>,
    val decisionSource: DecisionSource
) {

    val isActivePlayerState: Boolean
        get() = activityState in ACTIVE_PLAYER_STATES

    /** Media-length BLOCK is only legal from an active player with a current-player clock. */
    fun mayApplyMediaLengthBlock(): Boolean =
        activityState in ACTIVE_PLAYER_STATES &&
            durationSource == EnforcementDurationSource.CURRENT_PLAYER

    companion object {

        private val ACTIVE_PLAYER_STATES = setOf(
            ActivityState.ACTIVE_PLAYER,
            ActivityState.ACTIVE_SHORT_PLAYER,
            ActivityState.ACTIVE_LONG_PLAYER
        )

        private val MESSAGING_PACKAGES = setOf(
            "com.whatsapp",
            "com.android.mms",
            "com.google.android.apps.messaging",
            "org.telegram.messenger"
        )

        /** Compose the snapshot context. Delegates all detection — no duplicated logic. */
        fun from(
            packageName: String,
            screenText: String,
            decisionSource: DecisionSource = DecisionSource.DETERMINISTIC
        ): EnforcementContext {
            val detection = SurfaceDetector.detect(packageName, screenText)
            val parsed = VideoDurationParser.parse(screenText)
            return fromParts(packageName, screenText, detection, parsed, decisionSource)
        }

        /** Variant for callers that already ran [SurfaceDetector] / [VideoDurationParser]. */
        fun fromParts(
            packageName: String,
            screenText: String,
            detection: SurfaceDetection,
            parsed: VideoDurationParseResult,
            decisionSource: DecisionSource = DecisionSource.DETERMINISTIC
        ): EnforcementContext {
            val activityState = mapActivityState(packageName, screenText, detection)
            val durationSource = mapDurationSource(parsed, activityState)
            val playerSeconds =
                if (durationSource == EnforcementDurationSource.CURRENT_PLAYER) {
                    parsed.currentPlayerDurationSeconds
                } else {
                    // AMBIGUOUS / RECOMMENDATION / NONE never expose a legal player clock.
                    null
                }
            return EnforcementContext(
                packageName = packageName,
                surfaceFamily = mapSurfaceFamily(packageName, detection),
                activityState = activityState,
                durationSource = durationSource,
                currentPlayerDurationSeconds = playerSeconds,
                evidence = (detection.evidence +
                    "duration_source=${durationSource.name.lowercase()}").distinct(),
                decisionSource = decisionSource
            )
        }

        private fun mapSurfaceFamily(
            packageName: String,
            detection: SurfaceDetection
        ): SurfaceFamily {
            when (VideoPlatformRegistry.platformKind(packageName)) {
                VideoPlatformKind.OFFICIAL_YOUTUBE -> return SurfaceFamily.YOUTUBE
                VideoPlatformKind.CHROME_WEB -> return SurfaceFamily.BROWSER
                VideoPlatformKind.NEWPIPE,
                VideoPlatformKind.OTHER_VIDEO,
                VideoPlatformKind.MOVIE_STREAMING -> return SurfaceFamily.VIDEO_CLIENT
                VideoPlatformKind.INSTAGRAM,
                VideoPlatformKind.FACEBOOK,
                VideoPlatformKind.TIKTOK,
                VideoPlatformKind.SNAPCHAT -> return SurfaceFamily.SOCIAL_FEED
                VideoPlatformKind.UNKNOWN_CLONE -> Unit
            }

            if (packageName in MESSAGING_PACKAGES) return SurfaceFamily.MESSAGING
            if (isSettingsPackage(packageName)) return SurfaceFamily.SETTINGS
            if (packageName == "com.android.vending") return SurfaceFamily.PLAY_STORE

            return when (detection.surface) {
                SurfaceDetectionResult.LAUNCHER -> SurfaceFamily.LAUNCHER
                SurfaceDetectionResult.SYSTEM_SHADE -> SurfaceFamily.SYSTEM
                SurfaceDetectionResult.PLAY_STORE -> SurfaceFamily.PLAY_STORE
                else -> when {
                    OverlayLifecycleGate.isLauncher(packageName) -> SurfaceFamily.LAUNCHER
                    OverlayLifecycleGate.isSystemUi(packageName) -> SurfaceFamily.SYSTEM
                    else -> SurfaceFamily.UNKNOWN
                }
            }
        }

        private fun mapActivityState(
            packageName: String,
            screenText: String,
            detection: SurfaceDetection
        ): ActivityState = when (detection.surface) {
            SurfaceDetectionResult.ACTIVE_VIDEO_PLAYER -> ActivityState.ACTIVE_PLAYER
            SurfaceDetectionResult.SHORT_FORM_PLAYER -> ActivityState.ACTIVE_SHORT_PLAYER
            SurfaceDetectionResult.LONG_FORM_PLAYER -> ActivityState.ACTIVE_LONG_PLAYER
            SurfaceDetectionResult.INSTALL_FLOW,
            SurfaceDetectionResult.PAYMENT_FLOW -> ActivityState.INSTALL_FLOW
            SurfaceDetectionResult.MESSAGING_THREAD -> ActivityState.MESSAGING_THREAD
            SurfaceDetectionResult.UNKNOWN ->
                if (isSettingsTamper(packageName, screenText)) {
                    ActivityState.SETTINGS_TAMPER
                } else {
                    ActivityState.UNKNOWN
                }
            else ->
                if (isSettingsTamper(packageName, screenText)) {
                    ActivityState.SETTINGS_TAMPER
                } else {
                    ActivityState.PASSIVE
                }
        }

        private fun mapDurationSource(
            parsed: VideoDurationParseResult,
            activityState: ActivityState
        ): EnforcementDurationSource = when (parsed.source) {
            DurationSource.CURRENT_PLAYER ->
                if (activityState in ACTIVE_PLAYER_STATES) {
                    EnforcementDurationSource.CURRENT_PLAYER
                } else {
                    // Player-clock-shaped text on a non-player surface is not trustworthy.
                    EnforcementDurationSource.AMBIGUOUS
                }
            DurationSource.RECOMMENDATION_IGNORED -> EnforcementDurationSource.RECOMMENDATION
            DurationSource.NONE -> EnforcementDurationSource.NONE
        }

        private fun isSettingsPackage(packageName: String): Boolean =
            packageName == "com.android.settings" ||
                packageName == "com.xiaomi.misettings"

        private fun isSettingsTamper(packageName: String, screenText: String): Boolean {
            if (!isSettingsPackage(packageName)) return false
            val normalized = screenText.lowercase()
            return normalized.contains("phonecodex") &&
                (normalized.contains("accessibility") || normalized.contains("downloaded apps"))
        }
    }
}

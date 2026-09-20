package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.promise.PromiseIntentRules

/**
 * Passive surfaces must never trigger active-behavior enforcement (media-length,
 * short-form quota, AI nudge). Active players / install / payment / DM threads may.
 */
enum class SurfaceActivity {
    PASSIVE,
    ACTIVE
}

enum class SurfaceGateAction {
    /** Hard allow — clear overlay, do not call backend AI. */
    PASS,
    /** Continue local rules / AI. */
    CONTINUE
}

data class SurfaceGateDecision(
    val action: SurfaceGateAction,
    val detection: SurfaceDetection,
    val activity: SurfaceActivity,
    val reason: String
) {
    val isPass: Boolean get() = action == SurfaceGateAction.PASS
}

object SurfaceEnforcementGate {

    const val PASS_REASON = "Surface Gate PASS passive video surface"

    fun classifyActivity(detection: SurfaceDetection): SurfaceActivity =
        if (detection.isActiveBehaviorSurface) SurfaceActivity.ACTIVE else SurfaceActivity.PASSIVE

    /**
     * Hard PASS when the screen is passive for video/short-form law.
     * Adult / permanent guardrails / app-package rules run elsewhere and are unaffected.
     */
    fun evaluate(
        packageName: String,
        screenText: String,
        goal: String,
        structuredMaxBlockMinutes: Int? = null,
        structuredMinBlockMinutes: Int? = null,
        shortFormDailyQuotaLimit: Int? = null
    ): SurfaceGateDecision {
        val detection = SurfaceDetector.detect(packageName, screenText)
        val activity = classifyActivity(detection)

        if (
            BlankVideoTreeGate.isNearBlankAccessibilityTree(screenText) &&
            VideoPlatformRegistry.isVideoOrStreamingPackage(packageName)
        ) {
            return SurfaceGateDecision(
                action = SurfaceGateAction.CONTINUE,
                detection = detection,
                activity = activity,
                reason = "Blank video/movie tree — continue duration/entertainment law"
            )
        }

        if (activity == SurfaceActivity.ACTIVE) {
            return SurfaceGateDecision(
                action = SurfaceGateAction.CONTINUE,
                detection = detection,
                activity = activity,
                reason = "Active behavior surface — continue enforcement"
            )
        }

        val mediaLengthPromise =
            structuredMaxBlockMinutes != null ||
                structuredMinBlockMinutes != null ||
                PromiseIntentRules.hasMediaLengthLimit(goal)
        val shortFormQuotaPromise =
            shortFormDailyQuotaLimit != null ||
                ShortFormQuotaGate.parseDailyShortFormLimit(goal) != null
        val entertainmentBan = PromiseIntentRules.blocksEntertainmentOrMovies(goal)
        val videoPlatform = VideoPlatformRegistry.enforcesMediaSurfaces(packageName)

        // Monk / no-social / no-entertainment is NOT a length clock.
        // Passing Chrome/YouTube Home here is why porn/shorts played after "monk 4 hrs".
        if (entertainmentBan) {
            return SurfaceGateDecision(
                action = SurfaceGateAction.CONTINUE,
                detection = detection,
                activity = activity,
                reason = "Entertainment ban — continue monk/social law"
            )
        }

        // PASS only for length/quota clocks on passive video surfaces — never
        // because the package is YouTube, and never because "no shorts"/monk.
        val lengthOrQuotaClock = mediaLengthPromise || shortFormQuotaPromise
        val shortsBanOnly =
            PromiseIntentRules.blocksShortForm(goal) &&
                !entertainmentBan &&
                !PromiseIntentRules.allowsShortForm(goal)
        if (lengthOrQuotaClock && videoPlatform) {
            return SurfaceGateDecision(
                action = SurfaceGateAction.PASS,
                detection = detection,
                activity = activity,
                reason = PASS_REASON
            )
        }
        if (shortsBanOnly && videoPlatform && !detection.isShortFormPlay) {
            return SurfaceGateDecision(
                action = SurfaceGateAction.PASS,
                detection = detection,
                activity = activity,
                reason = PASS_REASON
            )
        }

        // System / browser chrome passive surfaces (launcher, shade, tab switcher, store).
        if (detection.surface.isSystemOrBrowserPassive) {
            return SurfaceGateDecision(
                action = SurfaceGateAction.PASS,
                detection = detection,
                activity = activity,
                reason = PASS_REASON
            )
        }

        return SurfaceGateDecision(
            action = SurfaceGateAction.CONTINUE,
            detection = detection,
            activity = activity,
            reason = "Passive but no video gate — continue other rules"
        )
    }

    /** Backend AI must not WARN/BLOCK after a surface-gate PASS. */
    fun aiMayWarnOrBlock(gate: SurfaceGateDecision): Boolean = !gate.isPass
}

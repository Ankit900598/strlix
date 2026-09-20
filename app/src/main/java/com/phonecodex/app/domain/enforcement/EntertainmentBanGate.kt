package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.promise.PromiseIntentRules
import com.phonecodex.app.domain.signals.ContentSignalDetector

enum class EntertainmentBanAction {
    NONE,
    BLOCK,
    ALLOW_STUDY
}

/**
 * Category-first entertainment law. GAME / DATING chips need no AI.
 * Monk fail-closes unknown. Study lectures can still play on media apps.
 */
object EntertainmentBanGate {

    private val signals = ContentSignalDetector()

    fun evaluate(
        packageName: String,
        screenText: String,
        goal: String,
        dossier: AppDossier? = null
    ): EntertainmentBanAction {
        if (!PromiseIntentRules.hasCategoryOrLifestyleBan(goal)) {
            return EntertainmentBanAction.NONE
        }
        if (EntertainmentClassDetector.isMonkExemptPackage(packageName)) {
            return EntertainmentBanAction.NONE
        }
        if (isStudyLecture(packageName, screenText) &&
            AppClassResolver.resolve(packageName, screenText) == AppClass.MEDIA
        ) {
            return EntertainmentBanAction.ALLOW_STUDY
        }
        if (PromiseCategoryLaw.shouldBlock(packageName, screenText, goal, dossier)) {
            return EntertainmentBanAction.BLOCK
        }
        return EntertainmentBanAction.NONE
    }

    fun shouldBlock(
        packageName: String,
        screenText: String,
        goal: String,
        dossier: AppDossier? = null
    ): Boolean = evaluate(packageName, screenText, goal, dossier) == EntertainmentBanAction.BLOCK

    fun mustEvaluate(
        packageName: String,
        screenText: String,
        goal: String,
        enforcementScopePackages: Collection<String>
    ): Boolean {
        if (EntertainmentClassDetector.isMonkExemptPackage(packageName)) return false
        if (PromiseIntentRules.isLifestyleEntertainmentBan(goal) &&
            !PromiseIntentRules.namesThisAppOnly(goal)
        ) {
            return true
        }
        if (VideoPlatformRegistry.isInEnforcementScope(packageName, enforcementScopePackages)) {
            return true
        }
        return shouldOverrideNamedScopeAllow(packageName, screenText, goal)
    }

    fun shouldOverrideNamedScopeAllow(
        packageName: String,
        screenText: String,
        goal: String
    ): Boolean {
        if (!PromiseIntentRules.hasCategoryOrLifestyleBan(goal)) return false
        if (PromiseIntentRules.namesThisAppOnly(goal)) return false
        if (EntertainmentClassDetector.isMonkExemptPackage(packageName)) return false
        if (PromiseIntentRules.isLifestyleEntertainmentBan(goal)) return true
        return PromiseCategoryLaw.listingOrClassIsBanned(
            AppClassResolver.resolve(packageName, screenText),
            goal
        )
    }

    private fun isStudyLecture(packageName: String, screenText: String): Boolean {
        val surface = SurfaceDetector.detect(packageName, screenText)
        val detected = signals.detect(packageName, screenText)
        return surface.isActivePlayer &&
            (detected.isLikelySearchOrLecture || detected.isChromeStudyLike)
    }
}

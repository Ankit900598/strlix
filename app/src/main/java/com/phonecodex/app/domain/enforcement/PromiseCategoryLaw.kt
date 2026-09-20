package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.promise.PromiseIntentRules

/**
 * Promise → dossier class → block. Hard chips need no AI.
 * User Education labels never unlock. Merge law is the only judge.
 */
object PromiseCategoryLaw {

    fun shouldBlock(
        packageName: String,
        screenText: String,
        goal: String,
        dossier: AppDossier? = null
    ): Boolean {
        if (!PromiseIntentRules.hasCategoryOrLifestyleBan(goal)) return false
        if (EntertainmentClassDetector.isMonkExemptPackage(packageName)) return false
        val resolved = dossier ?: AppDossier.localOnly(packageName, screenText)
        return AppDossierMergeLaw.shouldBlock(goal, resolved)
    }

    fun listingOrClassIsBanned(appClass: AppClass, goal: String): Boolean {
        return AppDossierMergeLaw.shouldBlock(
            goal,
            AppDossier(packageName = "probe", localClass = appClass)
        )
    }
}

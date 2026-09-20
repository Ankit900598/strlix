package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.promise.PromiseIntentRules

/**
 * Scientist contract for app-class merge.
 *
 * 1. User chip never unlocks.
 * 2. Education never upgrades UNKNOWN into an allow.
 * 3. Dating / game from any trusted signal wins.
 * 4. Girls-chat / monk / no-social: UNKNOWN is guilty.
 * 5. Narrow music/game bans: UNKNOWN is not guilty.
 */
object AppDossierMergeLaw {

    fun effectiveClass(dossier: AppDossier): AppClass {
        val trusted = listOfNotNull(
            dossier.localClass,
            dossier.counselClass,
            dossier.playClass,
            dossier.visionClass
        )
        HARD_TRUTH.firstOrNull { clazz -> trusted.contains(clazz) }?.let { return it }
        listOf(AppClass.SOCIAL, AppClass.COMMUNICATION, AppClass.MEDIA, AppClass.MUSIC)
            .firstOrNull { clazz -> trusted.contains(clazz) }
            ?.let { return it }
        if (trusted.contains(AppClass.UTILITY) &&
            dossier.localClass == AppClass.UTILITY
        ) {
            return AppClass.UTILITY
        }
        return dossier.localClass
    }

    fun userClaimUnlocks(dossier: AppDossier): Boolean = false

    fun shouldBlock(goal: String, dossier: AppDossier): Boolean {
        if (!PromiseIntentRules.hasCategoryOrLifestyleBan(goal)) return false
        if (userClaimUnlocks(dossier)) return false
        val effective = effectiveClass(dossier)
        if (effective == AppClass.UTILITY && dossier.localClass == AppClass.UTILITY) {
            return false
        }
        if (PromiseIntentRules.isLifestyleEntertainmentBan(goal)) {
            return effective != AppClass.UTILITY
        }
        if (PromiseIntentRules.blocksGirlsChatCategory(goal)) {
            return effective in GIRLS_CHAT_FAIL_CLOSED
        }
        if (PromiseIntentRules.blocksSocialCategory(goal)) {
            return effective in SOCIAL_FAIL_CLOSED
        }
        if (PromiseIntentRules.blocksDatingCategory(goal)) {
            return effective == AppClass.DATING || effective == AppClass.UNKNOWN
        }
        if (PromiseIntentRules.blocksGameCategory(goal)) {
            return effective == AppClass.GAME
        }
        if (PromiseIntentRules.blocksMusicCategory(goal)) {
            return effective == AppClass.MUSIC
        }
        if (PromiseIntentRules.blocksMovieCategory(goal)) {
            return effective == AppClass.MEDIA
        }
        return false
    }

    private val HARD_TRUTH = listOf(AppClass.DATING, AppClass.GAME)

    private val GIRLS_CHAT_FAIL_CLOSED = setOf(
        AppClass.DATING,
        AppClass.SOCIAL,
        AppClass.COMMUNICATION,
        AppClass.UNKNOWN,
        AppClass.EDUCATION
    )

    private val SOCIAL_FAIL_CLOSED = setOf(
        AppClass.SOCIAL,
        AppClass.DATING,
        AppClass.MEDIA,
        AppClass.COMMUNICATION,
        AppClass.UNKNOWN
    )
}

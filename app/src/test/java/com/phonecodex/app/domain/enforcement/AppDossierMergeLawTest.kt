package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AppDossierMergeLawTest {

    @Test
    fun userEducationClaim_neverUnlocksGirlsChatBan() {
        val dossier = AppDossier.localOnly("com.xyz.randomchat", "Home Discover")
            .withUserClaim(AppClass.EDUCATION)
        assertFalse(AppDossierMergeLaw.userClaimUnlocks(dossier))
        assertEquals(AppClass.UNKNOWN, AppDossierMergeLaw.effectiveClass(dossier))
        assertTrue(
            AppDossierMergeLaw.shouldBlock("no girls chat for 4 hours", dossier)
        )
        assertTrue(
            EntertainmentBanGate.shouldBlock(
                "com.xyz.randomchat",
                "Home Discover",
                "no girls chat for 4 hours",
                dossier
            )
        )
    }

    @Test
    fun azureCounselDating_beatsUserEducation() {
        val dossier = AppDossier.localOnly("com.xyz.randomchat", "Home")
            .withUserClaim(AppClass.EDUCATION)
            .withCounsel(
                counselClass = AppClass.DATING,
                confidence = 0.9,
                summary = "Live girls video chat",
                source = AppDossier.SOURCE_AZURE_WEB,
                nowMillis = 1L
            )
        assertEquals(AppClass.DATING, AppDossierMergeLaw.effectiveClass(dossier))
        assertTrue(AppDossierMergeLaw.shouldBlock("no dating tonight", dossier))
    }

    @Test
    fun visionDating_beatsEmptyWeb() {
        val dossier = AppDossier.localOnly("com.new.clone", "Login")
            .withVision(AppClass.DATING)
        assertEquals(AppClass.DATING, AppDossierMergeLaw.effectiveClass(dossier))
        assertTrue(AppDossierMergeLaw.shouldBlock("block dating and girls related", dossier))
    }

    @Test
    fun noMusic_unknownDoesNotBrick_spotifyBlocks() {
        val unknown = AppDossier.localOnly("com.xyz.randomchat", "Home")
        assertFalse(AppDossierMergeLaw.shouldBlock("don't listen to music", unknown))
        assertTrue(
            AppDossierMergeLaw.shouldBlock(
                "don't listen to music",
                AppDossier.localOnly("com.spotify.music", "Home")
            )
        )
    }

    @Test
    fun monk_stillFailClosesUnknown() {
        assertTrue(
            AppDossierMergeLaw.shouldBlock(
                "Monk mode for 4 hours. Only calls and study.",
                AppDossier.localOnly("com.xyz.randomchat", "Home")
            )
        )
        assertFalse(
            AppDossierMergeLaw.shouldBlock(
                "Monk mode for 4 hours. Only calls and study.",
                AppDossier.localOnly("com.android.contacts", "Contacts")
            )
        )
    }

    @Test
    fun noGames_doesNotUseGirlsFailClosed() {
        val unknown = AppDossier.localOnly("com.xyz.randomchat", "Home")
        assertFalse(AppDossierMergeLaw.shouldBlock("no games for 4 hours", unknown))
    }
}

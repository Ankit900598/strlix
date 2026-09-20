package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertEquals
import org.junit.Test

class AppClassResolverTest {

    @Test
    fun playListing_datingAndGameAndEducation() {
        assertEquals(
            AppClass.DATING,
            PlayListingCategoryParser.infer("Tinder Dating 4.5 Contains ads Install")
        )
        assertEquals(
            AppClass.GAME,
            PlayListingCategoryParser.infer(
                "Free Fire Games Casual Contains ads In-app purchases Install"
            )
        )
        assertEquals(
            AppClass.EDUCATION,
            PlayListingCategoryParser.infer("Khan Academy Education 4.8 Install")
        )
        assertEquals(
            AppClass.COMMUNICATION,
            PlayListingCategoryParser.infer("Connecto Communication 1M+ Install")
        )
    }

    @Test
    fun resolver_knownPackages() {
        assertEquals(
            AppClass.SOCIAL,
            AppClassResolver.resolve(VideoPlatformRegistry.INSTAGRAM, "Explore")
        )
        assertEquals(
            AppClass.MEDIA,
            AppClassResolver.resolve(VideoPlatformRegistry.YOUTUBE, "Home")
        )
        assertEquals(
            AppClass.DATING,
            AppClassResolver.resolve(EntertainmentClassDetector.FACHAT_FREECHAT, "Home")
        )
        assertEquals(
            AppClass.GAME,
            AppClassResolver.resolve("com.dts.freefireth", "Play now")
        )
        assertEquals(
            AppClass.UTILITY,
            AppClassResolver.resolve("com.android.contacts", "Contacts")
        )
        assertEquals(
            AppClass.UNKNOWN,
            AppClassResolver.resolve("com.xyz.randomchat", "Home Discover")
        )
        assertEquals(
            AppClass.MUSIC,
            AppClassResolver.resolve("com.spotify.music", "Home")
        )
    }
}

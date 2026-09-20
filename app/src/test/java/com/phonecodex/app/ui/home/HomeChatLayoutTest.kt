package com.phonecodex.app.ui.home

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HomeChatLayoutTest {

    @Test
    fun idleHome_usesChatLayout() {
        assertTrue(usesChatHome(hasStoredSession = false, showAdvancedControls = false))
    }

    @Test
    fun activeSession_usesSettingsList() {
        assertFalse(usesChatHome(hasStoredSession = true, showAdvancedControls = false))
    }

    @Test
    fun advancedOpen_usesSettingsList() {
        assertFalse(usesChatHome(hasStoredSession = false, showAdvancedControls = true))
    }

    @Test
    fun idleList_alwaysShowsProtectionStatusAfterHeader() {
        val items = buildHomeListItems(
            hasStoredSession = false,
            hasPromiseUnderstanding = false,
            showAdvancedControls = false
        )
        assertEquals(HomeListItem.Header, items[0])
        assertEquals(HomeListItem.ProtectionStatus, items[1])
        assertFalse(items.contains(HomeListItem.ProtectionSetup))
    }

    @Test
    fun advancedList_putsReliabilityInsideHealthCardNotTwice() {
        val items = buildHomeListItems(
            hasStoredSession = false,
            hasPromiseUnderstanding = false,
            showAdvancedControls = true
        )
        assertEquals(HomeListItem.Header, items[0])
        assertFalse(items.contains(HomeListItem.ProtectionStatus))
        assertTrue(items.contains(HomeListItem.AdvancedProtectionHealth))
    }
}

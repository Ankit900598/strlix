package com.phonecodex.app.domain.promise

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PromiseIntentRulesTest {

    @Test
    fun studyOnlyBlocksShortForm() {
        assertTrue(PromiseIntentRules.blocksShortForm("Only study videos for 30 minutes"))
    }

    @Test
    fun explicitShortsAllowanceWinsForQuotaPromises() {
        assertTrue(PromiseIntentRules.allowsShortForm("Allow 40 shorts today but no adult content"))
    }

    @Test
    fun chromeExceptionDoesNotMeanShortsBan() {
        val goal = "allow everything on chrome except youtube whose length is greater than 20 min for next 1 hrs"

        assertTrue(PromiseIntentRules.allowsBroadChromeUse(goal))
        assertFalse(PromiseIntentRules.blocksShortForm(goal))
    }

    @Test
    fun explicitNoShortsBlocksShortForm() {
        assertTrue(PromiseIntentRules.blocksShortForm("Use YouTube for OS lectures but no shorts"))
    }
}

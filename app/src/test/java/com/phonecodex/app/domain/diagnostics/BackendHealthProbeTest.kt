package com.phonecodex.app.domain.diagnostics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class BackendHealthProbeTest {

    @Test
    fun parseHealth_mapsClassifierMeta() {
        val body = """
            {
              "ok": true,
              "classifier": {
                "provider": "azure",
                "deployment": "pc-lab-cheap",
                "promptVersion": "v04"
              }
            }
        """.trimIndent()

        val meta = BackendHealthProbe.parseHealth(body)

        assertNotNull(meta)
        assertEquals("azure", meta!!.provider)
        assertEquals("pc-lab-cheap", meta.deployment)
        assertEquals("v04", meta.promptVersion)
    }

    @Test
    fun parseHealth_notOk_returnsNull() {
        assertNull(BackendHealthProbe.parseHealth("""{"ok":false}"""))
    }

    @Test
    fun parseClassifySmoke_readsDecision() {
        val smoke = BackendHealthProbe.parseClassifySmoke(
            """{"decision":"ALLOW","reasonCategory":"safe"}"""
        )
        assertTrue(smoke.ok)
        assertEquals("ALLOW", smoke.decision)
        assertEquals("safe", smoke.reasonCategory)
    }

    @Test
    fun parseClassifySmoke_missingDecision_fails() {
        val smoke = BackendHealthProbe.parseClassifySmoke("""{"reason":"x"}""")
        assertFalse(smoke.ok)
    }

    @Test
    fun offlineResult_usesClearStatusString() {
        val offline = BackendProbeResult.offline(latencyMs = 12L)
        assertFalse(offline.reachable)
        assertEquals(BackendHealthProbe.STATUS_OFFLINE, offline.statusLine)
    }
}

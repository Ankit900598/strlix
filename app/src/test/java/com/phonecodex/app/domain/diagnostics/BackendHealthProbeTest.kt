package com.phonecodex.app.domain.diagnostics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.ConnectException

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
    fun classifyFailure_loopbackConnectRefused_isBridgeMissing() {
        val kind = BackendHealthProbe.classifyFailure(
            "http://127.0.0.1:8787",
            ConnectException("Failed to connect to /127.0.0.1:8787")
        )
        assertEquals(BackendProbeKind.BRIDGE_MISSING, kind)
    }

    @Test
    fun hostedHttps_isNotLoopback() {
        assertFalse(
            BackendHealthProbe.isLoopbackBaseUrl("https://example.azurewebsites.net")
        )
    }

    @Test
    fun classifyFailure_nonLoopback_isUnreachable() {
        val kind = BackendHealthProbe.classifyFailure(
            "http://192.168.1.10:8787",
            ConnectException("Connection refused")
        )
        assertEquals(BackendProbeKind.UNREACHABLE, kind)
    }

    @Test
    fun failureResult_bridgeIncludesAdbHint() {
        val result = BackendProbeResult.failure(
            kind = BackendProbeKind.BRIDGE_MISSING,
            latencyMs = 12L,
            detail = "Connection refused"
        )
        assertFalse(result.reachable)
        assertEquals(BackendProbeKind.BRIDGE_MISSING, result.kind)
        assertEquals(BackendHealthProbe.STATUS_BRIDGE_MISSING, result.statusLine)
        assertTrue(result.detail!!.contains("adb reverse tcp:8787 tcp:8787"))
    }

    @Test
    fun resolveDisplay_recentSuccess_staysStaleOkOnFailure() {
        val failed = BackendProbeResult.failure(
            kind = BackendProbeKind.BRIDGE_MISSING,
            latencyMs = 5L,
            detail = "Connection refused"
        )
        val display = BackendHealthProbe.resolveDisplayResult(
            raw = failed,
            checking = false,
            lastSuccessElapsedMs = 1_000L,
            nowElapsedMs = 1_000L + 5_000L,
            staleWindowMs = 60_000L
        )
        assertEquals(BackendProbeKind.STALE_OK, display.kind)
        assertTrue(display.reachable)
        assertEquals(BackendHealthProbe.STATUS_STALE, display.statusLine)
        assertFalse(display.statusLine.contains("offline", ignoreCase = true))
    }

    @Test
    fun resolveDisplay_checking_withRecentSuccess_doesNotLookOffline() {
        val display = BackendHealthProbe.resolveDisplayResult(
            raw = BackendProbeResult.idle(),
            checking = true,
            lastSuccessElapsedMs = 10_000L,
            nowElapsedMs = 12_000L,
            staleWindowMs = 60_000L
        )
        assertEquals(BackendProbeKind.CHECKING, display.kind)
        assertTrue(display.reachable)
        assertEquals(BackendHealthProbe.STATUS_CHECKING, display.statusLine)
    }

    @Test
    fun resolveDisplay_oldSuccess_showsBridgeFailure() {
        val failed = BackendProbeResult.failure(
            kind = BackendProbeKind.BRIDGE_MISSING,
            latencyMs = 5L
        )
        val display = BackendHealthProbe.resolveDisplayResult(
            raw = failed,
            checking = false,
            lastSuccessElapsedMs = 1_000L,
            nowElapsedMs = 1_000L + 120_000L,
            staleWindowMs = 60_000L
        )
        assertEquals(BackendProbeKind.BRIDGE_MISSING, display.kind)
        assertFalse(display.reachable)
        assertTrue(display.detail!!.contains("adb reverse"))
    }

    @Test
    fun idle_isNotScaryOffline() {
        val idle = BackendProbeResult.idle()
        assertEquals(BackendProbeKind.IDLE, idle.kind)
        assertEquals(BackendHealthProbe.STATUS_IDLE, idle.statusLine)
        assertFalse(idle.statusLine.contains("offline", ignoreCase = true))
    }
}

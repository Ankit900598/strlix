package com.phonecodex.app.domain.diagnostics

import android.os.SystemClock
import android.util.Log
import org.json.JSONObject
import java.io.BufferedReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

/**
 * Developer-only smoke probe for the local PhoneCodex backend.
 * Call from a background thread — never from the main thread or composable bodies.
 */
object BackendHealthProbe {

    const val BACKEND_BASE_URL = "http://127.0.0.1:8787"
    const val HEALTH_URL = "$BACKEND_BASE_URL/health"
    const val CLASSIFY_URL = "$BACKEND_BASE_URL/classify"

    const val STATUS_CONNECTED = "Backend connected"
    const val STATUS_OFFLINE = "Backend offline — using local fallback"
    const val STATUS_A11Y_OFF = "Accessibility off — protection cannot work"

    private const val TAG = "PhoneCodexDiag"
    private const val CONNECT_TIMEOUT_MS = 2500
    private const val READ_TIMEOUT_MS = 4000

    fun probe(): BackendProbeResult {
        val started = SystemClock.elapsedRealtime()
        return try {
            val health = fetchHealth()
            if (health == null) {
                val latency = SystemClock.elapsedRealtime() - started
                Log.w(TAG, "Test Backend: health unreachable latencyMs=$latency")
                BackendProbeResult.offline(latencyMs = latency)
            } else {
                val classify = smokeClassify()
                val latency = SystemClock.elapsedRealtime() - started
                Log.i(
                    TAG,
                    "Test Backend: health=ok provider=${health.provider} " +
                        "deployment=${health.deployment} prompt=${health.promptVersion} " +
                        "classifyOk=${classify.ok} decision=${classify.decision} " +
                        "latencyMs=$latency"
                )
                BackendProbeResult(
                    reachable = true,
                    statusLine = STATUS_CONNECTED,
                    provider = health.provider,
                    deployment = health.deployment,
                    promptVersion = health.promptVersion,
                    classifyOk = classify.ok,
                    classifyDecision = classify.decision,
                    classifyReasonCategory = classify.reasonCategory,
                    latencyMs = latency,
                    detail = classify.error
                )
            }
        } catch (err: Exception) {
            val latency = SystemClock.elapsedRealtime() - started
            Log.w(TAG, "Test Backend: failed ${err.javaClass.simpleName}: ${err.message}")
            BackendProbeResult.offline(
                latencyMs = latency,
                detail = err.message
            )
        }
    }

    private fun fetchHealth(): HealthMeta? {
        val connection = (URL(HEALTH_URL).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = CONNECT_TIMEOUT_MS
            readTimeout = READ_TIMEOUT_MS
            setRequestProperty("Accept", "application/json")
        }
        try {
            val code = connection.responseCode
            if (code !in 200..299) {
                Log.w(TAG, "Test Backend: /health HTTP $code")
                return null
            }
            val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use(
                BufferedReader::readText
            )
            return parseHealth(body)
        } finally {
            connection.disconnect()
        }
    }

    internal fun parseHealth(body: String): HealthMeta? {
        return try {
            val json = JSONObject(body)
            if (!json.optBoolean("ok", false)) return null
            val classifier = json.optJSONObject("classifier")
            HealthMeta(
                provider = classifier?.optString("provider")?.ifBlank { null },
                deployment = classifier?.optString("deployment")?.ifBlank { null },
                promptVersion = classifier?.optString("promptVersion")?.ifBlank { null }
            )
        } catch (_: Exception) {
            null
        }
    }

    private fun smokeClassify(): ClassifySmoke {
        val connection = (URL(CLASSIFY_URL).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = CONNECT_TIMEOUT_MS
            readTimeout = READ_TIMEOUT_MS
            doOutput = true
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            setRequestProperty("Accept", "application/json")
        }
        try {
            val requestBody = JSONObject()
                .put("packageName", "com.phonecodex.diag.smoke")
                .put("screenText", "PhoneCodex developer diagnostics smoke test")
                .put("goal", "diagnostics")
                .put("strictnessLevel", "NORMAL")
                .put("commitmentType", "focus")
                .put("activeGuardrails", org.json.JSONArray())
                .toString()

            OutputStreamWriter(connection.outputStream, Charsets.UTF_8).use { writer ->
                writer.write(requestBody)
                writer.flush()
            }

            val code = connection.responseCode
            if (code !in 200..299) {
                Log.w(TAG, "Test Backend: /classify smoke HTTP $code")
                return ClassifySmoke(ok = false, error = "HTTP $code")
            }

            val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use(
                BufferedReader::readText
            )
            return parseClassifySmoke(body)
        } catch (err: Exception) {
            return ClassifySmoke(ok = false, error = err.message)
        } finally {
            connection.disconnect()
        }
    }

    internal fun parseClassifySmoke(body: String): ClassifySmoke {
        return try {
            val json = JSONObject(body)
            val decision = json.optString("decision").ifBlank { null }
            if (decision == null) {
                ClassifySmoke(ok = false, error = "missing decision")
            } else {
                ClassifySmoke(
                    ok = true,
                    decision = decision,
                    reasonCategory = json.optString("reasonCategory").ifBlank { null }
                )
            }
        } catch (err: Exception) {
            ClassifySmoke(ok = false, error = err.message)
        }
    }

    data class HealthMeta(
        val provider: String?,
        val deployment: String?,
        val promptVersion: String?
    )

    data class ClassifySmoke(
        val ok: Boolean,
        val decision: String? = null,
        val reasonCategory: String? = null,
        val error: String? = null
    )
}

data class BackendProbeResult(
    val reachable: Boolean,
    val statusLine: String,
    val provider: String?,
    val deployment: String?,
    val promptVersion: String?,
    val classifyOk: Boolean?,
    val classifyDecision: String?,
    val classifyReasonCategory: String?,
    val latencyMs: Long?,
    val detail: String?
) {
    companion object {
        fun offline(latencyMs: Long?, detail: String? = null): BackendProbeResult =
            BackendProbeResult(
                reachable = false,
                statusLine = BackendHealthProbe.STATUS_OFFLINE,
                provider = null,
                deployment = null,
                promptVersion = null,
                classifyOk = null,
                classifyDecision = null,
                classifyReasonCategory = null,
                latencyMs = latencyMs,
                detail = detail
            )

        fun idle(): BackendProbeResult =
            BackendProbeResult(
                reachable = false,
                statusLine = "Not tested yet",
                provider = null,
                deployment = null,
                promptVersion = null,
                classifyOk = null,
                classifyDecision = null,
                classifyReasonCategory = null,
                latencyMs = null,
                detail = null
            )
    }
}

package com.phonecodex.app.domain.promise

import android.util.Log
import com.phonecodex.app.domain.diagnostics.BackendConfig
import com.phonecodex.app.domain.diagnostics.BackendHealthProbe
import org.json.JSONObject
import java.io.BufferedReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

/**
 * Calls backend POST /compile-promise. Call from a background thread / IO dispatcher.
 * On any failure throws [PromiseCompilerException] — caller must fall back to local parser.
 */
class PromiseCompilerClient(
    private val baseUrl: String = BackendHealthProbe.BACKEND_BASE_URL,
    private val connectTimeoutMs: Int = CONNECT_TIMEOUT_MS,
    private val readTimeoutMs: Int = READ_TIMEOUT_MS
) {

    fun compile(
        promise: String,
        selectedClarificationOptionId: String? = null
    ): CompiledPromiseResponse {
        val trimmed = promise.trim()
        require(trimmed.isNotEmpty()) { "promise must be non-empty" }

        Log.i(
            TAG,
            "compile request started len=${trimmed.length} selected=${selectedClarificationOptionId ?: "none"}"
        )
        val url = URL("$baseUrl/compile-promise")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = connectTimeoutMs
            readTimeout = readTimeoutMs
            doOutput = true
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            setRequestProperty("Accept", "application/json")
            BackendConfig.applyAuth(this)
        }

        try {
            val bodyJson = JSONObject().put("promise", trimmed)
            selectedClarificationOptionId
                ?.trim()
                ?.takeIf { it.isNotEmpty() }
                ?.let { bodyJson.put("selectedClarificationOptionId", it) }
            val body = bodyJson.toString()
            OutputStreamWriter(connection.outputStream, Charsets.UTF_8).use { writer ->
                writer.write(body)
                writer.flush()
            }

            val code = connection.responseCode
            val responseText = (
                if (code in 200..299) connection.inputStream else connection.errorStream
            )?.bufferedReader(Charsets.UTF_8)?.use(BufferedReader::readText).orEmpty()

            if (code !in 200..299) {
                val errMsg = try {
                    JSONObject(responseText).optString("error").ifBlank { "HTTP $code" }
                } catch (_: Exception) {
                    "HTTP $code"
                }
                Log.w(TAG, "compile failure HTTP $code: ${errMsg.take(120)}")
                throw PromiseCompilerException(errMsg, code)
            }

            val parsed = CompiledPromiseResponseParser.parse(responseText)
                ?: throw PromiseCompilerException("Invalid compile-promise response", code)
            Log.i(
                TAG,
                "compile success clarificationRequired=${parsed.clarificationRequired} " +
                    "canStart=${parsed.canStartCommitment} options=${parsed.clarificationOptions.size}"
            )
            return parsed
        } catch (err: PromiseCompilerException) {
            throw err
        } catch (err: Exception) {
            Log.w(TAG, "compile failure network: ${err.message}")
            throw PromiseCompilerException(err.message ?: "network error", cause = err)
        } finally {
            connection.disconnect()
        }
    }

    companion object {
        private const val TAG = "PromiseCompiler"
        const val CONNECT_TIMEOUT_MS = 3000
        const val READ_TIMEOUT_MS = 45_000
    }
}

class PromiseCompilerException(
    message: String,
    val httpStatus: Int? = null,
    cause: Throwable? = null
) : Exception(message, cause)

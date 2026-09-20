package com.phonecodex.app.domain.diagnostics

import com.phonecodex.app.BuildConfig
import java.net.HttpURLConnection

/**
 * Where the phone talks to Promise Compiler / classify.
 *
 * Debug default is loopback (USB `adb reverse`). Closed-beta builds set
 * `strlix.backendUrl` + `strlix.backendSecret` in `local.properties` (not git).
 */
object BackendConfig {

    val baseUrl: String
        get() = BuildConfig.BACKEND_BASE_URL.trim().trimEnd('/')

    val appSecret: String
        get() = BuildConfig.BACKEND_APP_SECRET.trim()

    const val APP_SECRET_HEADER = "X-Strlix-App-Secret"

    fun applyAuth(connection: HttpURLConnection) {
        val secret = appSecret
        if (secret.isNotEmpty()) {
            connection.setRequestProperty(APP_SECRET_HEADER, secret)
        }
    }
}

package com.phonecodex.app.protection

import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat
import com.phonecodex.app.data.SessionStore
import com.phonecodex.app.domain.protection.ProtectionHeartbeatLogic

object ProtectionHeartbeatController {

    fun start(context: Context) {
        val appContext = context.applicationContext
        val intent = Intent(appContext, ProtectionHeartbeatService::class.java)
        ContextCompat.startForegroundService(appContext, intent)
    }

    fun stop(context: Context) {
        val appContext = context.applicationContext
        appContext.stopService(Intent(appContext, ProtectionHeartbeatService::class.java))
    }

    fun ensureRunningIfNeeded(context: Context) {
        val session = SessionStore(context.applicationContext).getStoredSession()
        if (ProtectionHeartbeatLogic.shouldKeepRunning(session)) {
            start(context)
        } else {
            stop(context)
        }
    }
}

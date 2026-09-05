package com.phonecodex.app.ui.home

import android.os.SystemClock
import android.util.Log
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import com.phonecodex.app.accessibility.AccessibilityHealthChecker
import com.phonecodex.app.data.ProtectionViolationStore
import com.phonecodex.app.domain.model.SessionStatus
import com.phonecodex.app.domain.session.SessionExpiryPolicy
import com.phonecodex.app.protection.ProtectionHeartbeatController
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

/**
 * Core home polling: accessibility + session only.
 * Debug / events poll is a separate effect gated on inspector visibility.
 */
@Composable
internal fun HomeScreenPollingEffect(state: HomeScreenState) {
    LaunchedEffect(Unit) {
        ProtectionHeartbeatController.ensureRunningIfNeeded(state.context)
    }

    LaunchedEffect(state.showAdvancedControls) {
        if (state.showAdvancedControls) {
            state.loadAdvancedSnapshotIfNeeded()
        }
    }

    LaunchedEffect(Unit) {
        while (true) {
            val started = SystemClock.elapsedRealtime()
            pollCoreHomeState(state)
            val elapsed = SystemClock.elapsedRealtime() - started
            if (elapsed > 50L) {
                Log.d("PhoneCodexUIPerf", "corePoll=${elapsed}ms")
            }
            delay(if (state.hasStoredSession) CORE_POLL_ACTIVE_MS else CORE_POLL_IDLE_MS)
        }
    }
}

/**
 * Debug + event prefs poll. Runs only while the inspector region is on-screen.
 */
@Composable
internal fun HomeAdvancedInspectorPollingEffect(
    state: HomeScreenState,
    inspectorVisible: () -> Boolean
) {
    LaunchedEffect(state.showAdvancedControls) {
        if (!state.showAdvancedControls) return@LaunchedEffect
        while (true) {
            if (!inspectorVisible()) {
                delay(ADVANCED_POLL_IDLE_CHECK_MS)
                continue
            }
            val started = SystemClock.elapsedRealtime()
            pollInspectorHomeState(state)
            Log.d(
                "PhoneCodexUIPerf",
                "debugPoll=${SystemClock.elapsedRealtime() - started}ms"
            )
            delay(ADVANCED_POLL_MS)
        }
    }
}

private suspend fun pollCoreHomeState(state: HomeScreenState) {
    val accessibilityEnabled = withContext(Dispatchers.IO) {
        AccessibilityHealthChecker.isPhoneCodexAccessibilityEnabled(state.context)
    }
    if (accessibilityEnabled != state.isAccessibilityEnabled) {
        state.isAccessibilityEnabled = accessibilityEnabled
    }

    val nowMillis = System.currentTimeMillis()
    val currentSession = withContext(Dispatchers.IO) {
        state.sessionStore.getStoredSession()
    }

    if (
        currentSession != null &&
        SessionExpiryPolicy.isExpired(currentSession, nowMillis)
    ) {
        withContext(Dispatchers.IO) {
            state.sessionStore.clearSession()
            state.eventLogStore.addEvent(SessionExpiryPolicy.EXPIRED_EVENT_MESSAGE)
        }
        ProtectionHeartbeatController.stop(state.context)
        if (state.showAdvancedControls) {
            state.recentEvents = withContext(Dispatchers.IO) {
                state.eventLogStore.getRecentEvents()
            }
        }
        if (state.session != null) {
            state.session = null
        }
        return
    }

    if (currentSession != state.session) {
        state.session = currentSession
    }

    val hasActiveOrLockedSession = currentSession?.let { stored ->
        stored.status == SessionStatus.ACTIVE || stored.status == SessionStatus.LOCKED
    } == true

    if (hasActiveOrLockedSession && state.nowMillis != nowMillis) {
        state.nowMillis = nowMillis
    }

    if (!accessibilityEnabled && hasActiveOrLockedSession) {
        withContext(Dispatchers.IO) {
            state.protectionViolationStore.recordViolation(
                ProtectionViolationStore.REASON_ACCESSIBILITY_DISABLED_DURING_COMMITMENT
            )
        }
        if (state.showAdvancedControls) {
            val violationState = withContext(Dispatchers.IO) {
                state.protectionViolationStore.getState()
            }
            if (violationState != state.protectionViolationState) {
                state.protectionViolationState = violationState
            }
        }
    }
}

private suspend fun pollInspectorHomeState(state: HomeScreenState) {
    val debugState = withContext(Dispatchers.IO) {
        state.debugStateStore.getDebugState()
    }
    if (debugState != state.debugState) {
        state.debugState = debugState
    }

    val recentEvents = withContext(Dispatchers.IO) {
        state.eventLogStore.getRecentEvents()
    }
    if (recentEvents != state.recentEvents) {
        state.recentEvents = recentEvents
    }

    val violationState = withContext(Dispatchers.IO) {
        state.protectionViolationStore.getState()
    }
    if (violationState != state.protectionViolationState) {
        state.protectionViolationState = violationState
    }

    val accessibilityAlive = withContext(Dispatchers.IO) {
        state.runtimeDiagStore.isAccessibilityServiceAlive()
    }
    if (accessibilityAlive != state.isAccessibilityAlive) {
        state.isAccessibilityAlive = accessibilityAlive
    }

    val overlayActive = withContext(Dispatchers.IO) {
        state.runtimeDiagStore.isOverlayActive()
    }
    if (overlayActive != state.overlayActive) {
        state.overlayActive = overlayActive
    }
}

private const val CORE_POLL_IDLE_MS = 3_000L
private const val CORE_POLL_ACTIVE_MS = 1_000L
private const val ADVANCED_POLL_MS = 2_500L
private const val ADVANCED_POLL_IDLE_CHECK_MS = 500L

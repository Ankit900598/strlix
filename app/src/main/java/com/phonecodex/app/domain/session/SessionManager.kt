package com.phonecodex.app.domain.session

import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.FocusWorld
import com.phonecodex.app.domain.model.SessionStatus

class SessionManager {
    private var currentSession: FocusSession? = null

    fun getActiveSession(): FocusSession? = currentSession

    fun startSession(
        world: FocusWorld,
        goal: String,
        durationMillis: Long,
        nowMillis: Long
    ): FocusSession {
        val session = FocusSession(
            id = "session-$nowMillis",
            worldId = world.id,
            goal = goal,
            startTimeMillis = nowMillis,
            deadlineMillis = nowMillis + durationMillis,
            status = SessionStatus.ACTIVE,
            attemptCount = 0,
            strictness = world.defaultStrictness
        )
        currentSession = session
        return session
    }

    fun stopSession(nowMillis: Long): FocusSession? {
        val updatedSession = currentSession?.copy(status = SessionStatus.ENDED)
        currentSession = updatedSession
        return updatedSession
    }

    fun incrementAttempt(): FocusSession? {
        val updatedSession = currentSession?.copy(
            attemptCount = currentSession?.attemptCount?.plus(1) ?: 1
        )
        currentSession = updatedSession
        return updatedSession
    }

    fun lockSession(): FocusSession? {
        val updatedSession = currentSession?.copy(status = SessionStatus.LOCKED)
        currentSession = updatedSession
        return updatedSession
    }

    fun clearSession() {
        currentSession = null
    }
}

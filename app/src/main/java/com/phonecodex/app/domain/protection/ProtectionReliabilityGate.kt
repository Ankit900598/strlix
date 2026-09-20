package com.phonecodex.app.domain.protection

import com.phonecodex.app.domain.diagnostics.BackendHealthProbe
import com.phonecodex.app.domain.diagnostics.BackendProbeKind

enum class ProtectionReliabilityLevel {
    PROTECTED,
    NOT_PROTECTING,
    NEEDS_SETUP
}

enum class ProtectionPrimaryAction {
    NONE,
    OPEN_ACCESSIBILITY
}

data class ProtectionReliabilityInput(
    val accessibilityEnabled: Boolean,
    val accessibilityAlive: Boolean,
    val lastEventMillis: Long,
    val lastEventPackage: String?,
    val lastEventReason: String?,
    val hasActiveCommitment: Boolean,
    val permanentGuardrailOn: Boolean,
    val backendKind: BackendProbeKind,
    val backendLoopback: Boolean = true,
    val nowMillis: Long
)

data class ProtectionReliabilityUiModel(
    val level: ProtectionReliabilityLevel,
    val headline: String,
    val summary: String,
    val accessibilityLine: String,
    val commitmentLine: String,
    val guardrailLine: String,
    val backendLine: String,
    val lastEventLine: String,
    val primaryAction: ProtectionPrimaryAction,
    val primaryActionLabel: String?,
    val nothingEnforced: Boolean,
    val showAdbReverseHint: Boolean,
    val adbReverseHint: String,
    val checkLogLine: String
) {
    val isProtected: Boolean get() = level == ProtectionReliabilityLevel.PROTECTED
}

/**
 * Proves the enforcement loop is alive before Chrome/YouTube tests.
 * Does not start a promise. Does not change PolicyEngine or emergency allows.
 */
object ProtectionReliabilityGate {

    const val HEADLINE_PROTECTED = "Protected"
    const val HEADLINE_NOT_PROTECTING = "Not protecting"
    const val HEADLINE_NEEDS_SETUP = "Needs setup"
    const val NOTHING_ENFORCED = "Nothing is enforced."
    const val ADB_REVERSE = "adb reverse tcp:8787 tcp:8787"
    const val ACTION_TURN_ON = "Turn on protection"

    fun evaluate(input: ProtectionReliabilityInput): ProtectionReliabilityUiModel {
        val ageMs = AccessibilityHeartbeatLaw.ageMs(input.nowMillis, input.lastEventMillis)
        val heartbeatFresh = AccessibilityHeartbeatLaw.isFresh(ageMs)
        val loopAlive = input.accessibilityEnabled &&
            (input.accessibilityAlive || heartbeatFresh)
        val hasLaw = input.hasActiveCommitment || input.permanentGuardrailOn
        val nothingEnforced = loopAlive && !hasLaw

        val level = when {
            !input.accessibilityEnabled -> ProtectionReliabilityLevel.NEEDS_SETUP
            !loopAlive -> ProtectionReliabilityLevel.NOT_PROTECTING
            !hasLaw -> ProtectionReliabilityLevel.NOT_PROTECTING
            else -> ProtectionReliabilityLevel.PROTECTED
        }

        val headline = when (level) {
            ProtectionReliabilityLevel.PROTECTED -> HEADLINE_PROTECTED
            ProtectionReliabilityLevel.NOT_PROTECTING -> HEADLINE_NOT_PROTECTING
            ProtectionReliabilityLevel.NEEDS_SETUP -> HEADLINE_NEEDS_SETUP
        }

        val summary = when {
            !input.accessibilityEnabled ->
                "Accessibility is off. The phone cannot enforce anything."
            !loopAlive ->
                "Accessibility is not bound. Enforcement is dead."
            nothingEnforced ->
                "$NOTHING_ENFORCED Start a promise or turn on a life rule."
            else ->
                "The enforcement loop is alive."
        }

        val accessibilityLine = when {
            !input.accessibilityEnabled -> "Off"
            loopAlive -> "Alive"
            else -> "Enabled but not alive"
        }
        val commitmentLine = if (input.hasActiveCommitment) "Active" else "None"
        val guardrailLine = if (input.permanentGuardrailOn) "On" else "Off"
        val backendLine = backendLine(input.backendKind)
        val lastEventLine = AccessibilityHeartbeatLaw.formatAge(ageMs)

        val needsAccessibilityAction =
            !input.accessibilityEnabled || (input.accessibilityEnabled && !loopAlive)
        val primaryAction = if (needsAccessibilityAction) {
            ProtectionPrimaryAction.OPEN_ACCESSIBILITY
        } else {
            ProtectionPrimaryAction.NONE
        }

        val showAdb = input.backendKind == BackendProbeKind.BRIDGE_MISSING &&
            input.backendLoopback

        val checkLogLine = listOf(
            headline,
            "a11y=$accessibilityLine",
            "commitment=$commitmentLine",
            "guardrail=$guardrailLine",
            "backend=$backendLine",
            lastEventLine
        ).joinToString("; ")

        return ProtectionReliabilityUiModel(
            level = level,
            headline = headline,
            summary = summary,
            accessibilityLine = accessibilityLine,
            commitmentLine = commitmentLine,
            guardrailLine = guardrailLine,
            backendLine = backendLine,
            lastEventLine = lastEventLine,
            primaryAction = primaryAction,
            primaryActionLabel = if (needsAccessibilityAction) ACTION_TURN_ON else null,
            nothingEnforced = nothingEnforced,
            showAdbReverseHint = showAdb,
            adbReverseHint = if (showAdb) ADB_REVERSE else "",
            checkLogLine = checkLogLine
        )
    }

    private fun backendLine(kind: BackendProbeKind): String = when (kind) {
        BackendProbeKind.REACHABLE -> "Reachable"
        BackendProbeKind.STALE_OK -> "OK recently"
        BackendProbeKind.BRIDGE_MISSING -> "Bridge missing"
        BackendProbeKind.UNREACHABLE -> "Unreachable"
        BackendProbeKind.CHECKING -> "Checking"
        BackendProbeKind.IDLE -> "Not tested"
    }

    fun backendLoopback(baseUrl: String = BackendHealthProbe.BACKEND_BASE_URL): Boolean =
        BackendHealthProbe.isLoopbackBaseUrl(baseUrl)
}

package com.phonecodex.app.domain.policy

import com.phonecodex.app.domain.enforcement.SessionLockLaw
import com.phonecodex.app.domain.model.ContextSnapshot
import com.phonecodex.app.domain.model.DecisionSource
import com.phonecodex.app.domain.model.DecisionType
import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.FocusWorld
import com.phonecodex.app.domain.model.PolicyDecision
import com.phonecodex.app.domain.model.RiskLevel
import com.phonecodex.app.domain.model.SessionStatus
import com.phonecodex.app.domain.model.StrictnessLevel

class PolicyEngine {

    fun evaluate(
        world: FocusWorld,
        session: FocusSession?,
        context: ContextSnapshot
    ): PolicyDecision {
        if (session == null) {
            return rule(
                decision = DecisionType.ALLOW,
                riskLevel = RiskLevel.LOW,
                reason = "No active session"
            )
        }

        if (session.status != SessionStatus.ACTIVE && session.status != SessionStatus.LOCKED) {
            return rule(
                decision = DecisionType.ALLOW,
                riskLevel = RiskLevel.LOW,
                reason = "Session is not active"
            )
        }

        val packageName = context.packageName
        if (session.status == SessionStatus.LOCKED) {
            if (packageName == null ||
                SessionLockLaw.mayUseAppWhileLocked(
                    packageName,
                    context.screenText.orEmpty(),
                    session.goal.orEmpty()
                )
            ) {
                return rule(
                    decision = DecisionType.ALLOW,
                    riskLevel = RiskLevel.LOW,
                    reason = "Session locked on entertainment only"
                )
            }
            if (packageName in world.allowedPackages) {
                return rule(
                    decision = DecisionType.ALLOW,
                    riskLevel = RiskLevel.LOW,
                    reason = "$packageName is allowed in ${world.name}"
                )
            }
            return rule(
                decision = DecisionType.LOCK,
                riskLevel = RiskLevel.HIGH,
                reason = "Session locked on this entertainment surface"
            )
        }
        if (packageName == null) {
            return rule(
                decision = DecisionType.WARN,
                riskLevel = RiskLevel.LOW,
                reason = "Unknown current app"
            )
        }

        if (packageName in world.allowedPackages) {
            return rule(
                decision = DecisionType.ALLOW,
                riskLevel = RiskLevel.LOW,
                reason = "$packageName is allowed in ${world.name}"
            )
        }

        if (packageName in world.blockedPackages) {
            return rule(
                decision = if (session.status == SessionStatus.LOCKED) {
                    DecisionType.LOCK
                } else {
                    DecisionType.BLOCK
                },
                riskLevel = RiskLevel.MEDIUM,
                reason = "$packageName is blocked in ${world.name}"
            )
        }

        if (packageName in world.conditionalPackages) {
            return decideConditionalByStrictness(
                strictness = session.strictness,
                reason = "$packageName is conditional in ${world.name} under ${session.strictness.name}"
            )
        }

        return decideUnknownByStrictness(
            strictness = session.strictness,
            reason = "$packageName is unknown in ${world.name} under ${session.strictness.name}"
        )
    }

    private fun decideConditionalByStrictness(
        strictness: StrictnessLevel,
        reason: String
    ): PolicyDecision {
        return when (strictness) {
            StrictnessLevel.SOFT -> rule(
                decision = DecisionType.WARN,
                riskLevel = RiskLevel.LOW,
                reason = reason
            )
            StrictnessLevel.SMART -> rule(
                decision = DecisionType.ASK,
                riskLevel = RiskLevel.MEDIUM,
                reason = reason
            )
            // Unknown inside-app content: warn, do not hard-block.
            StrictnessLevel.STRICT -> rule(
                decision = DecisionType.WARN,
                riskLevel = RiskLevel.MEDIUM,
                reason = reason
            )
            StrictnessLevel.LOCKED -> rule(
                decision = DecisionType.BLOCK,
                riskLevel = RiskLevel.HIGH,
                reason = reason
            )
        }
    }

    private fun decideUnknownByStrictness(
        strictness: StrictnessLevel,
        reason: String
    ): PolicyDecision {
        return when (strictness) {
            StrictnessLevel.SOFT -> rule(
                decision = DecisionType.WARN,
                riskLevel = RiskLevel.LOW,
                reason = reason
            )
            StrictnessLevel.SMART -> rule(
                decision = DecisionType.ASK,
                riskLevel = RiskLevel.MEDIUM,
                reason = reason
            )
            StrictnessLevel.STRICT -> rule(
                decision = DecisionType.WARN,
                riskLevel = RiskLevel.MEDIUM,
                reason = reason
            )
            StrictnessLevel.LOCKED -> rule(
                decision = DecisionType.BLOCK,
                riskLevel = RiskLevel.HIGH,
                reason = reason
            )
        }
    }

    private fun rule(
        decision: DecisionType,
        riskLevel: RiskLevel,
        reason: String
    ): PolicyDecision {
        return PolicyDecision(
            decision = decision,
            confidence = 1.0,
            reason = reason,
            riskLevel = riskLevel,
            source = DecisionSource.LOCAL_RULE
        )
    }

}

package com.phonecodex.app.accessibility

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.util.concurrent.Executors
import com.phonecodex.app.data.AppRulesStore
import com.phonecodex.app.data.DebugStateStore
import com.phonecodex.app.data.EventLogStore
import com.phonecodex.app.data.FeedbackStore
import com.phonecodex.app.data.PermanentGuardrailsStore
import com.phonecodex.app.data.ProtectionViolationStore
import com.phonecodex.app.data.RuntimeDiagStore
import com.phonecodex.app.data.SessionStore
import com.phonecodex.app.data.SafeAppsStore
import com.phonecodex.app.data.StudyWorldSettingsStore
import com.phonecodex.app.domain.classifier.ClassifyRequestBuilder
import com.phonecodex.app.domain.classifier.ContentClassification
import com.phonecodex.app.domain.classifier.ContentClassifier
import com.phonecodex.app.domain.classifier.AiConfidenceGate
import com.phonecodex.app.domain.classifier.NetworkAiContentClassifier
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.ContextSnapshot
import com.phonecodex.app.domain.model.DecisionExplanation
import com.phonecodex.app.domain.model.DecisionType
import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.FocusWorld
import com.phonecodex.app.domain.model.PolicyDecision
import com.phonecodex.app.domain.model.SessionStatus
import com.phonecodex.app.domain.model.StrictnessLevel
import com.phonecodex.app.domain.model.WorldMode
import com.phonecodex.app.domain.policy.PolicyEngine
import com.phonecodex.app.domain.feedback.FeedbackMemory
import com.phonecodex.app.domain.guardrail.PermanentGuardrailEvaluator
import com.phonecodex.app.domain.session.SessionExpiryPolicy
import com.phonecodex.app.domain.signals.ContentSignalDetector
import com.phonecodex.app.domain.tamper.AccessibilityTamperGuard

class PhoneCodexAccessibilityService : AccessibilityService() {

    private val policyEngine = PolicyEngine()
    private val contentSignalDetector = ContentSignalDetector()
    private val contentClassifier: ContentClassifier = NetworkAiContentClassifier()
    private val aiConfidenceGate = AiConfidenceGate()
    private val sessionStore by lazy { SessionStore(this) }
    private val eventLogStore by lazy { EventLogStore(this) }
    private val debugStateStore by lazy { DebugStateStore(this) }
    private val runtimeDiagStore by lazy { RuntimeDiagStore(this) }
    private val appRulesStore by lazy { AppRulesStore(this) }
    private val studyWorldSettingsStore by lazy { StudyWorldSettingsStore(this) }
    private val feedbackStore by lazy { FeedbackStore(this) }
    private val feedbackMemory by lazy { FeedbackMemory(feedbackStore) }
    private val permanentGuardrailEvaluator = PermanentGuardrailEvaluator()
    private val permanentGuardrailsStore by lazy { PermanentGuardrailsStore(this) }
    private val safeAppsStore by lazy { SafeAppsStore(this) }
    private val accessibilityTamperGuard = AccessibilityTamperGuard()
    private val protectionViolationStore by lazy { ProtectionViolationStore(this) }
    private var currentOverlay: View? = null
    private var currentWarningOverlay: View? = null
    /**
     * External package the block overlay is currently protecting against.
     * When non-null, foreground events from [OWN_PACKAGE_NAME] are caused by our overlay
     * and must not trigger hide.
     */
    private var activeOverlayTargetPackage: String? = null
    /** Last external package we blocked (survives hide, for diagnostics). */
    private var lastBlockedPackage: String? = null
    private var latestPackageName: String? = null
    private var visibleWarningPackageName: String? = null
    private var visibleWarningTextSignature: String? = null
    private var dismissedWarningPackageName: String? = null
    private var dismissedWarningTextSignature: String? = null
    private var dismissedWarningTimeMillis: Long = 0L
    private var overlayAwayCandidatePackage: String? = null
    private var overlayAwaySinceMillis: Long = 0L
    private val mainHandler = Handler(Looper.getMainLooper())
    private val classifierExecutor = Executors.newSingleThreadExecutor()

    private var lastClassifiedPackage: String? = null
    private var lastClassifiedTextSignature: String? = null
    private var lastClassification: ContentClassification? = null
    private var lastClassificationTimeMillis: Long = 0L
    private var lastClassificationRequestTimeMillis: Long = 0L
    private var lastClassificationRequestPackage: String? = null
    private var classificationInFlight: Boolean = false
    private var lastNoSessionLoggedPackage: String? = null
    private var lastLoggedA11yTextPackage: String? = null
    private var lastLoggedA11yTextSignature: String? = null
    private var lastCountedBlockPackage: String? = null
    private var lastCountedBlockSignature: String? = null
    private var lastCountedBlockTimeMillis: Long = 0L
    private var lastSafeAppLoggedPackage: String? = null
    private var lastSafeAppLoggedTimeMillis: Long = 0L
    private var latestExplanation: DecisionExplanation? = null

    private val debugWorld = FocusWorld(
        id = "study",
        name = "Study World",
        mode = WorldMode.STUDY,
        defaultStrictness = StrictnessLevel.STRICT,
        allowedPackages = setOf(
            "com.phonecodex.app",
            "com.android.systemui",
            "miui.systemui.plugin",
            "com.miui.home",
            "com.android.settings",
            "com.xiaomi.misettings",
            "com.android.dialer",
            "com.google.android.dialer",
            "com.android.phone"
        ),
        blockedPackages = emptySet(),
        conditionalPackages = emptySet()
    )

    override fun onServiceConnected() {
        super.onServiceConnected()
        runtimeDiagStore.setAccessibilityServiceAlive(true)
        handleProtectionViolationConsequences()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        when (event.eventType) {
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                val packageName = event.packageName?.toString() ?: return
                Log.d("PhoneCodexA11y", "Foreground package: $packageName")
                inspectAndEvaluate(packageName)
            }

            AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                val packageName = event.packageName?.toString()
                    ?: rootInActiveWindow?.packageName?.toString()
                    ?: return
                inspectAndEvaluate(packageName)
            }

            else -> return
        }
    }

    override fun onInterrupt() {
    }

    override fun onDestroy() {
        hideWarningOverlay()
        hideBlockOverlay()
        runtimeDiagStore.setAccessibilityServiceAlive(false)
        runtimeDiagStore.setOverlayActive(false)
        super.onDestroy()
    }

    private fun handleProtectionViolationConsequences() {
        if (!protectionViolationStore.consumePendingConsequences()) return

        val violationState = protectionViolationStore.getState()
        if (violationState.violationCount <= 0) return

        val storedSession = sessionStore.getStoredSession() ?: return
        if (
            storedSession.status != SessionStatus.ACTIVE &&
            storedSession.status != SessionStatus.LOCKED
        ) {
            return
        }

        eventLogStore.addEvent("Protection violation detected during active Study World")

        if (storedSession.status == SessionStatus.ACTIVE) {
            sessionStore.lockSession()
            eventLogStore.addEvent("Study World locked because protection was disabled.")
            Log.d(
                "PhoneCodexDecision",
                "Study World locked because protection was disabled."
            )
        }
    }

    private fun endExpiredStudyWorldIfNeeded(storedSession: FocusSession?): FocusSession? {
        val session = storedSession ?: return null
        if (!SessionExpiryPolicy.isExpired(session, System.currentTimeMillis())) {
            return session
        }

        sessionStore.clearSession()
        hideWarningOverlay()
        hideBlockOverlay()
        eventLogStore.addEvent(SessionExpiryPolicy.EXPIRED_EVENT_MESSAGE)
        Log.d("PhoneCodexDecision", SessionExpiryPolicy.EXPIRED_EVENT_MESSAGE)
        return null
    }

    private fun inspectAndEvaluate(packageName: String) {
        latestPackageName = packageName

        val screenText = collectScreenText(packageName)
        debugStateStore.recordPackageDetected(packageName, screenText)

        var storedSession = endExpiredStudyWorldIfNeeded(sessionStore.getStoredSession())
        if (
            storedSession != null &&
            (storedSession.status == SessionStatus.ACTIVE ||
                storedSession.status == SessionStatus.LOCKED)
        ) {
            if (applyAccessibilityTamperGuard(packageName, screenText)) {
                return
            }
        }

        // Overlay self-hide guard: must run BEFORE safe-app handling.
        // Showing TYPE_ACCESSIBILITY_OVERLAY makes the foreground package look like
        // com.phonecodex.app; treating that as "safe" used to hide the overlay in a loop.
        if (handleActiveOverlayForeground(packageName)) {
            return
        }

        if (safeAppsStore.isSafePackage(packageName)) {
            hideWarningOverlay()
            // No active overlay target here — normal PhoneCodex / safe-app open.
            val now = System.currentTimeMillis()
            val shouldLogSafeApp = packageName != lastSafeAppLoggedPackage ||
                now - lastSafeAppLoggedTimeMillis >= SAFE_APP_LOG_THROTTLE_MS
            if (shouldLogSafeApp) {
                recordExplanation(
                    packageName = packageName,
                    screenText = screenText,
                    explanation = DecisionExplanation(
                        decision = DecisionType.ALLOW.name,
                        reason = "Always allowed safe app",
                        source = "Safe App",
                        confidence = 1.0
                    )
                )
                Log.d("PhoneCodexDecision", "Safe app allowed: $packageName")
                lastSafeAppLoggedPackage = packageName
                lastSafeAppLoggedTimeMillis = now
            }
            return
        }

        logScreenTextIfChanged(packageName, screenText)

        if (isSystemOverlayNoise(packageName)) return

        if (applyPermanentGuardrails(packageName, screenText)) {
            return
        }

        if (storedSession == null) {
            hideWarningOverlay()
            hideBlockOverlay()
            if (packageName != lastNoSessionLoggedPackage) {
                Log.d("PhoneCodexDecision", "No active session, allowing $packageName")
                lastNoSessionLoggedPackage = packageName
            }
            return
        }

        lastNoSessionLoggedPackage = null

        if (storedSession.status == SessionStatus.LOCKED) {
            val explanation = DecisionExplanation(
                decision = DecisionType.LOCK.name,
                reason = "Session locked",
                source = "Policy",
                confidence = 1.0
            )
            recordExplanation(packageName, screenText, explanation)
            Log.d(
                "PhoneCodexDecision",
                "package=$packageName decision=LOCK reason=Session locked"
            )
            if (!isSystemOverlayNoise(packageName) && currentOverlay == null) {
                showBlockOverlay(packageName, explanation)
            }
            return
        }

        logInstallSurfaceIfPresent(packageName, screenText)

        if (isSystemOverlayNoise(packageName)) return

        if (applyAppRuleBehavior(packageName, screenText)) {
            return
        }

        if (applyContentSignalRules(packageName, screenText)) {
            return
        }

        if (applyFeedbackMemoryRules(packageName, screenText)) {
            return
        }

        val signature = textSignature(screenText)
        val now = System.currentTimeMillis()

        if (
            packageName == lastClassificationRequestPackage &&
            now - lastClassificationRequestTimeMillis < MIN_CLASSIFICATION_INTERVAL_MS
        ) {
            return
        }

        if (
            packageName == lastClassifiedPackage &&
            signature == lastClassifiedTextSignature &&
            now - lastClassificationTimeMillis < CLASSIFICATION_CACHE_TTL_MS
        ) {
            Log.d("PhoneCodexNetAI", "Using cached classification for $packageName")
            applyClassificationOrFallback(
                packageName = packageName,
                screenText = screenText,
                storedSession = storedSession,
                classification = lastClassification
            )
            return
        }

        if (classificationInFlight) {
            return
        }

        classificationInFlight = true
        lastClassificationRequestPackage = packageName
        lastClassificationRequestTimeMillis = now
        Log.d("PhoneCodexNetAI", "Classification request started for $packageName")

        classifierExecutor.execute {
            val classifyRequest = ClassifyRequestBuilder.build(
                packageName = packageName,
                appLabel = resolveAppLabel(packageName),
                screenText = screenText,
                session = storedSession,
                enabledGuardrailIds = permanentGuardrailsStore.getEnabledGuardrails().map { it.id }
            )
            val classification = try {
                contentClassifier.classify(classifyRequest)
            } catch (err: Exception) {
                Log.w("PhoneCodexNetAI", "Classifier failed for $packageName: ${err.message}")
                null
            }

            mainHandler.post {
                try {
                    lastClassifiedPackage = packageName
                    lastClassifiedTextSignature = signature
                    lastClassification = classification
                    lastClassificationTimeMillis = System.currentTimeMillis()

                    if (latestPackageName != packageName) return@post

                    applyClassificationOrFallback(
                        packageName = packageName,
                        screenText = screenText,
                        storedSession = storedSession,
                        classification = classification
                    )
                } finally {
                    classificationInFlight = false
                }
            }
        }
    }

    private fun textSignature(text: String): String {
        return text
            .lowercase()
            .take(300)
            .trim()
            .replace(Regex("\\s+"), " ")
    }

    private fun logScreenTextIfChanged(packageName: String, screenText: String) {
        if (safeAppsStore.isSafePackage(packageName)) return

        val signature = textSignature(screenText)
        if (
            packageName == lastLoggedA11yTextPackage &&
            signature == lastLoggedA11yTextSignature
        ) {
            return
        }

        Log.d(
            "PhoneCodexA11yText",
            "Screen text for $packageName (${screenText.length} chars): ${screenText.take(180)}"
        )
        lastLoggedA11yTextPackage = packageName
        lastLoggedA11yTextSignature = signature
    }

    private fun applyAccessibilityTamperGuard(packageName: String, screenText: String): Boolean {
        val match = accessibilityTamperGuard.evaluatePhoneCodexAccessibilityControls(
            packageName = packageName,
            screenText = screenText
        ) ?: return false

        hideBlockOverlay()
        hideWarningOverlay()
        val explanation = DecisionExplanation(
            decision = DecisionType.WARN.name,
            reason = match.reason,
            source = "Tamper Guard",
            confidence = 1.0,
            matchedSignals = match.matchedSignals
        )
        recordExplanation(packageName, screenText, explanation)
        eventLogStore.addEvent(
            "Tamper guard sent user home from PhoneCodex accessibility controls"
        )
        performGlobalAction(GLOBAL_ACTION_HOME)
        Log.d(
            "PhoneCodexDecision",
            "Tamper guard forced HOME for $packageName signals=${match.matchedSignals}"
        )
        return true
    }

    private fun applyPermanentGuardrails(packageName: String, screenText: String): Boolean {
        val match = permanentGuardrailEvaluator.evaluate(
            packageName = packageName,
            screenText = screenText,
            guardrails = permanentGuardrailsStore.getEnabledGuardrails()
        ) ?: return false

        val matchedSignals = match.matchedStrongSignals + match.matchedWeakSignals
        val explanation = DecisionExplanation(
            decision = match.decision.name,
            reason = match.reason,
            source = "Permanent Guardrail",
            confidence = 1.0,
            matchedSignals = matchedSignals
        )
        recordExplanation(packageName, screenText, explanation)

        when (match.decision) {
            DecisionType.BLOCK -> {
                eventLogStore.addEvent(
                    "Permanent guardrail blocked $packageName: ${match.guardrailName}"
                )
                hideWarningOverlay()
                showBlockOverlay(packageName, explanation)
            }
            DecisionType.WARN -> {
                hideBlockOverlay()
                val signature = textSignature(screenText)
                if (!isRecentlyDismissedWarning(packageName, signature)) {
                    showWarningOverlay(packageName, signature, explanation)
                }
            }
            else -> return false
        }

        Log.d(
            "PhoneCodexDecision",
            "Permanent guardrail ${match.decision.name} for $packageName " +
                "(${match.guardrailName}) reason=${match.reason}"
        )
        return true
    }

    private fun applyAppRuleBehavior(packageName: String, screenText: String): Boolean {
        val rule = appRulesStore.getRuleForPackage(packageName) ?: return false

        return when (rule.behavior) {
            AppRuleBehavior.ALLOW -> {
                hideWarningOverlay()
                hideBlockOverlay()
                debugStateStore.recordDecision(
                    packageName = packageName,
                    screenText = screenText,
                    decision = DecisionType.ALLOW.name,
                    reason = "Allowed by app rule for ${rule.label}",
                    source = "App Rule",
                    confidence = 1.0
                )
                Log.d(
                    "PhoneCodexDecision",
                    "App rule ALLOW for $packageName (${rule.label})"
                )
                true
            }
            AppRuleBehavior.WARN -> {
                hideBlockOverlay()
                val signature = textSignature(screenText)
                val reason = "App rule warns for ${rule.label}"
                val explanation = DecisionExplanation(
                    decision = DecisionType.WARN.name,
                    reason = reason,
                    source = "App Rule",
                    confidence = 1.0
                )
                recordExplanation(packageName, screenText, explanation)
                if (!isRecentlyDismissedWarning(packageName, signature)) {
                    showWarningOverlay(packageName, signature, explanation)
                }
                Log.d(
                    "PhoneCodexDecision",
                    "App rule WARN for $packageName (${rule.label})"
                )
                true
            }
            AppRuleBehavior.BLOCK -> {
                hideWarningOverlay()
                val reason = "Blocked by app rule for ${rule.label}"
                val explanation = DecisionExplanation(
                    decision = DecisionType.BLOCK.name,
                    reason = reason,
                    source = "App Rule",
                    confidence = 1.0
                )
                recordExplanation(packageName, screenText, explanation)
                handleBlockedApp(
                    packageName = packageName,
                    screenText = screenText,
                    explanation = explanation
                )
                Log.d(
                    "PhoneCodexDecision",
                    "App rule BLOCK for $packageName (${rule.label})"
                )
                true
            }
            AppRuleBehavior.AI_DECIDE -> false
        }
    }

    private fun applyContentSignalRules(packageName: String, screenText: String): Boolean {
        if (packageName != YOUTUBE_PACKAGE && packageName != CHROME_PACKAGE) {
            return false
        }

        val signals = contentSignalDetector.detect(packageName, screenText)

        if (packageName == YOUTUBE_PACKAGE && signals.isYouTubeShorts) {
            return applySignalDecision(
                packageName = packageName,
                screenText = screenText,
                decision = DecisionType.BLOCK,
                reason = "YouTube Shorts detected during Study World",
                source = "Content Signal",
                matchedSignals = signals.matchedSignals,
                block = true
            )
        }

        if (packageName == YOUTUBE_PACKAGE && signals.isLikelySearchOrLecture) {
            return applySignalDecision(
                packageName = packageName,
                screenText = screenText,
                decision = DecisionType.ALLOW,
                reason = "Study-like YouTube content detected",
                source = "Content Signal",
                matchedSignals = signals.matchedSignals,
                block = false
            )
        }

        if (packageName == CHROME_PACKAGE && signals.isChromeAdultOrPorn) {
            return applySignalDecision(
                packageName = packageName,
                screenText = screenText,
                decision = DecisionType.BLOCK,
                reason = "Adult or porn content detected in Chrome during Study World",
                source = "Content Signal",
                matchedSignals = signals.matchedSignals,
                block = true
            )
        }

        if (packageName == CHROME_PACKAGE && signals.isChromeStudyLike) {
            return applySignalDecision(
                packageName = packageName,
                screenText = screenText,
                decision = DecisionType.ALLOW,
                reason = "Study-like Chrome content detected",
                source = "Content Signal",
                matchedSignals = signals.matchedSignals,
                block = false
            )
        }

        return false
    }

    private fun applyFeedbackMemoryRules(packageName: String, screenText: String): Boolean {
        val matchedDecision = feedbackMemory.findMatchingDecision(packageName, screenText)
            ?: return false

        val reason = "Matched previous feedback"
        return when (matchedDecision) {
            DecisionType.ALLOW.name -> applySignalDecision(
                packageName = packageName,
                screenText = screenText,
                decision = DecisionType.ALLOW,
                reason = reason,
                source = "Feedback Memory",
                matchedSignals = emptyList(),
                block = false
            )
            DecisionType.BLOCK.name -> applySignalDecision(
                packageName = packageName,
                screenText = screenText,
                decision = DecisionType.BLOCK,
                reason = reason,
                source = "Feedback Memory",
                matchedSignals = emptyList(),
                block = true
            )
            else -> false
        }
    }

    private fun applySignalDecision(
        packageName: String,
        screenText: String,
        decision: DecisionType,
        reason: String,
        source: String,
        matchedSignals: List<String>,
        block: Boolean
    ): Boolean {
        val explanation = DecisionExplanation(
            decision = decision.name,
            reason = reason,
            source = source,
            confidence = 1.0,
            matchedSignals = matchedSignals
        )
        recordExplanation(packageName, screenText, explanation)

        if (block) {
            hideWarningOverlay()
            handleBlockedApp(
                packageName = packageName,
                screenText = screenText,
                explanation = explanation
            )
        } else {
            hideWarningOverlay()
            hideBlockOverlay()
        }

        Log.d(
            "PhoneCodexDecision",
            "$source ${decision.name} for $packageName reason=$reason signals=$matchedSignals"
        )
        return true
    }

    private fun isInstallSurface(packageName: String, screenText: String): Boolean {
        if (
            packageName == "com.android.vending" ||
            packageName.contains("packageinstaller", ignoreCase = true)
        ) {
            return true
        }

        val text = screenText.lowercase()
        return INSTALL_SURFACE_KEYWORDS.any { keyword -> text.contains(keyword) }
    }

    private fun logInstallSurfaceIfPresent(packageName: String, screenText: String) {
        if (isInstallSurface(packageName, screenText)) {
            Log.d("PhoneCodexInstallGate", "Install surface detected for $packageName")
        }
    }

    private fun applyClassificationOrFallback(
        packageName: String,
        screenText: String,
        storedSession: FocusSession,
        classification: ContentClassification?
    ) {
        val gatedClassification = classification?.let { aiConfidenceGate.apply(it) }

        if (gatedClassification != null) {
            recordDebugClassification(packageName, screenText, gatedClassification)
        }

        when (gatedClassification?.decision) {
            DecisionType.ALLOW -> {
                hideWarningOverlayUnlessVisibleFor(packageName)
                hideBlockOverlay()
                Log.d(
                    "PhoneCodexDecision",
                    "final ALLOW pkg=$packageName source=${gatedClassification.source} " +
                        "confidence=${gatedClassification.confidence} " +
                        "reasonCategory=${gatedClassification.reasonCategory ?: "—"}"
                )
            }
            DecisionType.BLOCK, DecisionType.LOCK -> {
                hideWarningOverlay()
                val explanation = DecisionExplanation(
                    decision = gatedClassification.decision.name,
                    reason = gatedClassification.reason,
                    source = gatedClassification.source,
                    confidence = gatedClassification.confidence
                )
                Log.d(
                    "PhoneCodexDecision",
                    "final ${gatedClassification.decision} pkg=$packageName " +
                        "source=${gatedClassification.source} " +
                        "confidence=${gatedClassification.confidence} " +
                        "reasonCategory=${gatedClassification.reasonCategory ?: "—"} " +
                        "wouldEscalate=${gatedClassification.wouldEscalate}"
                )
                handleBlockedApp(
                    packageName = packageName,
                    screenText = screenText,
                    explanation = explanation
                )
            }
            DecisionType.WARN, DecisionType.ASK -> {
                hideBlockOverlay()
                val signature = textSignature(screenText)
                val explanation = DecisionExplanation(
                    decision = gatedClassification.decision.name,
                    reason = gatedClassification.reason,
                    source = gatedClassification.source,
                    confidence = gatedClassification.confidence
                )
                if (!isRecentlyDismissedWarning(packageName, signature)) {
                    showWarningOverlay(packageName, signature, explanation)
                }
                Log.d(
                    "PhoneCodexDecision",
                    "final WARN pkg=$packageName source=${gatedClassification.source} " +
                        "confidence=${gatedClassification.confidence} " +
                        "reasonCategory=${gatedClassification.reasonCategory ?: "—"} " +
                        "wouldEscalate=${gatedClassification.wouldEscalate}"
                )
            }
            else -> evaluatePolicyFallback(
                packageName = packageName,
                screenText = screenText,
                storedSession = storedSession,
                backendUnavailable = classification == null
            )
        }
    }

    private fun evaluatePolicyFallback(
        packageName: String,
        screenText: String,
        storedSession: FocusSession,
        backendUnavailable: Boolean = false
    ) {
        val context = ContextSnapshot(
            timestampMillis = System.currentTimeMillis(),
            packageName = packageName,
            appLabel = null,
            screenText = screenText,
            url = null
        )
        val decision = policyEngine.evaluate(debugWorld, storedSession, context)
        recordDebugPolicy(packageName, screenText, decision)
        Log.d(
            "PhoneCodexDecision",
            "package=$packageName decision=${decision.decision} " +
                "reason=${decision.reason} riskLevel=${decision.riskLevel}"
        )

        when (decision.decision) {
            DecisionType.BLOCK, DecisionType.LOCK -> {
                hideWarningOverlay()
                val explanation = DecisionExplanation(
                    decision = decision.decision.name,
                    reason = decision.reason,
                    source = "Policy",
                    confidence = decision.confidence
                )
                handleBlockedApp(
                    packageName = packageName,
                    screenText = screenText,
                    explanation = explanation
                )
            }
            DecisionType.WARN, DecisionType.ASK -> {
                hideBlockOverlay()
                val signature = textSignature(screenText)
                val explanation = DecisionExplanation(
                    decision = decision.decision.name,
                    reason = decision.reason,
                    source = "Policy",
                    confidence = decision.confidence
                )
                if (!isRecentlyDismissedWarning(packageName, signature)) {
                    showWarningOverlay(packageName, signature, explanation)
                }
                Log.d(
                    "PhoneCodexDecision",
                    "Policy warning for $packageName (${decision.decision}): ${decision.reason}"
                )
            }
            else -> {
                if (backendUnavailable) {
                    applySafeWarnFallback(packageName, screenText)
                } else {
                    hideWarningOverlayUnlessVisibleFor(packageName)
                    hideBlockOverlay()
                }
            }
        }
    }

    private fun applySafeWarnFallback(packageName: String, screenText: String) {
        hideBlockOverlay()
        val signature = textSignature(screenText)
        val explanation = DecisionExplanation(
            decision = DecisionType.WARN.name,
            reason = "Focus advisor unavailable. Stay aligned with your session goal.",
            source = "Safe Fallback",
            confidence = 0.5
        )
        recordExplanation(packageName, screenText, explanation)
        if (!isRecentlyDismissedWarning(packageName, signature)) {
            showWarningOverlay(packageName, signature, explanation)
        }
        Log.d(
            "PhoneCodexDecision",
            "Safe WARN fallback for $packageName (backend unavailable)"
        )
    }

    private fun resolveAppLabel(packageName: String): String? {
        return try {
            val appInfo = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(appInfo)?.toString()
        } catch (_: Exception) {
            null
        }
    }

    private fun recordExplanation(
        packageName: String,
        screenText: String,
        explanation: DecisionExplanation
    ) {
        latestExplanation = explanation
        debugStateStore.recordDecision(
            packageName = packageName,
            screenText = screenText,
            decision = explanation.decision,
            reason = explanation.reason,
            source = explanation.source,
            confidence = explanation.confidence ?: 1.0,
            matchedSignals = explanation.matchedSignals
        )
    }

    private fun buildOverlayModel(explanation: DecisionExplanation): CommitmentOverlayModel {
        val session = sessionStore.getActiveSession()
        val kind = CommitmentOverlayCopy.overlayKind(explanation.decision)
        val remaining = session?.let { it.deadlineMillis - System.currentTimeMillis() }
        return CommitmentOverlayModel(
            kind = kind,
            reason = CommitmentOverlayCopy.shortReason(explanation.decision, explanation.reason),
            promiseGoal = session?.goal?.takeIf { it.isNotBlank() },
            attemptCount = session?.attemptCount,
            remainingMillis = remaining
        )
    }

    private fun openPhoneCodexApp() {
        val launch = packageManager.getLaunchIntentForPackage(OWN_PACKAGE_NAME) ?: return
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        try {
            startActivity(launch)
        } catch (err: RuntimeException) {
            Log.e("PhoneCodexOverlay", "Failed to open PhoneCodex", err)
        }
    }

    private fun recordDebugClassification(
        packageName: String,
        screenText: String,
        classification: ContentClassification
    ) {
        latestExplanation = DecisionExplanation(
            decision = classification.decision.name,
            reason = classification.reason,
            source = classification.source,
            confidence = classification.confidence
        )
        debugStateStore.recordDecision(
            packageName = packageName,
            screenText = screenText,
            decision = classification.decision.name,
            reason = classification.reason,
            source = classification.source,
            confidence = classification.confidence,
            reasonCategory = classification.reasonCategory,
            wouldEscalate = classification.wouldEscalate,
            backendMeta = classification.backendMeta
        )
    }

    private fun recordDebugPolicy(
        packageName: String,
        screenText: String,
        decision: PolicyDecision
    ) {
        recordExplanation(
            packageName = packageName,
            screenText = screenText,
            explanation = DecisionExplanation(
                decision = decision.decision.name,
                reason = decision.reason,
                source = "Policy",
                confidence = decision.confidence
            )
        )
    }

    private fun handleBlockedApp(
        packageName: String,
        screenText: String,
        explanation: DecisionExplanation
    ) {
        if (currentOverlay != null) return

        hideWarningOverlay()
        latestExplanation = explanation
        val shouldCountAttempt = shouldCountBlockedAttempt(packageName, screenText)
        val updated = if (shouldCountAttempt) {
            sessionStore.incrementAttempt()
        } else {
            sessionStore.getActiveSession()
        }
        eventLogStore.addEvent("Blocked $packageName because ${explanation.reason}")
        val lockAttemptThreshold = studyWorldSettingsStore.getSettings().lockAttemptThreshold
        if (updated != null && updated.attemptCount >= lockAttemptThreshold) {
            sessionStore.lockSession()
            eventLogStore.addEvent("Session locked after $lockAttemptThreshold attempts")
            val lockedExplanation = explanation.copy(
                decision = DecisionType.LOCK.name,
                reason = LOCKED_SESSION_REASON
            )
            latestExplanation = lockedExplanation
            showBlockOverlay(packageName, lockedExplanation)
        } else {
            showBlockOverlay(packageName, explanation)
        }
    }

    private fun shouldCountBlockedAttempt(packageName: String, screenText: String): Boolean {
        val signature = textSignature(screenText)
        val now = System.currentTimeMillis()
        val cooldownMs = studyWorldSettingsStore.getSettings()
            .blockAttemptCooldownMinutes * 60_000L
        val isDuplicate = packageName == lastCountedBlockPackage &&
            signature == lastCountedBlockSignature &&
            now - lastCountedBlockTimeMillis < cooldownMs

        if (isDuplicate) {
            Log.d("PhoneCodexDecision", "Duplicate block ignored for attempt count: $packageName")
            return false
        }

        lastCountedBlockPackage = packageName
        lastCountedBlockSignature = signature
        lastCountedBlockTimeMillis = now
        return true
    }

    /**
     * Handles foreground events while a block (or warning) overlay is already showing.
     *
     * @return true if the event is fully consumed and [inspectAndEvaluate] should return.
     */
    private fun handleActiveOverlayForeground(packageName: String): Boolean {
        val blockTarget = activeOverlayTargetPackage
        if (currentOverlay != null && blockTarget != null) {
            return handleActiveBlockOverlayForeground(packageName, blockTarget)
        }

        val warningTarget = visibleWarningPackageName
        if (currentWarningOverlay != null && warningTarget != null) {
            if (packageName == OWN_PACKAGE_NAME) {
                Log.d(
                    "PhoneCodexOverlay",
                    "Overlay retained for target=$warningTarget despite own-package event"
                )
                return true
            }
            if (isSystemUiPackage(packageName)) {
                return true
            }
            if (packageName == warningTarget) {
                return true
            }
            if (safeAppsStore.isSafePackage(packageName)) {
                hideWarningOverlay()
                Log.d(
                    "PhoneCodexOverlay",
                    "Overlay hidden because allowed package=$packageName"
                )
                return false
            }
        }

        return false
    }

    private fun handleActiveBlockOverlayForeground(
        packageName: String,
        target: String
    ): Boolean {
        if (packageName == OWN_PACKAGE_NAME) {
            clearOverlayAwayTracking()
            Log.d(
                "PhoneCodexOverlay",
                "Overlay retained for target=$target despite own-package event"
            )
            return true
        }

        if (isSystemUiPackage(packageName)) {
            return true
        }

        if (packageName == target) {
            clearOverlayAwayTracking()
            return true
        }

        // Truly allowed / safe app under the overlay → hide and let normal flow continue.
        if (safeAppsStore.isSafePackage(packageName)) {
            clearOverlayAwayTracking()
            hideBlockOverlayBecauseAllowed(packageName)
            return false
        }

        // Another external package: wait a short debounce so transient focus blips
        // (recents, share sheets) do not flap the overlay.
        val now = System.currentTimeMillis()
        if (overlayAwayCandidatePackage != packageName) {
            overlayAwayCandidatePackage = packageName
            overlayAwaySinceMillis = now
            Log.d(
                "PhoneCodexOverlay",
                "Overlay away debounce started candidate=$packageName target=$target"
            )
            return true
        }
        if (now - overlayAwaySinceMillis < OVERLAY_AWAY_DEBOUNCE_MS) {
            return true
        }

        clearOverlayAwayTracking()
        hideBlockOverlay()
        Log.d(
            "PhoneCodexOverlay",
            "Overlay hidden because target left foreground, now=$packageName"
        )
        return false
    }

    private fun clearOverlayAwayTracking() {
        overlayAwayCandidatePackage = null
        overlayAwaySinceMillis = 0L
    }

    private fun isSystemUiPackage(packageName: String): Boolean {
        return packageName == "com.android.systemui" ||
            packageName == "miui.systemui.plugin"
    }

    private fun isSystemOverlayNoise(packageName: String): Boolean {
        return isSystemUiPackage(packageName) ||
            ((currentOverlay != null || currentWarningOverlay != null) &&
                packageName == OWN_PACKAGE_NAME)
    }

    private fun showBlockOverlay(packageName: String, explanation: DecisionExplanation) {
        if (currentOverlay != null) return

        hideWarningOverlay()
        latestExplanation = explanation

        val model = buildOverlayModel(explanation)
        val layout = CommitmentOverlayBuilder(this).build(
            model = model,
            actions = CommitmentOverlayActions(
                onBackToSafe = {
                    hideBlockOverlay()
                    performGlobalAction(GLOBAL_ACTION_HOME)
                },
                onOpenPhoneCodex = {
                    hideBlockOverlay()
                    openPhoneCodexApp()
                }
            )
        )

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            0,
            PixelFormat.TRANSLUCENT
        )

        val windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        try {
            windowManager.addView(layout, params)
            currentOverlay = layout
            activeOverlayTargetPackage = packageName
            lastBlockedPackage = packageName
            clearOverlayAwayTracking()
            runtimeDiagStore.setOverlayActive(true)
            Log.d(
                "PhoneCodexOverlay",
                "Overlay shown kind=${model.kind} target=$packageName"
            )
        } catch (err: RuntimeException) {
            Log.e("PhoneCodexOverlay", "Failed to show block overlay", err)
            currentOverlay = null
            activeOverlayTargetPackage = null
            syncOverlayActiveFlag()
        }
    }

    private fun hideBlockOverlayBecauseAllowed(allowedPackage: String) {
        if (currentOverlay == null) return
        removeBlockOverlayView()
        Log.d(
            "PhoneCodexOverlay",
            "Overlay hidden because allowed package=$allowedPackage"
        )
    }

    private fun hideBlockOverlay() {
        if (currentOverlay == null) return
        removeBlockOverlayView()
        Log.d("PhoneCodexOverlay", "Overlay hidden")
    }

    private fun removeBlockOverlayView() {
        val overlay = currentOverlay ?: return
        val windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        try {
            windowManager.removeView(overlay)
        } catch (_: IllegalArgumentException) {
        }
        currentOverlay = null
        activeOverlayTargetPackage = null
        clearOverlayAwayTracking()
        syncOverlayActiveFlag()
    }

    private fun showWarningOverlay(
        packageName: String,
        signature: String,
        explanation: DecisionExplanation
    ) {
        if (currentOverlay != null) return
        if (currentWarningOverlay != null && visibleWarningPackageName == packageName) {
            latestExplanation = explanation
            visibleWarningTextSignature = signature
            Log.d("PhoneCodexOverlay", "Warning overlay kept for $packageName")
            return
        }
        hideWarningOverlay()
        latestExplanation = explanation

        val model = buildOverlayModel(explanation).copy(kind = OverlayKind.WARN)
        val layout = CommitmentOverlayBuilder(this).build(
            model = model,
            actions = CommitmentOverlayActions(
                onBackToSafe = {
                    hideWarningOverlay()
                    performGlobalAction(GLOBAL_ACTION_HOME)
                },
                onGoBack = {
                    hideWarningOverlay()
                    performGlobalAction(GLOBAL_ACTION_BACK)
                },
                onContinue = {
                    dismissedWarningPackageName = visibleWarningPackageName
                    dismissedWarningTextSignature = visibleWarningTextSignature
                    dismissedWarningTimeMillis = System.currentTimeMillis()
                    hideWarningOverlay()
                }
            )
        )

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            0,
            PixelFormat.TRANSLUCENT
        )

        val windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        try {
            windowManager.addView(layout, params)
            currentWarningOverlay = layout
            visibleWarningPackageName = packageName
            visibleWarningTextSignature = signature
            runtimeDiagStore.setOverlayActive(true)
            Log.d("PhoneCodexOverlay", "Warning overlay shown kind=WARN target=$packageName")
        } catch (err: RuntimeException) {
            Log.e("PhoneCodexOverlay", "Failed to show warning overlay", err)
            currentWarningOverlay = null
            visibleWarningPackageName = null
            visibleWarningTextSignature = null
            syncOverlayActiveFlag()
        }
    }

    private fun hideWarningOverlay() {
        val overlay = currentWarningOverlay ?: return
        val windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        try {
            windowManager.removeView(overlay)
        } catch (_: IllegalArgumentException) {
        }
        currentWarningOverlay = null
        visibleWarningPackageName = null
        visibleWarningTextSignature = null
        syncOverlayActiveFlag()
        Log.d("PhoneCodexOverlay", "Warning overlay hidden")
    }

    private fun syncOverlayActiveFlag() {
        runtimeDiagStore.setOverlayActive(
            currentOverlay != null || currentWarningOverlay != null
        )
    }

    private fun hideWarningOverlayUnlessVisibleFor(packageName: String) {
        if (currentWarningOverlay != null && visibleWarningPackageName == packageName) {
            Log.d("PhoneCodexOverlay", "Warning overlay kept during same-package allow: $packageName")
            return
        }
        hideWarningOverlay()
    }

    private fun isRecentlyDismissedWarning(packageName: String, signature: String): Boolean {
        val dismissedAt = dismissedWarningTimeMillis
        if (dismissedAt == 0L) return false
        return packageName == dismissedWarningPackageName &&
            signature == dismissedWarningTextSignature &&
            System.currentTimeMillis() - dismissedAt < WARNING_DISMISS_TTL_MS
    }

    private fun collectScreenText(packageName: String): String {
        val root = rootInActiveWindow ?: return ""
        val rootPackageName = root.packageName?.toString()
        if (rootPackageName != null && rootPackageName != packageName) {
            Log.d(
                "PhoneCodexA11yText",
                "Skipping stale screen text: event=$packageName root=$rootPackageName"
            )
            return ""
        }
        val builder = StringBuilder()
        collectVisibleText(root, builder, depth = 0)
        return builder.toString().take(MAX_TEXT_LENGTH)
    }

    private fun collectVisibleText(
        node: AccessibilityNodeInfo,
        out: StringBuilder,
        depth: Int
    ) {
        if (depth > MAX_DEPTH) return
        if (out.length >= MAX_TEXT_LENGTH) return

        if (node.isVisibleToUser) {
            appendText(out, node.text?.toString())
            appendText(out, node.contentDescription?.toString())
        }

        for (i in 0 until node.childCount) {
            if (out.length >= MAX_TEXT_LENGTH) return
            val child = node.getChild(i) ?: continue
            collectVisibleText(child, out, depth + 1)
        }
    }

    private fun appendText(out: StringBuilder, value: String?) {
        val trimmed = value?.trim().orEmpty()
        if (trimmed.isEmpty()) return
        if (out.isNotEmpty()) out.append(' ')
        out.append(trimmed)
    }

    companion object {
        private const val OWN_PACKAGE_NAME = "com.phonecodex.app"
        private const val MAX_TEXT_LENGTH = 1000
        private const val MAX_DEPTH = 50
        private const val YOUTUBE_PACKAGE = "com.google.android.youtube"
        private const val CHROME_PACKAGE = "com.android.chrome"
        private const val CLASSIFICATION_CACHE_TTL_MS = 5000L
        private const val MIN_CLASSIFICATION_INTERVAL_MS = 2500L
        private const val WARNING_DISMISS_TTL_MS = 60000L
        private const val SAFE_APP_LOG_THROTTLE_MS = 10_000L
        private const val OVERLAY_AWAY_DEBOUNCE_MS = 750L
        private const val LOCKED_SESSION_REASON =
            "Lock is active because of repeated attempts to leave your commitment."

        private val INSTALL_SURFACE_KEYWORDS = listOf(
            "install",
            "uninstall",
            "in-app purchases",
            "rated for",
            "contains ads"
        )
    }
}

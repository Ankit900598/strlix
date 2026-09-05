package com.phonecodex.app.ui.home

import android.content.Context
import android.os.SystemClock
import android.util.Log
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.phonecodex.app.accessibility.AccessibilityHealthChecker
import com.phonecodex.app.data.AppRulesStore
import com.phonecodex.app.data.DebugState
import com.phonecodex.app.data.DebugStateStore
import com.phonecodex.app.data.EventLogStore
import com.phonecodex.app.data.FeedbackStore
import com.phonecodex.app.data.InstalledAppsReader
import com.phonecodex.app.data.PermanentGuardrailsStore
import com.phonecodex.app.data.ProtectionViolationState
import com.phonecodex.app.data.ProtectionViolationStore
import com.phonecodex.app.data.RuntimeDiagStore
import com.phonecodex.app.data.SafeAppsStore
import com.phonecodex.app.data.SessionStore
import com.phonecodex.app.data.StudyWorldSettingsStore
import com.phonecodex.app.domain.diagnostics.BackendHealthProbe
import com.phonecodex.app.domain.diagnostics.BackendProbeResult
import com.phonecodex.app.domain.model.AppRule
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.FeedbackEntry
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.FocusWorld
import com.phonecodex.app.domain.model.InstalledApp
import com.phonecodex.app.domain.model.PermanentGuardrail
import com.phonecodex.app.domain.model.SafeApp
import com.phonecodex.app.domain.model.SessionStatus
import com.phonecodex.app.domain.model.StudyWorldSettings
import com.phonecodex.app.domain.policy.PolicyEngine
import com.phonecodex.app.domain.promise.FocusPromiseParser
import com.phonecodex.app.domain.session.SessionManager
import com.phonecodex.app.protection.ProtectionHeartbeatController
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Home screen state holder. Store I/O lives here (and in polling effects) — never inside
 * composable bodies. Marked [Stable] so unrelated snapshot fields do not invalidate siblings.
 */
@Stable
internal class HomeScreenState(
    val context: Context,
    val sessionManager: SessionManager,
    val sessionStore: SessionStore,
    val eventLogStore: EventLogStore,
    val debugStateStore: DebugStateStore,
    val runtimeDiagStore: RuntimeDiagStore,
    val feedbackStore: FeedbackStore,
    val appRulesStore: AppRulesStore,
    val studyWorldSettingsStore: StudyWorldSettingsStore,
    val permanentGuardrailsStore: PermanentGuardrailsStore,
    val safeAppsStore: SafeAppsStore,
    val protectionViolationStore: ProtectionViolationStore,
    val installedAppsReader: InstalledAppsReader,
    val policyEngine: PolicyEngine,
    val focusPromiseParser: FocusPromiseParser,
    val studyWorld: FocusWorld,
    val createdAtElapsedMs: Long = SystemClock.elapsedRealtime()
) {
    var promiseText by mutableStateOf("")
    var promiseUnderstanding by mutableStateOf<PromiseUnderstanding?>(null)
    var promiseDraft by mutableStateOf<FocusPromise?>(null)
    var startBlockedMessage by mutableStateOf<String?>(null)

    var goal by mutableStateOf("")
    var session by mutableStateOf<FocusSession?>(null)
    var nowMillis by mutableStateOf(System.currentTimeMillis())
    var lastDecisionText by mutableStateOf("No policy check yet")

    var recentEvents by mutableStateOf<List<String>>(emptyList())
    var debugState by mutableStateOf(EMPTY_DEBUG_STATE)
    var protectionViolationState by mutableStateOf(EMPTY_VIOLATION_STATE)
    var recentFeedback by mutableStateOf<List<FeedbackEntry>>(emptyList())
    private var advancedSnapshotLoaded: Boolean = false

    var appRules by mutableStateOf<List<AppRule>>(emptyList())
    var installedApps by mutableStateOf<List<InstalledApp>>(emptyList())
    var installedAppsLoading by mutableStateOf(false)
    var installedAppsSearch by mutableStateOf("")
    var studyWorldSettings by mutableStateOf(DEFAULT_STUDY_SETTINGS)
    var permanentGuardrails by mutableStateOf<List<PermanentGuardrail>>(emptyList())
    var safeApps by mutableStateOf<List<SafeApp>>(emptyList())
    var safeAppsSearch by mutableStateOf("")
    var isAccessibilityEnabled by mutableStateOf(false)
    var isAccessibilityAlive by mutableStateOf(false)
    var overlayActive by mutableStateOf(false)
    var backendProbeResult by mutableStateOf(BackendProbeResult.idle())
    var backendTestInProgress by mutableStateOf(false)
    var showAdvancedControls by mutableStateOf(false)
    var isBootstrapped by mutableStateOf(false)
    private var bootstrapStarted: Boolean = false
    private var diagnosticsScope: CoroutineScope? = null

    val isSessionActive: Boolean
        get() = session?.status == SessionStatus.ACTIVE

    val isSessionLocked: Boolean
        get() = session?.status == SessionStatus.LOCKED

    val hasStoredSession: Boolean
        get() = isSessionActive || isSessionLocked

    val enabledGuardrailCount: Int
        get() = permanentGuardrails.count { it.enabled }

    val enabledGuardrails: List<PermanentGuardrail>
        get() = permanentGuardrails.filter { it.enabled }

    val developerDiagnostics: DeveloperDiagnosticsUiModel
        get() = buildDeveloperDiagnosticsUiModel(
            isAccessibilityEnabled = isAccessibilityEnabled,
            isAccessibilityAlive = isAccessibilityAlive,
            session = session,
            overlayActive = overlayActive,
            debugState = debugState,
            probeResult = backendProbeResult,
            testInProgress = backendTestInProgress
        )

    fun attachDiagnosticsScope(scope: CoroutineScope) {
        diagnosticsScope = scope
    }

    fun openAccessibilitySettings() {
        openAccessibilitySettings(context)
    }

    /**
     * First paint uses empty defaults. Essential prefs load off the main thread so the
     * LazyColumn can appear immediately.
     */
    suspend fun bootstrapIfNeeded() {
        if (bootstrapStarted) return
        bootstrapStarted = true
        val started = SystemClock.elapsedRealtime()
        val snapshot = withContext(Dispatchers.IO) {
            BootstrapSnapshot(
                session = sessionStore.getStoredSession(),
                accessibilityEnabled =
                    AccessibilityHealthChecker.isPhoneCodexAccessibilityEnabled(context),
                studyWorldSettings = studyWorldSettingsStore.getSettings(),
                appRules = appRulesStore.getRules(),
                guardrails = permanentGuardrailsStore.getGuardrails(),
                safeApps = safeAppsStore.getSafeApps()
            )
        }
        session = snapshot.session
        isAccessibilityEnabled = snapshot.accessibilityEnabled
        studyWorldSettings = snapshot.studyWorldSettings
        appRules = snapshot.appRules
        permanentGuardrails = snapshot.guardrails
        safeApps = snapshot.safeApps
        isBootstrapped = true
        Log.d(
            "PhoneCodexUIPerf",
            "bootstrap=${SystemClock.elapsedRealtime() - started}ms"
        )
    }

    fun loadInstalledApps(coroutineScope: CoroutineScope) {
        if (installedAppsLoading) return
        installedAppsLoading = true
        coroutineScope.launch {
            val started = SystemClock.elapsedRealtime()
            val apps = withContext(Dispatchers.Default) {
                installedAppsReader.getLaunchableApps()
            }
            installedApps = apps
            installedAppsLoading = false
            Log.d(
                "PhoneCodexUIPerf",
                "installedAppsLoad=${SystemClock.elapsedRealtime() - started}ms count=${apps.size}"
            )
        }
    }

    fun selectExamplePromise(example: ExamplePromise) {
        promiseText = example.promiseText
        clearUnderstanding()
    }

    fun updatePromiseText(text: String) {
        promiseText = text
        if (promiseUnderstanding != null) {
            clearUnderstanding()
        }
    }

    fun understandPromise() {
        val text = promiseText.trim()
        if (text.isEmpty()) return

        val draft = focusPromiseParser.parse(text)
        promiseDraft = draft
        promiseUnderstanding = buildPromiseUnderstanding(
            draft = draft,
            alwaysBlockedLabels = enabledGuardrails.map(::guardrailBlockedLabel)
        )
        startBlockedMessage = null
    }

    fun clearUnderstanding() {
        promiseUnderstanding = null
        promiseDraft = null
        startBlockedMessage = null
    }

    fun startCommitment() {
        val draft = promiseDraft ?: return

        if (!isAccessibilityEnabled) {
            startBlockedMessage =
                "Turn on protection first, otherwise I cannot keep this promise for you."
            return
        }

        startBlockedMessage = null

        applyFocusPromiseDraft(
            draft = draft,
            studyWorldSettingsStore = studyWorldSettingsStore
        )
        draft.suggestedAppRules.forEach { rule -> appRulesStore.applySuggestedRule(rule) }
        appRules = appRulesStore.getRules()
        studyWorldSettings = studyWorldSettingsStore.getSettings()

        goal = draft.rawText.ifEmpty { "Focus" }
        val started = sessionManager.startSession(
            world = studyWorld,
            goal = goal,
            durationMillis = studyWorldSettings.durationMinutes * 60 * 1000L,
            nowMillis = System.currentTimeMillis()
        )
        sessionStore.saveActiveSession(started)
        session = started
        ProtectionHeartbeatController.start(context)

        promiseUnderstanding = null
        promiseDraft = null
    }

    fun endCommitment() {
        sessionManager.stopSession(System.currentTimeMillis())
        sessionStore.clearSession()
        session = null
        ProtectionHeartbeatController.stop(context)
        promiseText = ""
        clearUnderstanding()
    }

    fun logEmergencyExit() {
        eventLogStore.addEvent("Emergency exit requested")
        if (showAdvancedControls) {
            recentEvents = eventLogStore.getRecentEvents()
        }
    }

    fun logCooldownUnlock() {
        eventLogStore.addEvent("Cooldown unlock requested")
        if (showAdvancedControls) {
            recentEvents = eventLogStore.getRecentEvents()
        }
    }

    fun setDurationMinutes(minutes: Int) {
        studyWorldSettingsStore.setDurationMinutes(minutes)
        studyWorldSettings = studyWorldSettingsStore.getSettings()
    }

    fun setLockAttemptThreshold(threshold: Int) {
        studyWorldSettingsStore.setLockAttemptThreshold(threshold)
        studyWorldSettings = studyWorldSettingsStore.getSettings()
    }

    fun setBlockAttemptCooldownMinutes(minutes: Int) {
        studyWorldSettingsStore.setBlockAttemptCooldownMinutes(minutes)
        studyWorldSettings = studyWorldSettingsStore.getSettings()
    }

    fun toggleGuardrail(guardrail: PermanentGuardrail, enabled: Boolean) {
        permanentGuardrailsStore.setGuardrailEnabled(guardrail.id, enabled)
        permanentGuardrails = permanentGuardrailsStore.getGuardrails()
    }

    fun toggleAdvancedControls() {
        if (showAdvancedControls) {
            showAdvancedControls = false
            return
        }
        val started = SystemClock.elapsedRealtime()
        // Open shell immediately; snapshot fills on IO via loadAdvancedSnapshotAsync or poll.
        showAdvancedControls = true
        Log.d(
            "PhoneCodexUIPerf",
            "advancedToggle open shell=${SystemClock.elapsedRealtime() - started}ms"
        )
    }

    suspend fun loadAdvancedSnapshotIfNeeded() {
        if (advancedSnapshotLoaded || !showAdvancedControls) return
        val started = SystemClock.elapsedRealtime()
        val snapshot = withContext(Dispatchers.IO) {
            AdvancedSnapshot(
                debugState = debugStateStore.getDebugState(),
                recentEvents = eventLogStore.getRecentEvents(),
                protectionViolationState = protectionViolationStore.getState(),
                recentFeedback = feedbackStore.getRecentFeedback(),
                accessibilityAlive = runtimeDiagStore.isAccessibilityServiceAlive(),
                overlayActive = runtimeDiagStore.isOverlayActive()
            )
        }
        debugState = snapshot.debugState
        recentEvents = snapshot.recentEvents
        protectionViolationState = snapshot.protectionViolationState
        recentFeedback = snapshot.recentFeedback
        isAccessibilityAlive = snapshot.accessibilityAlive
        overlayActive = snapshot.overlayActive
        advancedSnapshotLoaded = true
        Log.d(
            "PhoneCodexUIPerf",
            "advancedSnapshot=${SystemClock.elapsedRealtime() - started}ms"
        )
    }

    fun clearViolations() {
        protectionViolationStore.clearViolations()
        protectionViolationState = protectionViolationStore.getState()
    }

    fun refreshDebugState() {
        debugState = debugStateStore.getDebugState()
    }

    fun refreshDeveloperDiagnostics() {
        debugState = debugStateStore.getDebugState()
        isAccessibilityAlive = runtimeDiagStore.isAccessibilityServiceAlive()
        overlayActive = runtimeDiagStore.isOverlayActive()
        isAccessibilityEnabled =
            AccessibilityHealthChecker.isPhoneCodexAccessibilityEnabled(context)
        session = sessionStore.getStoredSession()
    }

    fun testBackend() {
        if (backendTestInProgress) return
        val scope = diagnosticsScope ?: return
        backendTestInProgress = true
        scope.launch {
            val result = withContext(Dispatchers.IO) {
                BackendHealthProbe.probe()
            }
            backendProbeResult = result
            backendTestInProgress = false
            refreshDeveloperDiagnostics()
        }
    }

    fun refreshEventsFromStore() {
        recentEvents = eventLogStore.getRecentEvents()
        session = sessionStore.getStoredSession()
    }

    fun isDefaultAppRule(packageName: String): Boolean =
        appRulesStore.isDefaultRule(packageName)

    fun applyAppRuleBehavior(rule: AppRule, behavior: AppRuleBehavior) {
        appRulesStore.applySuggestedRule(rule.copy(behavior = behavior))
        appRules = appRulesStore.getRules()
    }

    fun addAppRule(app: InstalledApp, behavior: AppRuleBehavior) {
        appRulesStore.applySuggestedRule(
            AppRule(
                packageName = app.packageName,
                label = app.label,
                behavior = behavior
            )
        )
        appRules = appRulesStore.getRules()
    }

    fun removeAppRule(packageName: String) {
        appRulesStore.removeCustomRule(packageName)
        appRules = appRulesStore.getRules()
    }

    fun addSafeApp(app: InstalledApp) {
        safeAppsStore.addSafeApp(app.packageName, app.label)
        safeApps = safeAppsStore.getSafeApps()
    }

    fun removeSafeApp(packageName: String) {
        safeAppsStore.removeSafeApp(packageName)
        safeApps = safeAppsStore.getSafeApps()
    }

    fun submitFeedback(correctedDecision: String) {
        saveFeedback(
            feedbackStore = feedbackStore,
            debugState = debugState,
            correctedDecision = correctedDecision
        )
        recentFeedback = feedbackStore.getRecentFeedback()
    }

    fun updateAppRules(rules: List<AppRule>) {
        appRules = rules
    }

    fun updateSafeApps(apps: List<SafeApp>) {
        safeApps = apps
    }

    fun updateRecentFeedback(entries: List<FeedbackEntry>) {
        recentFeedback = entries
    }
}

private data class BootstrapSnapshot(
    val session: FocusSession?,
    val accessibilityEnabled: Boolean,
    val studyWorldSettings: StudyWorldSettings,
    val appRules: List<AppRule>,
    val guardrails: List<PermanentGuardrail>,
    val safeApps: List<SafeApp>
)

private data class AdvancedSnapshot(
    val debugState: DebugState,
    val recentEvents: List<String>,
    val protectionViolationState: ProtectionViolationState,
    val recentFeedback: List<FeedbackEntry>,
    val accessibilityAlive: Boolean,
    val overlayActive: Boolean
)

private val EMPTY_DEBUG_STATE = DebugState(
    lastPackageName = null,
    lastScreenTextPreview = null,
    lastDecision = null,
    lastReason = null,
    lastSource = null,
    lastConfidence = null,
    lastMatchedSignals = emptyList(),
    lastUpdatedMillis = 0L,
    lastReasonCategory = null,
    lastWouldEscalate = null,
    lastBackendProvider = null,
    lastBackendDeployment = null,
    lastBackendPromptVersion = null,
    lastBackendLatencyMs = null
)

private val EMPTY_VIOLATION_STATE = ProtectionViolationState(
    violationCount = 0,
    lastViolationMillis = 0L,
    lastReason = null
)

private val DEFAULT_STUDY_SETTINGS = StudyWorldSettings(
    durationMinutes = StudyWorldSettingsStore.DEFAULT_DURATION_MINUTES,
    lockAttemptThreshold = StudyWorldSettingsStore.DEFAULT_LOCK_ATTEMPT_THRESHOLD,
    blockAttemptCooldownMinutes = StudyWorldSettingsStore.DEFAULT_BLOCK_ATTEMPT_COOLDOWN_MINUTES
)

@Composable
internal fun rememberHomeScreenState(): HomeScreenState {
    val context = LocalContext.current
    val appContext = context.applicationContext
    val coroutineScope = rememberCoroutineScope()

    val state = remember {
        val started = SystemClock.elapsedRealtime()
        val created = HomeScreenState(
            context = context,
            sessionManager = SessionManager(),
            sessionStore = SessionStore(appContext),
            eventLogStore = EventLogStore(appContext),
            debugStateStore = DebugStateStore(appContext),
            runtimeDiagStore = RuntimeDiagStore(appContext),
            feedbackStore = FeedbackStore(appContext),
            appRulesStore = AppRulesStore(appContext),
            studyWorldSettingsStore = StudyWorldSettingsStore(appContext),
            permanentGuardrailsStore = PermanentGuardrailsStore(appContext),
            safeAppsStore = SafeAppsStore(appContext),
            protectionViolationStore = ProtectionViolationStore(appContext),
            installedAppsReader = InstalledAppsReader(appContext),
            policyEngine = PolicyEngine(),
            focusPromiseParser = FocusPromiseParser(),
            studyWorld = defaultStudyWorld(),
            createdAtElapsedMs = started
        )
        Log.d(
            "PhoneCodexUIPerf",
            "rememberHomeScreenState construct=${SystemClock.elapsedRealtime() - started}ms"
        )
        created
    }
    state.attachDiagnosticsScope(coroutineScope)
    return state
}

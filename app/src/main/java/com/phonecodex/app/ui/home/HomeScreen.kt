package com.phonecodex.app.ui.home

import android.os.SystemClock
import android.util.Log
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.phonecodex.app.domain.recovery.RecoveryPolicyDefaults
import com.phonecodex.app.ui.theme.PhoneCodexTheme

/**
 * Home is a LazyColumn of section items — only on-screen sections compose.
 * Heavy Advanced cards are separate list items, not one mega-composable.
 */
@Composable
fun HomeScreen(modifier: Modifier = Modifier) {
    val state = rememberHomeScreenState()
    val coroutineScope = rememberCoroutineScope()
    val recoveryPolicy = remember { RecoveryPolicyDefaults.default() }
    val listState = rememberLazyListState()
    val firstRenderLogged = remember { booleanArrayOf(false) }

    HomeScreenPollingEffect(state)

    LaunchedEffect(Unit) {
        state.bootstrapIfNeeded()
        if (!firstRenderLogged[0]) {
            firstRenderLogged[0] = true
            Log.d(
                "PhoneCodexUIPerf",
                "firstRender ready bootstrapped=${state.isBootstrapped} " +
                    "elapsed=${SystemClock.elapsedRealtime() - state.createdAtElapsedMs}ms"
            )
        }
    }

    val listItems by remember {
        derivedStateOf {
            buildHomeListItems(
                isAccessibilityEnabled = state.isAccessibilityEnabled,
                hasStoredSession = state.hasStoredSession,
                hasPromiseUnderstanding = state.promiseUnderstanding != null,
                showAdvancedControls = state.showAdvancedControls
            )
        }
    }

    // Inspector poll only while the debug row is actually on-screen (or nearby).
    val inspectorVisible by remember {
        derivedStateOf {
            if (!state.showAdvancedControls) return@derivedStateOf false
            listState.layoutInfo.visibleItemsInfo.any { info ->
                val key = info.key as? String
                key == HomeListItem.AdvancedDebug.id ||
                    key == HomeListItem.AdvancedEvents.id ||
                    key == HomeListItem.AdvancedDiagnostics.id ||
                    key == HomeListItem.AdvancedFeedback.id
            }
        }
    }
    val inspectorVisibleState = rememberUpdatedState(inspectorVisible)
    HomeAdvancedInspectorPollingEffect(
        state = state,
        inspectorVisible = { inspectorVisibleState.value }
    )

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        state = listState,
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 28.dp)
    ) {
        items(
            items = listItems,
            key = { item -> item.id },
            contentType = { item -> item.id }
        ) { item ->
            when (item) {
                HomeListItem.Header -> {
                    HomeScreenHeader(
                        isProtectionOn = state.isAccessibilityEnabled,
                        permanentCommitmentCount = state.enabledGuardrailCount
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                }

                HomeListItem.ProtectionSetup -> {
                    ProtectionSetupCard(
                        onOpenAccessibilitySettings = state::openAccessibilitySettings
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                }

                HomeListItem.ActiveCommitment -> {
                    val session = state.session
                    if (session != null) {
                        ActiveCommitmentCard(
                            session = session,
                            isLocked = state.isSessionLocked,
                            nowMillis = state.nowMillis,
                            recoveryPolicy = recoveryPolicy,
                            onEndCommitment = state::endCommitment,
                            onEmergencyExit = state::logEmergencyExit,
                            onCooldownUnlock = state::logCooldownUnlock
                        )
                        Spacer(modifier = Modifier.height(28.dp))
                    }
                }

                HomeListItem.PromiseComposer -> {
                    PromiseComposerSection(
                        promiseText = state.promiseText,
                        onPromiseTextChange = state::updatePromiseText,
                        onExampleSelected = state::selectExamplePromise,
                        onUnderstandPromise = state::understandPromise
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                }

                HomeListItem.PromiseUnderstanding -> {
                    state.promiseUnderstanding?.let { understanding ->
                        PromiseUnderstandingCard(
                            understanding = understanding,
                            startBlockedMessage = state.startBlockedMessage,
                            onStartCommitment = state::startCommitment,
                            onEditPromise = state::clearUnderstanding
                        )
                        Spacer(modifier = Modifier.height(28.dp))
                    }
                }

                HomeListItem.AdvancedToggle -> {
                    if (state.promiseUnderstanding == null && !state.hasStoredSession) {
                        Spacer(modifier = Modifier.height(12.dp))
                    }
                    AdvancedControlsToggle(
                        showAdvancedControls = state.showAdvancedControls,
                        onToggle = {
                            val openedAt = SystemClock.elapsedRealtime()
                            state.toggleAdvancedControls()
                            if (state.showAdvancedControls) {
                                Log.d(
                                    "PhoneCodexUIPerf",
                                    "advancedOpen requested after=" +
                                        "${SystemClock.elapsedRealtime() - openedAt}ms"
                                )
                            }
                        }
                    )
                    if (state.showAdvancedControls) {
                        Spacer(modifier = Modifier.height(16.dp))
                    }
                }

                HomeListItem.AdvancedIntro -> {
                    AdvancedIntroCard()
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedSessionTuning -> {
                    AdvancedSessionTuningCard(state = state)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedPermanentCommitments -> {
                    AdvancedPermanentCommitmentsCard(state = state)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedProtectionHealth -> {
                    AdvancedProtectionHealthCard(state = state)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedActiveSession -> {
                    AdvancedActiveSessionCard(state = state)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedRecoveryPolicy -> {
                    AdvancedRecoveryPolicyCard(recoveryPolicy = recoveryPolicy)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedAppRules -> {
                    AdvancedAppRulesCard(
                        state = state,
                        onLoadInstalledApps = { state.loadInstalledApps(coroutineScope) }
                    )
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedSafeApps -> {
                    AdvancedSafeAppsCard(
                        state = state,
                        onLoadInstalledApps = { state.loadInstalledApps(coroutineScope) }
                    )
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedEvents -> {
                    AdvancedEventsCard(state = state)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedDebug -> {
                    AdvancedDebugCard(state = state)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedDiagnostics -> {
                    AdvancedDeveloperDiagnosticsCard(state = state)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.AdvancedFeedback -> {
                    AdvancedFeedbackCard(state = state)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                HomeListItem.BottomSpacer -> {
                    Spacer(modifier = Modifier.height(32.dp))
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun HomeScreenPreview() {
    PhoneCodexTheme {
        HomeScreen()
    }
}

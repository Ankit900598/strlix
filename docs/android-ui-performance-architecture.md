# Android UI Performance Architecture

## What was slow

PhoneCodex’s home screen felt like a settings form glued together, not a product UI.

Three structural problems caused the lag:

1. **One giant `verticalScroll` Column**  
   Every section (promise UI + Advanced + debug + app lists) lived in a single scrollable Column. Expanding Advanced composed *everything* in one frame — session knobs, permanent commitments, app rules, safe apps, events, decision inspector, feedback. That is why “Advanced Controls” froze for several seconds.

2. **Polling dirtied the whole tree**  
   A 2s loop read SharedPreferences for debug state, event log, violations, and session on the main-ish path, then wrote `mutableStateOf` fields even when Advanced was closed. Compose recomposed the entire home screen every tick.

3. **Expensive work on first composition**  
   `rememberHomeScreenState()` synchronously read session prefs, accessibility settings, app rules, guardrails, safe apps, and debug/events. Package Manager was only on explicit “Load Installed Apps”, but first render still blocked on prefs. Installed-app pickers later used nested lists inside the outer scroll without a real LazyColumn contract.

Cosmetic theme tweaks cannot fix that. The architecture had to change.

## What changed

### LazyColumn home

`HomeScreen` is now a **LazyColumn of `HomeListItem` sections**.

Main items (always light):

- Header
- Protection setup (only if accessibility is off)
- Promise composer *or* active commitment
- Confirmation card (only after Understand)
- Advanced toggle

Advanced items are **separate list rows**, inserted only when Advanced is open:

- Intro, session tuning, permanent commitments, protection health
- Active session (if running), recovery policy
- App rules, safe apps
- Events, debug inspector, feedback

Compose only measures/composes visible rows. Scrolling past Advanced does not keep every inspector field alive in the composition tree the way a mega-Column did.

### Deferred bootstrap

`HomeScreenState` constructs with **empty defaults** — no SharedPreferences, no Settings, no PackageManager on the first frame.

`bootstrapIfNeeded()` loads session / accessibility / settings / rules / guardrails / safe apps on `Dispatchers.IO`, then applies snapshots. `PhoneCodexUIPerf` logs `bootstrap=` and `firstRender`.

Installed apps still load **only** on button tap, on a background dispatcher, with `installedAppsLoad=` timing.

### Advanced open path

Toggle sets `showAdvancedControls = true` immediately (shell items appear in the LazyColumn).  
`loadAdvancedSnapshotIfNeeded()` fills debug/events/violations/feedback off the main thread.  
No sync prefs wall on the click handler.

### Inspector poll only when visible

`HomeAdvancedInspectorPollingEffect` polls debug/events/violations **only while** Advanced is open *and* the events/debug/feedback rows are in the LazyColumn viewport (`layoutInfo.visibleItemsInfo`).  
Logs: `debugPoll=…ms`.

Core poll (accessibility + session expiry) remains always-on, slower when idle (3s) / faster with an active commitment (1s), and only writes state when values change.

### Installed apps lists

App Rules and Safe Apps use a **nested LazyColumn with fixed height** + `remember`-cached `filterInstalledApps()`. Parent home LazyColumn stays responsible for page scroll; the nested list virtualizes the picker.

Store mutations (apply rule, add safe app, refresh debug) go through `HomeScreenState` methods — composables do not call SharedPreferences directly.

### Stability

`HomeScreenState` is `@Stable`. List item models are `@Immutable`. List membership is built with `derivedStateOf` from lightweight flags so typing in the promise field does not rebuild the Advanced item list structure unnecessarily.

## Behavior preserved

- Promise → Understand → confirm → Start Commitment
- Active commitment card + recovery
- Advanced: duration / lock / cooldown, permanent commitments, protection health, app rules, safe apps, events, debug inspector, feedback
- Accessibility polling and session expiry
- No Package Manager until “Load Installed Apps”

## How to verify

```text
adb logcat -s PhoneCodexUIPerf
```

Expect roughly:

- `rememberHomeScreenState construct=…ms` (should be tiny)
- `firstRender ready …`
- `bootstrap=…ms`
- On Advanced: `advancedToggle open shell=…ms`, `advancedSnapshot=…ms`
- On Load Apps: `installedAppsLoad=…ms count=…`
- When inspector on-screen: `debugPoll=…ms`  
  When Advanced closed or scrolled away: no debug poll spam

Target feel: Advanced shell under ~300ms; home scroll smooth with Advanced closed.

## Remaining risks

1. **Nested LazyColumn** (installed apps) still needs a fixed height. Very long rule lists above the picker are still composed as Column children inside one Lazy item — fine for current default rule counts, not for hundreds of rules.
2. **Bootstrap race**: first frame may briefly show “protection off” / empty session until IO returns. Acceptable; avoid putting trust-critical CTAs that depend on stale a11y for more than one frame without the existing ProtectionSetup card.
3. **Store writes on click** (start commitment, toggle guardrail) still hit SharedPreferences on the main thread. Fine for small prefs; move to IO if those clicks ever feel sticky.
4. **Accessibility service** can still make the *device* feel heavy while classifying — that is separate from this home UI architecture pass.
5. **Promise Compiler** is still local heuristics; UX speed ≠ comprehension quality.

## Files touched (UI layer)

- `ui/home/HomeScreen.kt` — LazyColumn host
- `ui/home/HomeListModels.kt` — section items + filter helper
- `ui/home/HomeScreenState.kt` — async bootstrap / advanced snapshot / store APIs
- `ui/home/HomeScreenPollingEffect.kt` — core vs inspector visibility poll
- `ui/home/AdvancedControlsSection.kt` — per-card composables for lazy items
- `ui/home/AppRulesSection.kt` / `SafeAppsSection.kt` — nested LazyColumn + cached filter
- `docs/android-ui-performance-architecture.md` — this report

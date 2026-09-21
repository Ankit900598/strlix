# On-device model and Android `ROLE_ASSISTANT`

**Pass P status (2026-09-21 IST): architecture and honest Android stubs only.**

This document defines the path without presenting a model or a system role as
shipped. The current APK continues to use its existing deterministic local
commands and the configured Android API/host chat path. Azure credentials remain
on the host and are never placed in the APK.

## Current truth

| Capability | Current state |
|---|---|
| Deterministic on-device actions (`Home`, app launch, accessibility gestures) | Shipped through `LocalActions` and the existing user-enabled accessibility service |
| On-device language/vision model | **Not shipped**. `OnDeviceModel` is an interface and `UnavailableOnDeviceModel` reports `DISABLED`; it never returns fabricated model output |
| `ROLE_ASSISTANT` | **Not requested or granted**. `AssistantRoleHook` is disabled, does not launch a consent activity, and only provides a future inspection seam |
| Android assistant qualification | Not present. The APK does not declare `VoiceInteractionService` and does not handle Android's `ACTION_ASSIST` |
| Background listening or hidden model work | Not present |

The home widget, custom `com.zevi.agent.OPEN_ASSISTANT` intent, and chat
activity are app-owned entry points. They do **not** make Strlix the Android
assistant and must not be described as a granted system role.

## Pass P Android seams

The debug/release build contains these deliberately inert seams:

- `android-agent/app/src/main/java/com/zevi/agent/OnDeviceModel.java` — a
  foreground-turn interface with explicit availability, cancellation, and
  callback outcomes. A model receives only the prompt/history passed by its
  caller; it has no implicit screen, microphone, file, or accessibility access.
- `UnavailableOnDeviceModel.java` — the honest placeholder. With no model
  installed it returns `MODEL_NOT_INSTALLED` only if a development build flag is
  deliberately changed; the checked-in flag is false, so the normal result is
  `DISABLED`.
- `AssistantRoleHook.java` — a compile-safe API 29+ `RoleManager` seam. It can
  inspect availability/held state and build (but never launch) Android's
  user-consent intent when enabled by a future reviewed build.
- `app/build.gradle.kts` —
  `ON_DEVICE_MODEL_ENABLED=false` and
  `ASSISTANT_ROLE_HOOKS_ENABLED=false` for this build.

No permissions, role declarations, `VoiceInteractionService`,
`ACTION_ASSIST` filter, model asset, runtime download, or product UI were added
in Pass P. The stubs are therefore safe to compile and do not silently change
Play-facing behavior.

## Path to an on-device model

The intended production boundary is:

```text
explicit foreground Ask
        ↓
request classifier + privacy/policy gate
        ↓
OnDeviceModel adapter (text and, only when separately allowed, vision/audio)
        ↓
typed answer or typed proposed action
        ↓
user confirmation / existing LocalActions or accessibility boundary
```

A future implementation should proceed in this order:

1. **Choose a runtime and model.** Evaluate a supported Android runtime (for
   example LiteRT/MediaPipe Tasks or an OEM-supported runtime) against the
   actual minSdk/ABI matrix. Do not add a large model or a network model
   downloader until size, license, provenance, signature, rollback, and update
   behavior are decided.
2. **Add a model adapter, not model logic to the UI.** The adapter implements
   `OnDeviceModel`, exposes `READY` only after an integrity-checked model is
   available, and runs bounded foreground work on a worker executor. It must
   have cancellation, memory-pressure handling, and an explicit maximum input
   size.
3. **Keep actions typed and separate.** Model text cannot directly call ADB,
   accessibility gestures, notification APIs, contacts, messages, or payment
   flows. A small allow-listed action schema must be validated by the app,
   shown as needed, and routed through the same user-controlled action boundary
   already used by Strlix.
4. **Define a real fallback.** If the model is absent, too slow, out of memory,
   or uncertain, report that state and offer the existing cloud path only under
   the product's existing network/consent rules. Never label a cloud answer as
   on-device.
5. **Measure before enabling.** Gate rollout on task accuracy, refusal/error
   behavior, p50/p95 latency, peak memory, battery/thermal impact, model load
   time, accessibility regressions, and offline behavior on representative API
   levels and low-memory devices.

### Constraints to budget

- **Memory and thermals:** model weights, tokenizer, KV/cache, image buffers,
  and concurrent Android UI work compete for a phone's memory. No resident
  daemon or unbounded cache is assumed.
- **Latency and battery:** inference is foreground and cancellable; no hidden
  hotword loop, periodic screen capture, or background generation is implied.
- **Privacy:** screen/audio/image input is opt-in per feature and per turn;
  sensitive content is not logged; prompts, outputs, and temporary tensors have
  bounded retention and are cleared where the runtime permits.
- **Distribution:** model license, export restrictions, device download size,
  ABI coverage, signed updates, rollback, and removal must be reviewed before
  any asset ships.
- **Safety:** local inference is not a grant of authority. It cannot bypass
  Android permissions, user confirmation, accessibility enablement, or app
  security boundaries.

## Path to Android `ROLE_ASSISTANT`

On API 29+, Android's `RoleManager` exposes the `ROLE_ASSISTANT` role when the
system makes it available. Android documentation says apps must check role
availability, qualify through the required assistant surface, and obtain user
consent through the system role request flow. Role availability and
role-specific privileges are device/system dependent; they must never be
assumed.

A future, reviewed implementation would be:

1. Add only the minimum qualifying component (`VoiceInteractionService` **or** a
   correctly scoped `ACTION_ASSIST` handler) after product, privacy, and Play
   policy review.
2. Check `RoleManager.isRoleAvailable(ROLE_ASSISTANT)` and current
   `isRoleHeld(ROLE_ASSISTANT)` at runtime. The app must remain fully functional
   when the role is unavailable or held by another app.
3. Explain the change in plain language and launch
   `RoleManager.createRequestRoleIntent(ROLE_ASSISTANT)` only from an explicit
   user action. Do not deep-link, silently request, or retry the prompt in the
   background.
4. Treat the system result as a request outcome, then verify
   `isRoleHeld(ROLE_ASSISTANT)`. Only that verified state may be shown as
   **granted**. `RESULT_OK` by itself is not enough.
5. Provide a visible way to stop using the role and preserve the current
   non-role entry points. Re-check status after boot, package/system changes,
   and user revocation.
6. Re-audit sensitive data access and retention. Assistant qualification can
   involve role-specific privileges, and any call-log, SMS, microphone, or
   screen behavior requires its own least-privilege design and policy basis.

### Why this is not enabled now

The current Strlix APK has no assistant service or `ACTION_ASSIST` intent
filter, and its role hook is build-flagged off. Adding a role declaration or
claiming to replace the system assistant without the qualifying component,
user consent, verification, and policy review would be misleading and could
change access to sensitive data. Pass P intentionally does none of that.

Google Play policy eligibility and default-handler rules must be checked again
against the intended distribution and current policy before enabling this
path. An emulator setting, an ADB command, a custom app intent, or a screenshot
is not evidence that `ROLE_ASSISTANT` was granted.

## Privacy and release checklist

Before enabling either path:

- [ ] Model and model updates have documented provenance, license, integrity,
      rollback, and removal behavior.
- [ ] On-device inputs/outputs have data-flow diagrams, bounded retention, and
      no sensitive logcat/analytics payloads.
- [ ] Screen, mic, notifications, contacts, call log, and SMS are separate
      opt-in capabilities; none is inferred from model availability.
- [ ] Model output is typed, validated, cancellable, and cannot directly invoke
      privileged actions.
- [ ] Cloud fallback is visible and accurately labeled; offline failures remain
      honest.
- [ ] Role request is foreground-only, user initiated, reversible, and verified
      with `RoleManager.isRoleHeld()`.
- [ ] Android API-level/OEM behavior, Play policy, accessibility policy, and
      privacy disclosures have been reviewed for the release target.
- [ ] Real-device tests cover role unavailable, user denial, revocation,
      low-memory, thermal throttling, airplane mode, and process death.

## References

- [Android `RoleManager`](https://developer.android.com/reference/android/app/role/RoleManager)
- [AndroidX `RoleManagerCompat`](https://developer.android.com/reference/androidx/core/role/RoleManagerCompat)
- [Android `VoiceInteractionService`](https://developer.android.com/reference/android/service/voice/VoiceInteractionService)

These references describe the platform API, not a claim that Strlix currently
qualifies for or holds the role.

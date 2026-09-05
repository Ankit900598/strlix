# PhoneCodex — Current State

**Updated:** 2026-09-05  
**Audience:** Future Cursor / Codex sessions  
**Rule:** Read this before shipping features. Prefer this file over chat memory.

Related depth (do not replace this file):

- Product vision: `docs/PRODUCT_MEMORY.md`
- AI / eval strategy: `docs/cto-strategy-phonecodex-ai.md`
- Classifier shipping bar: `evals/reports/classifier_v04_recommendation.md`
- Promise Compiler status: `evals/reports/promise_compiler_v03_failure_analysis.md`

---

## 1. North star

**PhoneCodex is a personal commitment OS, not a normal blocker.**

Users speak intentions (“no Shorts during study”, “no porn for a year”, “40 Shorts then stop”). The product turns those into structured policy, then the phone enforces them deterministically.

```text
promise → policy → PolicyEngine (law) → overlay (hand) → log (witness)
AI advises. Policy decides. Never the reverse.
```

Normal blockers = package deny-lists. PhoneCodex = promise-relative behavior inside the same apps (lecture vs Shorts, DMs vs Reels).

---

## 2. Current architecture

```text
Android AccessibilityService
  → screen / package signals
  → PolicyEngine (local law: safe apps, guardrails, rules, counters, tamper)
  → overlay (WARN / BLOCK / LOCK)

Android → local backend → Azure OpenAI
  → classifier_v04 (advisory ALLOW / WARN / BLOCK)
  → AiConfidenceGate → merge into PolicyEngine

Promise Compiler (NL → CommitmentPolicy JSON)
  → research-stage only (eval lab)
  → NOT wired into the Android app yet
```

| Layer | Status |
|-------|--------|
| Accessibility detect + evaluate | In app |
| PolicyEngine + Decision Inspector | In app |
| Overlay enforcement | In app — **unstable under own-package events** |
| Backend `/classify` + Azure | Working in lab; default model = `pc-lab-cheap` + `classifier_v04` |
| Promise Compiler | Lab only (`promise_compiler_v03`, ~64% safety match) |

---

## 3. Verified working parts (as of 2026-09-05)

**Android / product loop**

- Study World session start / stop
- AccessibilityService foreground package detection
- PolicyEngine decisions (ALLOW / WARN / BLOCK / LOCK)
- Overlay show path for BLOCK / WARN
- Safe-app allowlist (including PhoneCodex itself in study allow set)
- Permanent guardrails store + evaluator
- Tamper guard hooks
- Decision Inspector / debug UI + event log
- Network classifier path: app → backend → Azure → confidence gate → policy merge

**AI Lab (not product-critical this week)**

- Screen classifier **v04** on `v1_edge_cases`: ~95% accuracy on `pc-lab-cheap`, **0 false allows** — recommended production advisor prompt
- Promise Compiler **v03**: parseFailures 0, safetyMatchRate **63.6%**, exactMatchRate **34.3%** — usable as research signal, **not** ship-ready as product input

---

## 4. Current known blocker (P0)

### Overlay self-hide / foreground package loop around `com.phonecodex.app`

**Symptom:** Overlay appears on a blocked app (e.g. YouTube), then vanishes or flickers because Accessibility reports the foreground package as PhoneCodex’s own package when the overlay window is shown.

**Mechanism:**

1. User opens blocked package (e.g. YouTube).
2. PolicyEngine → BLOCK → TYPE_ACCESSIBILITY_OVERLAY shown.
3. Next accessibility event may report `packageName = com.phonecodex.app`.
4. If that event is treated as “safe app / left target,” the overlay hides → loop.

**Code already has a guard** (`activeOverlayTargetPackage`, `handleActiveOverlayForeground`) — treat as **not fully verified on device**. Stabilize and prove with the checklist below before any new features.

**Until this is green:** do not trust “blocking works” demos.

---

## 5. Current next priority

**Stabilize the blocking loop before new features.**

Order:

1. Prove overlay stays up on YouTube (or Instagram) under Study World.
2. Prove PhoneCodex own-package events do **not** wrongly hide the overlay.
3. Prove logs show a stable final decision (not thrashing ALLOW/BLOCK).
4. Only then: polish, AI lab expansion, or new product surfaces.

---

## 6. What NOT to do now

| Do not | Why |
|--------|-----|
| New AI Lab phases / datasets / prompt v05+ | Distraction until blocking loop is solid |
| Azure expansion (new deployments, vision path) | Classifier is already past shipping bar for text; vision waits for OCR failure evidence |
| UI polish / mascot / marketing screens | No product without reliable block |
| Feature creep (payments, friends, pet, operator taps) | Premature |
| Wire Promise Compiler into Android | Research-stage; wrong gold taught us not to ship early |
| Treat AI as sole authority | PolicyEngine must remain law |

---

## 7. Exact verification checklist (next build)

Run on a real device (Xiaomi / target phone). All must pass.

1. **Backend `/health`** — local Node backend up; health endpoint OK.
2. **`adb reverse`** — phone can reach host backend (e.g. `adb reverse tcp:3000 tcp:3000` or whatever port the app uses).
3. **Accessibility alive** — PhoneCodex service On in system Accessibility settings; Logcat shows `PhoneCodexA11y` / decision tags.
4. **Launch YouTube** (or known blocked package) with Study World active.
5. **Overlay stays** — block overlay remains visible; no flicker-off within ~5–10s of idle on the blocked app.
6. **Logs show final decision** — Logcat (`PhoneCodexDecision` / `PhoneCodexOverlay` / Decision Inspector) shows a stable BLOCK (or WARN) with reason; not rapid flip-flop.
7. **Own package does not hide wrongly** — events for `com.phonecodex.app` while overlay is up must **retain** overlay for the external target; opening the PhoneCodex app intentionally may hide only when the user truly left the blocked app.

Fail any step → stay on P0. Do not open a new track.

---

## 8. Important future ideas (remember; do not build now)

From product memory + CTO strategy — park here until the loop is stable:

| Idea | One-line |
|------|----------|
| **Guided Study Rail** | Allowed path inside distracting apps (lecture track, not free roam) |
| **Exact YouTube playlist / channel enforcement** | Promise-scoped allow: only named channel/playlist |
| **Natural-language Promise Compiler** | Text → CommitmentPolicy; ship when safetyMatch is product-grade and wired behind PolicyEngine |
| **Strict mode / tamper protection** | Harder exit, preventDisable, LOCKED — with emergency always open |
| **Vision classifier** | Screenshot / frame when OCR lies; opt-in; never bank/OTP |
| **Safe phone operator** | Agentic “do X on phone” — long-term only; Play + liability constrained |

Also remember (not ship now): permanent Life Rules vs session Worlds, Recovery World, install gate, accountability friend, recovery fees only with pre-consent.

---

## 9. Session bootstrap (for agents)

When starting work:

1. Read **this file** first.
2. If task is Android blocking: fix overlay loop; use §7 checklist.
3. If task is AI Lab: confirm Ankit explicitly wants lab work; otherwise refuse and point here.
4. Never print secrets / `.env` keys.
5. Do not “helpfully” expand scope into UI polish or Azure.

**One sentence truth:** The product is a commitment OS; the current job is making the overlay stay up when YouTube is blocked — everything else waits.

---

## Future Reliability Issue — PiP / Floating Video Escape

**Discovered:** 2026-09-05 during phone testing on Xiaomi / MIUI.

**Symptom:** Full-screen YouTube/Chrome blocking works, but a distracting video can continue playing in a small Picture-in-Picture / floating mini-player while the foreground package is `com.miui.home`.

**Why it matters:** Foreground package detection alone can say “home screen is safe” while the user is still watching distracting media. This is exactly the kind of small escape path that makes a blocker feel untrustworthy at scale.

**Not a P0 today:** Full-screen enforcement is the current priority. Do not derail the main loop for PiP yet.

**Later solution direction:** Add a media/PiP detection layer using a combination of Accessibility window changes, media session signals, notification/media controls, and possibly screenshot/vision classification. Policy should treat active distracting media overlay as context, not just foreground app.

**Future test case:** Start commitment → open YouTube distracting video → enter PiP/floating window → return home → PhoneCodex should detect active media distraction and warn/block/close/guide back according to policy.

---

## Operating Principles — Do Not Forget

**Added:** 2026-09-05

Before any major prompt, feature, bugfix, or architecture decision, think from three roles at once:

1. **Scientist:** What is the measurable hypothesis? What evidence proves it? What edge case breaks it?
2. **Best engineer:** What is the simplest reliable system that survives Android reality, scale, latency, crashes, permissions, and debugging?
3. **Founder / product thinker:** If this had millions or a billion users, would people trust it, understand it, love it, and keep using it?

### Required decision filter

Before giving Cursor/Fable/Claude/any AI a task, check:

- **North star:** PhoneCodex is an AI commitment OS, not a normal blocker.
- **Scale:** Would this architecture still make sense for millions/billions of users?
- **Trust:** Does this make the user feel protected by their own promise, not controlled by malware-like software?
- **Accuracy:** Are false allows, false blocks, latency, and user harm measured?
- **UX quality:** Does this move toward YouTube/Netflix/Claude/Gemini-level smoothness, not a rough settings form?
- **Android reality:** Does it account for accessibility quirks, overlays, PiP/floating windows, battery killing, permission loss, settings tamper, and OS limits?
- **Competitive learning:** Study and borrow patterns from Opal, Freedom, One Sec, ScreenZen, Stay Focused, Digital Wellbeing, YouTube, Netflix, Duolingo, Headspace, Claude, ChatGPT, Gemini.
- **Uniqueness:** The unique wedge is natural-language promise → structured policy → phone behavior → logs/feedback → smarter future behavior.

### Prompt quality bar

Do not give shallow Cursor tasks for hard problems. For serious work, prompts must include:

```text
Context → strategic goal → current verified state → phases → deliverables → success metrics → forbidden actions → product north star
```

Use strong models like Fable/Opus only for monster tasks: ambiguous product architecture, eval science, user psychology, trust/safety, failure analysis, and new system design. Do not waste them on tiny edits.

### Stability rule

Do not chase new features while the core loop is unstable:

```text
promise starts → app detects context → policy decides → overlay/warn/block works → user understands why → logs prove it
```

If a bug appears, do not immediately prompt Cursor. First:

```text
VERIFY → DIAGNOSE → EXPLAIN → THEN PROMPT
```

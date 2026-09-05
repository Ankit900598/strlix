# Trustworthy Block Experience — Science & Product Logic

**Date:** 2026-09-05  
**Track:** AI Lab / Fable — overlay UX science (no Android code in this track)  
**Audience:** Founder + Android team  
**Status:** Design authority for next overlay UX work  
**Depends on:** `docs/CURRENT_STATE.md`, `docs/PRODUCT_MEMORY.md`, classifier_v04, Promise Compiler v03 (research)

---

## 0. One-line truth

A PhoneCodex block is not “we caught you.” It is **your earlier self enforcing a contract you signed while clear-headed.** If the overlay feels like malware, parental control, or a shame pop-up, the product is dead even if PolicyEngine is correct.

---

## 1. What the user should feel

| Feel | Status | Why |
|------|--------|-----|
| “This is my promise protecting me” | **Required** | Ownership. The block cites *their* words, not PhoneCodex morality. |
| Clarity (what / why / what next) | **Required** | Confusion → force-stop → uninstall. |
| Mild friction / seriousness | **Allowed** | Commitment without friction is theater. |
| Shame / moralizing | **Forbidden** | Shame → avoidance → disable. Recovery World exists for post-failure. |
| Anger at the product | **Failure mode** | Usually caused by wrong decision, opaque reason, or no useful next action. |
| Being watched / controlled by an app | **Failure mode** | Malware pattern. Must feel *self-chosen*, not *installed on me*. |

**Critical cut:** Do not say “stay focused!” / “you’ve got this!” / “be better.” That is wellness trash. Say: *what promise fired, what was detected, what you can do that still honors the promise.*

Emotional formula:

```text
Recognition (your promise) + Evidence (why this screen) + Agency (safe next step)
≠ Guilt + Lecture + Dead end
```

---

## 2. Decision modes — they are not the same UX

PolicyEngine emits severity. Overlay must not collapse them into one full-screen “blocked” sheet.

| Mode | Job | Duration feel | User agency | Default next step |
|------|-----|---------------|-------------|-------------------|
| **WARN** | Interrupt drift before damage | Seconds–tens of seconds; dismissible with cost | High | Continue carefully *or* return to safe path |
| **BLOCK** | Hard stop on this content/app path | Until user leaves target or chooses allowed action | Medium | Leave forbidden screen; optional guided return |
| **LOCK** | Commitment pause after strikes/tamper | Minutes (policy); harder to dismiss | Low | Wait / emergency / open PhoneCodex recovery only |
| **REDIRECT** | Block *and* move user to an allowed surface | Instant transition | Medium-high | Land on allowed lecture / rail / home study |
| **COOLING-OFF** | Time friction before any override | Fixed wait (e.g. 30–120s) | Low during wait | Timer; then limited choice |

### Mode rules (non-negotiable)

1. **WARN ≠ soft BLOCK.** WARN must be visually lighter, shorter copy, primary action is not “go away forever.”
2. **BLOCK ≠ LOCK.** BLOCK ends when the forbidden foreground leaves. LOCK survives navigation until timer/policy says otherwise.
3. **REDIRECT is a product feature, not a toast.** It requires a concrete destination (playlist, app, PhoneCodex study home). Without destination → do not fake REDIRECT; use BLOCK + “Open allowed path” CTA.
4. **COOLING-OFF is for override requests**, not for every Shorts open. Using it on every temptation trains rage-quit.
5. **Classifier advises; overlay never invents LOCK.** LOCK comes from PolicyEngine (strikes, tamper, user-preconsented lock policy).

---

## 3. Message anatomy (every overlay)

Always five parts, in this order. Omit only if mode forbids (e.g. LOCK may hide “continue”).

1. **Mode chip** — WARN / BLOCK / LOCK / REDIRECT / COOLING-OFF  
2. **Promise line** — quote or paraphrase of *user’s* commitment (max ~12 words)  
3. **Evidence line** — what we detected (package + signal), not AI poetry  
4. **Strictness cue** — SOFT / SMART / STRICT / LOCKED (one word, quiet)  
5. **Primary action** — one clear next step; secondary actions ≤2

Never lead with the app brand as judge. Lead with the promise.

**Anti-patterns:**

- “Inappropriate content detected” (parental spyware tone)
- “Stay strong!” (gym bro)
- “AI thinks you shouldn’t…” (outsources blame to model)
- Wall of settings on the overlay (Decision Inspector belongs in-app)

---

## 4. Copy by scenario

Tone: adult, specific, contract-like. Hinglish OK later; English v0 below.

### 4.1 Study drift (lecture → sidebar / unrelated tab)

| Mode | Headline | Body | Primary CTA |
|------|----------|------|-------------|
| WARN | Drift from your study promise | You asked for calculus lectures. This doesn’t look like that path. | Back to lecture |
| BLOCK | Outside your study rail | Screen doesn’t match: “YouTube for calculus only.” | Leave YouTube / Open study home |

### 4.2 Adult content guardrail (permanent or session)

| Mode | Headline | Body | Primary CTA |
|------|----------|------|-------------|
| BLOCK | Guardrail: no adult content | This hits your long-term promise — not a Study World soft rule. | Close this / Home |
| LOCK (if tamper+adult) | Guardrail locked | You asked PhoneCodex not to let this through. Pause active. | Wait / Emergency |

No “dirty” language. No shame. Name the **guardrail**, not the user’s character.

### 4.3 Shorts / Reels temptation

| Mode | Headline | Body | Primary CTA |
|------|----------|------|-------------|
| WARN (quota remaining) | Shorts on your radar | Promise: limit Shorts. You’re approaching the line. | Exit Shorts |
| BLOCK (quota hit / ban) | Shorts blocked by your promise | “No Shorts during study” / quota exhausted. | Exit Shorts |
| REDIRECT (if rail known) | Shorts aren’t on your rail | Opening your allowed lecture instead. | (auto) Open lecture |

### 4.4 Useful-but-risky WhatsApp / Instagram

| Mode | Headline | Body | Primary CTA |
|------|----------|------|-------------|
| WARN | Useful app, risky surface | DMs/college may be allowed. Feed/Reels are not under this promise. | Stay in messages |
| BLOCK | This surface isn’t allowed | Instagram Reels / gossip path vs “college team DMs only.” | Leave Reels |

Do **not** block the whole app in copy if policy is surface-level. Lying in copy destroys trust faster than a false block.

### 4.5 Tamper attempt

| Mode | Headline | Body | Primary CTA |
|------|----------|------|-------------|
| LOCK | Tamper blocked | You asked: don’t let me disable this mid-promise. | Wait out lock / Emergency |

No humor. No “nice try.” Cold, contractual.

### 4.6 Exact playlist / channel rail (Guided Study Rail preview)

| Mode | Headline | Body | Primary CTA |
|------|----------|------|-------------|
| BLOCK | Off your study rail | Allowed: [Channel/Playlist name]. This video isn’t on that list. | Open allowed playlist |
| REDIRECT | Returning to your rail | Taking you back to [Playlist]. | (auto) |

If rail metadata missing → fall back to generic study-drift copy. Never invent a playlist name.

### 4.7 Long-term promise (Life Rule / permanent guardrail)

| Mode | Headline | Body | Primary CTA |
|------|----------|------|-------------|
| BLOCK | Active life rule | This isn’t a 2-hour study timer. You set this for [duration]. | Acknowledge / Home |

Difference from session block: say **life rule / long-term**, so users don’t think “session ended wrong.”

---

## 5. Overlay actions

### 5.1 Offer (by mode)

| Action | WARN | BLOCK | LOCK | REDIRECT | COOLING-OFF |
|--------|------|-------|------|----------|-------------|
| Return to previous / leave app | ✓ | ✓ primary | — | after land | after timer |
| Open allowed lecture / rail | if known | if known | — | auto | — |
| Review promise (read-only sheet) | ✓ | ✓ | ✓ (read-only) | ✓ | ✓ |
| Emergency exception | always visible, de-emphasized | always | always | always | always |
| Continue anyway (costs strike) | SOFT/SMART only | NEVER in STRICT/LOCKED | NEVER | NEVER | after timer + policy |
| Reflect later (schedule debrief) | optional | optional | after unlock | optional | optional |
| Open PhoneCodex Decision Inspector | deep link secondary | secondary | secondary | — | — |

### 5.2 Never offer on overlay

| Action | Why |
|--------|-----|
| “Disable PhoneCodex” / “Turn off for 15 min” | Easy disable = product is a joke in STRICT/LOCKED |
| “Ignore anyway” under STRICT/LOCKED | Contradicts pre-consent; use COOLING-OFF + Recovery World later |
| Full settings / guardrail editor | Too much power mid-temptation; edit only in Normal World or with friction |
| Share to social / streak flex | Gamification mid-block is trash |
| Payment / unlock for money (v0) | Not built; never surprise-charge |
| Blame AI (“Model said so”) | Undermines PolicyEngine-as-law |

**Emergency** is not “I want Instagram.” Emergency = calls, safety, critical device function. Copy must say so. Misuse can still open a path but should log `emergency_claimed` for later accountability UX — not silent unlimited bypass.

---

## 6. Tone by strictness

Same decision, different voice and agency.

| Strictness | Voice | WARN | BLOCK continue? | Visual weight |
|------------|-------|------|-----------------|---------------|
| **SOFT** | Coach-contract: “You asked me to nudge.” | Gentle; dismiss easy | Soft continue OK | Light sheet / partial |
| **SMART** | Peer-contract: “Drift detected; your call with a cost.” | Clear cost (strike) | Continue = +strike | Medium |
| **STRICT** | Guard-contract: “This path is closed for this session.” | Rare; escalate fast | No continue | Full-screen |
| **LOCKED** | Vault-contract: “You locked this; I won’t open it casually.” | Almost never | No; timer/emergency only | Full-screen + timer |

**Rule:** Strictness changes **agency and friction**, not morality volume. LOCKED does not mean crueler words; it means fewer doors.

---

## 7. Not feeling like malware / parental control

Competitors die here. Checklist for every overlay revision:

| Malware / control smell | PhoneCodex antidote |
|-------------------------|---------------------|
| No explanation | Always promise + evidence |
| Cannot leave / trapped | Emergency always; LOCK has timer + Recovery World path |
| Hides system UI forever | Never block dialer/SOS; never trap in accessibility settings mid-emergency |
| Brand as authority | Promise as authority; brand is executor |
| Dark patterns to re-enable | Friction is pre-consented and explained at session start |
| Silent screenshot / “we’re watching” | No voyeur copy; Decision Inspector is user-facing transparency |
| Uninstall friction theater | Don’t fight uninstall with scare UI; earn keep via trust |

**Pre-consent screen (before Study World / LOCKED)** must preview: what will be blocked, what WARN vs BLOCK means, that emergency stays, how to end session when timer allows. Overlay is enforcement of that preview — not a surprise constitution.

---

## 8. How the block screen increases trust over time

Trust compounds only if decisions are **legible and consistently correct**.

1. **Cite the promise every time** → user learns the mapping: words → behavior.  
2. **Stable evidence language** → same Shorts player → same evidence phrase (not random LLM poetry).  
3. **Admit uncertainty** (SMART only): if classifier confidence low and policy didn’t hard-ban, prefer WARN over BLOCK. Wrong BLOCK is worse than missed WARN.  
4. **Post-session reflect** (optional, not on overlay): “3 Shorts blocks, 1 false? Mark wrong.” Feeds FeedbackMemory — user trains the companion.  
5. **Never gaslight.** If we blocked wrong, Decision Inspector + “This was wrong” must exist later. Hiding errors = spyware psychology.  
6. **Streak of correct blocks > motivational quotes.** Trust is accuracy + honesty, not warmth.

---

## 9. What to log (for better decisions)

Log for product science — not for surveillance theater. Prefer on-device; cloud only with existing classify consent.

| Field | Why |
|-------|-----|
| `decision` (WARN/BLOCK/LOCK/REDIRECT/COOLING_OFF) | Funnel |
| `strictnessLevel` | Tone/agency audits |
| `promiseId` / promise fingerprint + short paraphrase shown | Copy ↔ policy alignment |
| `reasonCategory` + `evidenceSignals` (shorts_player, adult, off_rail, …) | Classifier/policy debug |
| `packageName` + surface hint | Same-app different surfaces |
| `confidence` + `source` (policy / AI / guardrail / tamper) | Who decided |
| `overlayActionsOffered[]` / `actionTaken` | CTA usefulness |
| `timeToActionMs` / `timeVisibleMs` | Friction calibration |
| `dismissedWithoutAction` | Rage / confusion signal |
| `emergencyClaimed` | Abuse vs real safety |
| `userMarkedWrong` (later) | Gold for evals |
| `railId` / playlist if any | Guided Study Rail |

**Do not log:** message bodies, OTPs, passwords, full screenshots by default, contact names beyond “family exception used.”

---

## 10. Connection to Guided Study Rail & Promise Compiler

```text
Promise Compiler (research → later product)
  → CommitmentPolicy (allowedApps scopes, blockedContent, guardrails, lock/strike)
       ↓
PolicyEngine + classifier_v04
  → decision + reasonCategory
       ↓
Overlay UX (this doc)
  → promise-cited copy + mode-correct actions
       ↓
Guided Study Rail (future)
  → REDIRECT destinations + “open allowed lecture” become real, not placeholders
```

| Future piece | Overlay implication |
--------------|---------------------|
| Promise Compiler | Overlay headline can use compiled `followUpQuestion` only if unanswered; otherwise use structured fields (scope `calculus_only`, guardrail ids) — **never raw LLM apology** |
| Guided Study Rail | Unlocks true REDIRECT; without rail metadata, don’t pretend |
| Permanent guardrails | Copy branch “life rule” vs “session rule” |
| Recovery World | After LOCK ends / session fail — separate surface; not the block overlay |

Until Promise Compiler is wired, Android may use **session goal string + rule labels** as the “promise line.” Do not wait for compiler to ship trustworthy copy.

---

## 11. Decision / action matrix (engineering)

| Trigger | Typical decision | Overlay mode | Primary CTA | Forbidden CTA |
|---------|------------------|--------------|-------------|---------------|
| Shorts player + study ban | BLOCK | BLOCK | Leave Shorts | Continue |
| Shorts + quota remaining + nudge promise | WARN | WARN | Exit Shorts | Disable app |
| Shorts + quota 0 | BLOCK | BLOCK | Leave | Continue |
| Adult + guardrail | BLOCK | BLOCK | Home | Ignore |
| Off playlist + rail configured | BLOCK or REDIRECT | REDIRECT if dest else BLOCK | Open playlist | Continue |
| IG Reels + DM-only promise | BLOCK | BLOCK | Leave Reels | Open settings |
| WA / IG DM allowed surface | ALLOW | none | — | — |
| Strike threshold hit | LOCK | LOCK | Wait / Emergency | Continue |
| Tamper / disable attempt | LOCK | LOCK | Wait / Emergency | Disable |
| User requests override mid-STRICT | COOLING-OFF | COOLING-OFF | Wait | Instant ignore |
| Low AI confidence + no hard rule | WARN or ALLOW | WARN if shown | Continue carefully | Hard BLOCK from AI alone |
| Emergency / SOS / dialer | ALLOW | none | — | Never overlay |

---

## 12. Edge cases

| Edge | Correct behavior |
|------|------------------|
| Overlay shows; foreground becomes `com.phonecodex.app` | Retain overlay for external target (P0 stability) — UX copy must not say “PhoneCodex blocked” as if self-blocked |
| User opens PhoneCodex intentionally during BLOCK | Allow; hide overlay only when leaving blocked target is confirmed |
| False adult on “adult learners” article | Prefer WARN or ALLOW via classifier_v04 rules; if BLOCK, user needs “mark wrong” later |
| Useful Chrome research looks like entertainment | WARN first under SMART; STRICT may BLOCK — copy must say “doesn’t match study promise,” not “entertainment detected” |
| Family WhatsApp during monk | No overlay if emergency/family exception; if shown wrongly → trust death |
| Double WARN spam on same surface | Throttle; one WARN per signature per N minutes |
| LOCK while on call | Never cover in-call UI; defer LOCK UI until call ends if needed |
| PiP / floating video | Out of scope this track; when built, same promise citation rules apply |
| Content filter / classify failure | Policy-only path; overlay: “Couldn’t verify screen — holding to your hard rules” if guardrail fires; else don’t invent BLOCK |

---

## 13. Design principles (checklist)

1. **Promise is the protagonist; PhoneCodex is the executor.**  
2. **Mode fidelity** — WARN/BLOCK/LOCK/REDIRECT/COOLING-OFF are different products sharing one shell.  
3. **One primary action.**  
4. **Evidence over vibes.**  
5. **Agency scales with strictness, not insult volume.**  
6. **Emergency is sacred and narrow.**  
7. **No mid-temptation constitution editing.**  
8. **Wrong blocks must be confessable later.**  
9. **REDIRECT without destination is a lie — don’t ship it.**  
10. **If copy could appear in a parental-control app unchanged, rewrite it.**

---

## 14. Engineering requirements (Android team)

No implementation in this track — requirements only.

1. **OverlayViewModel / state** must carry: `mode`, `strictness`, `promiseLine`, `evidenceLine`, `reasonCategory`, `actions[]`, `lockEndsAt?`, `redirectTarget?`, `emergencyAvailable=true`.  
2. **Copy templates** keyed by `(reasonCategory × mode × strictness)` — not free-form LLM on-device for v1. Classifier `reason` may fill evidence slot only after sanitization.  
3. **Separate layouts or clear variants** for WARN (non-full or lighter) vs BLOCK/LOCK (full-screen).  
4. **Action handlers** must call PolicyEngine / session APIs (strike increment, lock start) — UI cannot “continue” without recording.  
5. **Own-package / overlay retain** behavior remains P0; new UX must not regress `activeOverlayTargetPackage` logic (`docs/CURRENT_STATE.md`).  
6. **Logging** fields in §9 via existing EventLogStore / Decision Inspector.  
7. **Pre-consent** screen before STRICT/LOCKED sessions summarizing overlay behavior.  
8. **Do not** put Promise Compiler network calls on the overlay path.  
9. **Accessibility:** overlay must not trap TalkBack users without Emergency; content descriptions for mode + CTAs.  
10. **Test hooks:** debug trigger to force each mode with fixture promise lines for phone QA.

---

## 15. Success criteria — phone testing

Pass all before calling overlay UX “done.”

| # | Test | Pass condition |
|---|------|----------------|
| 1 | Study World + open Shorts | BLOCK (or WARN if policy says) with promise line visible; primary CTA works |
| 2 | Same Shorts within 10s | No flicker / self-hide from `com.phonecodex.app` events |
| 3 | WARN under SMART | User can dismiss with recorded strike; STRICT path has no “ignore” |
| 4 | Adult guardrail hit | Copy says guardrail/life rule; no shame words |
| 5 | Tamper / disable attempt | LOCK copy; Emergency visible; no Disable CTA |
| 6 | Emergency path | One tap reaches dialer/SOS without dead end |
| 7 | Review promise | Read-only promise text matches session goal |
| 8 | Decision Inspector | Last overlay decision visible with same reasonCategory |
| 9 | Blind user quote test | After block, user can say in one sentence *which promise* fired — if they only say “the app blocked me,” copy failed |
| 10 | Uninstall temptation | After 5 correct blocks, user does not feel “spied on” in verbal debrief (founder dogfood) |

**Fail any of 1–6 → not shipable.** 9–10 are product-quality bars, not optional fluff.

---

## 16. Brutal anti-goals

- Motivational posters on a block screen.  
- Cute mascot pleading mid-temptation (park Focus pet for Recovery World).  
- One full-screen for WARN and LOCK.  
- “Ignore” as the biggest button.  
- Explaining Azure / model names to end users.  
- Building Guided Study Rail UI before BLOCK copy cites promises correctly.

---

## 17. Recommended Android sequence (after P0 overlay stability)

1. Structured overlay state + templates for WARN vs BLOCK vs LOCK.  
2. Promise-line + evidence-line wiring from session/goal/guardrail ids.  
3. Action matrix (§11) with strike/lock side effects.  
4. Logging (§9).  
5. Pre-consent copy for STRICT/LOCKED.  
6. Only then: REDIRECT stubs when rail metadata exists; COOLING-OFF for override requests.

---

**Bottom line:** The trustworthy block experience is **contract enforcement UX**. If Ankit ships warmth without specificity, users will feel controlled. If he ships cold specificity with a clear next allowed action, users will feel protected by themselves — which is the only durable retention story for a commitment OS.

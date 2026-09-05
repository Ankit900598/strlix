# Classifier v03 Design — Decision Philosophy

**Date:** 2026-09-05  
**Prior prompt:** `evals/prompts/classifier_v02.txt` (84% on `v0_challenge`, 0 false allows, 0 false blocks)  
**Eval report analyzed:** `evals/reports/azure_openai_20260905_081406.csv`  
**Target prompt:** `evals/prompts/classifier_v03.txt`

## Product truth

PhoneCodex is **not** “block Shorts always.” It converts a user's **natural-language promise** into reliable phone behavior. The classifier advises; PolicyEngine decides.

**Same screen → different decisions** depending on `userGoal`, `strictnessLevel`, `activeGuardrails`, and counters. The model must reason about **promise modality**, not app reputation.

---

## v02 remaining failures (8) — all boundary mistakes

| Case | Expected | Got | Boundary |
|------|----------|-----|----------|
| `ch_yt_shelf_wording_warn_001` | WARN | ALLOW | Drift-affordance + explicit nudge promise |
| `ch_ig_dm_project_allow_001` | WARN | ALLOW | Social channel friction during narrow social promise |
| `ch_chrome_compsci_meme_warn_001` | WARN | BLOCK | Discouraged ≠ forbidden |
| `ch_gpt_laugh_study_warn_001` | WARN | BLOCK | Off-goal detour ≠ clear violation |
| `ch_set_wifi_normal_warn_001` | WARN | ALLOW | Study focus + neutral system surface |
| `ch_home_messy_icons_warn_001` | WARN | ALLOW | Study focus + visible distraction affordance |
| `ch_chrome_so_with_meme_ad_allow_001` | ALLOW | WARN | Foreground study beats ambient ad noise |
| `ch_wa_useful_monk_warn_001` | WARN | ALLOW | Monk + useful social = friction not alignment |

**Pattern:** v02 fixed false BLOCKs but lacks a coherent **ALLOW ↔ WARN ↔ BLOCK** philosophy. The model still collapses to “aligned = ALLOW” or “off-goal = BLOCK.”

---

## Core decision framework (v03)

Every case is evaluated on **three axes**:

| Axis | Question |
|------|----------|
| **Alignment** | Does foreground activity match what the promise permits? |
| **Violation clarity** | Is a forbidden activity *actively happening* (not merely possible)? |
| **Friction intent** | Does the promise ask for nudges, or is the session in high-focus mode? |

**Decision = combine axes + strictness + guardrails.** Never decide from `packageName` alone.

```
                    violation clarity
                           │
              low ─────────┼───────── high
                           │
         friction high     │     BLOCK (clear violation)
              │            │            │
              ▼            │            ▼
            WARN           │          LOCK (tamper only)
              │            │
         friction low      │
              │            │
              ▼            ▼
            ALLOW ◄── alignment high, no active violation
```

---

## When neutral surfaces should be ALLOW

**ALLOW** neutral/system surfaces when **all** apply:

1. **Foreground is neutral** — launcher not opened into app, Wi‑Fi status, blank tab, phone call, family message allowed by promise.
2. **No active violation** — user is not inside Shorts/Reels player, streaming movie under edu ban, explicit adult, install gate violation.
3. **Promise is permissive OR surface is essential** — guardrail-only (“my choice”), emergency, allowed communication, quota under limit.
4. **No explicit nudge request** — userGoal does not ask to “warn/ping/nudge if I drift.”
5. **No high-friction focus cue** — distracting affordances absent (study-icon home, not TikTok dock).

**Examples → ALLOW**

- Guardrail-only home with social icons visible (`ch_home_guardrail_allow`)
- Study home with calculator/notes only (`ch_home_study_icons`)
- Stack Overflow question with meme **sidebar ad** — study foreground wins (`ch_chrome_so_with_meme_ad`)
- Academic WhatsApp under study promise (`ch_wa_lab_partner`)
- Long lecture with shelf visible when promise says lecture is fine (`ch_yt_shelf_wording_allow`)

---

## When neutral-but-risky surfaces should be WARN

**WARN** = uncertain, drift-risk, or promise requests **friction** — not punishment.

Use WARN when **any** apply:

1. **Insufficient evidence** — loading, unread count only, about:blank, partial OCR.
2. **Drift affordance visible, not entered** — Shorts/Reels shelf, carousel, notification shade, distracting icons on home **during study/focus promise**.
3. **Promise requests nudges** — userGoal contains warn / ping / nudge / drift / “if I open” language **and** screen shows the risky affordance (even if foreground content is aligned).
4. **Social channel under narrow promise** — Instagram DM, gossip, hostel chat during study; work-related content still gets friction because channel is distracting.
5. **Discouraged off-goal content** — memes, comedy, humor when promise says “no memes” / “no comedy detours” but not monk/zero-fun → **WARN not BLOCK**.
6. **Monk/zero-fun + borderline useful social** — lab partner message: useful but still social under zero-fun → WARN.
7. **Active study/focus + benign system detour** — Wi‑Fi settings, battery, browsing settings list during “finish assignment” → gentle WARN (`neutral_navigation`).
8. **Torn between ALLOW and BLOCK** — default WARN (safety without false hard blocks).

**Examples → WARN**

- Lecture + micro-clips shelf + promise says “ping if I drift” (`ch_yt_shelf_wording_warn`)
- Wi‑Fi settings during study session (`ch_set_wifi_normal`)
- Home with TikTok/IG icons during study (`ch_home_messy_icons`)
- IG DM for presentation under “college work only on social” (`ch_ig_dm_project`)
- ProgrammerHumor when memes discouraged (`ch_chrome_compsci_meme`)
- Comedy ChatGPT when assignment focus forbids detours (`ch_gpt_laugh_study`)
- Lab partner WA under monk mode (`ch_wa_useful_monk`)

---

## When clear promise violation should be BLOCK

**BLOCK** only when **all** apply:

1. **Forbidden activity is actively happening** — inside vertical feed, watching stream under edu-only, installing banned app, explicit adult with guardrail, dating app under dating ban.
2. **Promise clearly prohibits it** — not merely “discouraged” or “prefer not.”
3. **Not explainable as neutral navigation or mention-only** — #shorts in comment ≠ BLOCK; Shorts player swipe feed = BLOCK.

**Never BLOCK for:**

- Neutral launcher / settings browse / blank tab / unread preview
- Foreground-aligned study with ambient distraction (ads, shelves not opened)
- Discouraged memes/comedy/gossip without monk/zero-fun — use WARN
- Guardrail-only promise on non-adult entertainment

**Examples → BLOCK**

- Active short-form feed when promise forbids vertical clips
- Movie streaming under research-only promise
- Meme sticker spam under monk/zero-fun
- Tinder install under adult/dating guardrail
- Quota/limit reached while in short-form player

---

## How STRICT and LOCKED change thresholds

`strictnessLevel` **tunes friction**, not morality. It does not mean “always BLOCK.”

| Level | ALLOW ↔ WARN threshold | WARN ↔ BLOCK threshold |
|-------|------------------------|-------------------------|
| **SOFT** | Wider ALLOW; WARN only on clear drift | BLOCK rarely; needs explicit prohibition + active violation |
| **SMART** | Balanced default | BLOCK on clear violations |
| **STRICT** | Narrower ALLOW on ambiguous; neutral system use → WARN during focus | BLOCK on active forbidden content |
| **LOCKED** | Same as STRICT for content; **adds LOCK path for tamper only** | LOCK ≠ BLOCK everything; only PhoneCodex disable attempts |

**LOCKED rule:** Increases protection against **tamper** (disable PhoneCodex). Does **not** justify BLOCK on settings browse, home, or academic messages.

**STRICT rule:** During study/focus promises, prefer **WARN over ALLOW** on neutral-but-risky surfaces. Does **not** justify BLOCK on memes/comedy — still WARN unless monk.

---

## How permanent guardrails override normal goals

Guardrails are **hard law** from PolicyEngine. They override entertainment allowances in `userGoal`.

| Guardrail | BLOCK when | Does NOT block |
|-----------|------------|----------------|
| `no_adult_content` | Explicit sexual content, porn age gates, 18+ explicit previews, dating/hookup apps when promise covers dating | Free movies, “adult learners” news, “mature discussion” academic forums |
| (future) | Catalog-defined | — |

**Interaction with decisions:**

- Guardrail hit + active violation → **BLOCK** (even if quota allows Shorts)
- Guardrail-only promise (no study ban) → user chooses entertainment → **ALLOW** non-adult content
- Guardrails do **not** turn neutral home/settings into BLOCK

**Quota example:** 12/40 Shorts allowed + adult Short → **BLOCK** (`adult_content`), not ALLOW.

---

## v03 changes over v02 (philosophy, not wording)

| v02 gap | v03 principle |
|---------|----------------|
| Aligned foreground → always ALLOW | Split **foreground alignment** vs **ambient risk**; ambient + focus promise → WARN |
| Off-goal → BLOCK | **Discouraged** → WARN; **forbidden + active** → BLOCK |
| Neutral surfaces → ALLOW | Study/focus promise → neutral system surfaces → WARN; permissive promise → ALLOW |
| Ignores nudge promises | If userGoal requests nudges + drift affordance → WARN even when foreground aligned |
| Monk useful social → ALLOW | Monk + social (even useful) → WARN unless emergency/family explicitly allowed |
| Sidebar ad → WARN | Foreground study content **ALLOW**; peripheral ads do not downgrade |

---

## How to run v03 eval

```bash
python evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt evals/prompts/classifier_v03.txt
```

**Success gates (vs v02 @ 84%):**

| Metric | v02 | v03 target |
|--------|-----|------------|
| Accuracy | 84% (42/50) | ≥ 90% (45/50) |
| False allows | 0 | 0 (hard) |
| False blocks | 0 | 0 (hard) |
| Boundary fixes | — | Resolve 6+ of 8 v02 failures |

Re-run `v0_seed` and confirm safety cases (adult, tamper LOCK, short-form BLOCK) still pass.

---

## Policy vs classifier (unchanged)

- **Classifier (v03):** alignment, violation clarity, friction intent → advisory decision
- **PolicyEngine:** counters, guardrail catalog, attempt LOCK math, final merge
- **Baseline adapter:** keyword floor for regression only

The prompt teaches **how to think** about promises. Wording lists are examples, not the law.

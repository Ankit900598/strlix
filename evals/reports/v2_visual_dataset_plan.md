# v2 Visual Cases — Dataset Plan

**Date:** 2026-09-05  
**Phase:** AI Lab (next after v1_edge_cases + classifier_v04)  
**Working name:** `v2_visual_cases`  
**Target files (future):** `evals/datasets/v2_visual_cases.jsonl`, `evals/fixtures/screenshots/v2/`  
**Vision deployment:** `pc-lab-vision` (gpt-4o) on `ay186mnc-1561-resource`  
**Status:** Plan only — no app/backend changes in this phase

---

## Why v2 exists

v1 proved promise-relative reasoning on **clean `screenText`**. Model matrix showed **pc-lab-vision = pc-lab-strong** when no image is attached — vision is wasted spend today.

Production PhoneCodex will not receive perfect accessibility trees. Real inputs are:

- Truncated or reordered OCR
- WebViews with missing node labels
- Icon-only UI (Reels tab selected, Shorts player chrome)
- Misleading text (“Shorts” in a comment, “adult” in a headline)
- Loading / blank / overlay states

**v2_visual_cases** tests whether multimodal classification improves **safety and boundary accuracy** when text is incomplete, ambiguous, or wrong — using curated screenshots (and optional short screen recordings later) as ground-truth evidence.

**Success criteria (proposed):**

| Metric | v1 text-only (v04 cheap) | v2 target |
|--------|--------------------------|-----------|
| False allows | 0 on v1 | **0** on v2 visual subset |
| False blocks | ≤1 | ≤2 (harder OCR traps) |
| Accuracy vs text-only baseline | 94.7% v1 | ≥ same on paired cases where vision should help |
| Vision lift over text-only | 0pp today | **≥+5pp** on vision-critical cluster |

If vision does not beat text-only on v2, **do not ship gpt-4o to production** — keep cheap text path + better OCR.

---

## Relationship to existing evals

```text
v0_seed (100)     → plumbing, overfit risk
v0_challenge (50) → generalization smoke
v1_edge_cases (114) → promise modality, paired goals, clean screenText
v2_visual_cases (~80–120 planned) → same promise logic + screenshot evidence
```

**Design principle:** Reuse v1 **case IDs and labels** where possible. For each visual case, ship:

1. `screenshotPath` — relative path under `evals/fixtures/screenshots/v2/`
2. `screenText` — deliberately imperfect (truncated, missing, or misleading) to simulate live OCR
3. Same `userGoal`, counters, guardrails as v1 paired case when applicable

This isolates **vision value**: same promise, worse text, image disambiguates.

Schema already supports optional `screenshotPath` in `evals/datasets/schema.json` — no schema break required for v2 v1.

---

## Screenshot categories (required coverage)

Each category below needs **minimum case counts**, **vision-critical signals**, and **paired text traps**.

### Category summary table

| # | Category | Min cases | Vision-critical? | v1 text cluster |
|---|----------|----------:|:----------------:|-----------------|
| 1 | YouTube long video | 12 | Medium | `yt_lecture_shelf` |
| 2 | YouTube Shorts | 14 | **High** | `yt_shorts_*` |
| 3 | Chrome adult page | 10 | **High** | `ch_real_adult` |
| 4 | Movie page false positive | 8 | **High** | `ch_false_adult`, `ch_movie_guardrail` |
| 5 | WhatsApp useful chat | 10 | Low–Medium | `wa_*` |
| 6 | Instagram feed vs DM vs Reels | 14 | **High** | `ig_*` |
| 7 | Play Store install page | 10 | Medium | `ps_*` |
| — | **Cross-cutting OCR traps** | 12 | **High** | loading, blank, partial |
| | **Total (planned)** | **~90–100** | | |

---

### 1. YouTube — long video

**What to capture**

- Full-width 16:9 player with progress bar (45–90 min duration visible)
- Title overlay: lecture / tutorial (e.g. “Organic Chemistry — Chapter 7”)
- **Shorts shelf row below player** — thumbnails visible, tab not selected
- Optional variants: Home with recommended long videos + Shorts row label; PiP corner lecture

**Fixture naming:** `v2/yt/lecture_shelf_{001-004}.webp`

**Paired promises (from v1):**

| Variant | userGoal gist | Expected |
|---------|---------------|----------|
| A | Long lectures fine | ALLOW |
| B | Warn if I drift toward Shorts | WARN |
| C | Zero short-form / exam week | BLOCK |
| D | Monk mode study only | BLOCK |

**Why screenshot matters**

Text-only can say “Shorts shelf visible (not opened)” — live OCR often returns only video title + duration. Vision confirms: **horizontal player + shelf geometry**, not Shorts vertical feed.

**Text trap for eval:** `screenText` = title + duration only (no “shelf” token).

---

### 2. YouTube — Shorts

**What to capture**

- Vertical full-screen Shorts player (9:16)
- Shorts tab highlighted or “Shorts” header chip
- Swipe-up hint, like/comment icons on right rail
- Quota variant: same UI with session overlay mock (optional)
- **Negative pair:** long video thumbnail in search results (horizontal) — not Shorts player

**Fixture naming:** `v2/yt/shorts_player_{001-006}.webp`, `v2/yt/not_shorts_horizontal_{001-002}.webp`

**Subtypes**

| Subtype | Expected under study ban |
|---------|---------------------------|
| Active Shorts swipe feed | BLOCK |
| Quota 18/40 + Shorts player | ALLOW |
| Quota 40/40 + Shorts player | BLOCK |
| Guardrail-only + non-explicit Shorts | ALLOW |
| Mature comedy Shorts preview + guardrail | BLOCK |
| Search result horizontal thumbnail | ALLOW or WARN (not BLOCK) |

**Why screenshot matters**

OCR may omit “vertical” / “swipe”. Image shows **aspect ratio + player chrome** — the strongest signal for short-form **active** vs **mentioned**.

**Text trap:** `screenText` = “Dance trend #47” only (no “Shorts” word).

---

### 3. Chrome — adult page

**What to capture**

- Age gate: “18+”, “Verify age”, “Enter site”
- Explicit warning interstitial (wording varies by site — use **synthetic/staged** fixtures, not real porn URLs in repo)
- Search results page with clear sexual intent in snippets (blurred/staged)
- Dating/hookup landing (Tinder-style layout — can use Play Store or web landing mock)

**Fixture naming:** `v2/chrome/adult_gate_{001-003}.webp`, `v2/chrome/explicit_landing_{001-002}.webp`

**Safety for dataset**

- **No real explicit imagery** in fixtures — age gates, blur overlays, warning text only
- Store under private `evals/fixtures/` — never commit user device captures without consent
- Label `notes` with `[synthetic]` or `[redacted]`

**Why screenshot matters**

Guardrail triggers on **UI patterns** (age gate modal, verify button), not keyword “adult” in paragraph text.

**Text trap:** `screenText` = “Verify to continue” (ambiguous without page chrome).

---

### 4. Chrome — movie page false positive

**What to capture**

- Free streaming landing (“Watch HD movies”) — **no** age gate
- IMDb / parent guide: “mature themes discussed”
- News article: “adult learners return to college”
- Gmail: “Congratulations — you are shortlisted”
- Academic page: “adult stem cells” / “mature discussion forum”

**Fixture naming:** `v2/chrome/fp_movies_{001-002}.webp`, `v2/chrome/fp_adult_word_{001-004}.webp`

**Expected:** ALLOW under `no_adult_content` guardrail-only or study promise.

**Why screenshot matters**

Text-only classifiers false BLOCK on substring “adult”, “mature”, “short” in `shortlisted`. Vision shows **article layout vs age gate vs email UI**.

**Text trap:** include trap substring in `screenText`, omit layout cues.

---

### 5. WhatsApp — useful chat

**What to capture**

- Lab partner thread: PDF attachment, “problem set 6”
- Family: “Dinner ready?” (allowed family promise)
- Gossip: “tea about professor” (WARN)
- Meme/sticker spam chain (BLOCK under monk)
- Incomplete: chat list “5 unread” only

**Fixture naming:** `v2/wa/useful_{001-002}.webp`, `v2/wa/gossip_{001}.webp`, `v2/wa/meme_monk_{001}.webp`

**Why screenshot matters**

Moderate — message bubble layout + media icons help when OCR drops sender name. High value for **monk + sticker grid** (visual spam vs single text line).

**Text trap:** `screenText` = first line only without “Forwarded” / sticker grid context.

---

### 6. Instagram — feed vs DM vs Reels

**What to capture**

| Surface | Visual tells |
|---------|--------------|
| **Feed** | Single column posts, no full-screen vertical video, home icon selected |
| **DM** | Thread UI, back arrow, username header, no Reels tab |
| **Reels** | Full-screen vertical video, Reels tab active, swipe-up affordance |

**Fixture naming:** `v2/ig/feed_{001-002}.webp`, `v2/ig/dm_work_{001-002}.webp`, `v2/ig/reels_player_{001-003}.webp`

**Paired promise:** “Posts OK, no Reels” — same promise, three surfaces → ALLOW / WARN / BLOCK.

**Why screenshot matters**

**Highest ROI category after Shorts.** OCR often says “Reels” on feed (thumbnail caption) without player open. Vision distinguishes **tab state + layout**.

**Text trap:** `screenText` = “Reels” word on feed post caption only.

---

### 7. Play Store — install page

**What to capture**

- Productivity: Anki, Notion, Forest — green “Install” / “Open”
- Entertainment: TikTok, BGMI — vertical video / game art
- Dating: Tinder — guardrail BLOCK
- Same TikTok listing under guardrail-only promise → ALLOW (non-adult app)

**Fixture naming:** `v2/ps/productivity_{001-002}.webp`, `v2/ps/tiktok_{001}.webp`, `v2/ps/tinder_{001}.webp`

**Why screenshot matters**

App icon + category chips + “Contains ads” / age rating badge — OCR misses **Play Store age rating (Mature 17+)** vs **Everyone**.

**Text trap:** `screenText` = app name only (“TikTok”).

---

## What image evidence matters

Vision is not “see the screen prettier.” It is **disambiguate structure when text lies or is incomplete.**

### Signal hierarchy (what models should weight)

| Priority | Visual signal | Decisions affected |
|----------|---------------|-------------------|
| P0 | **Aspect ratio + player chrome** (9:16 full bleed vs 16:9 letterbox) | Shorts/Reels BLOCK vs lecture ALLOW |
| P0 | **Modal age gate** (overlay, verify button, 18+ badge) | adult_content BLOCK |
| P0 | **Tab / nav selected state** (Reels tab, Shorts tab) | short_form_disallowed |
| P1 | **Shelf vs player** (horizontal row of vertical thumbnails below player) | WARN/BLOCK under shelf rules |
| P1 | **Play Store age rating badge** | install + guardrail |
| P1 | **Thread vs feed layout** (DM header vs infinite scroll) | social WARN vs ALLOW |
| P2 | **Sticker/media grid density** | monk BLOCK vs WARN |
| P2 | **Status bar / loading skeleton** | ambiguous WARN |
| P3 | **App icon on home** (not opened) | WARN friction only |

### What image evidence should NOT drive alone

- App icon brand (YouTube logo ≠ Shorts)
- Dark mode / OEM skin colors
- Time of day in status bar
- Notification peek content (unless foreground)

Promise (`userGoal`) still dominates — vision resolves **what activity is happening**, not **whether user allowed it**.

---

## What text-only AI cannot see

These are **concrete v1 failure modes** that clean `screenText` hid but live phones produce.

| Gap | Live phone reality | Text-only failure | Vision fix |
|-----|-------------------|-------------------|------------|
| **Shorts player without “Shorts” string** | OEM YouTube layout | ALLOW (study aligned) | BLOCK — vertical player visible |
| **Lecture + shelf, OCR = title only** | a11y tree drops sibling nodes | ALLOW under monk ban | BLOCK/WARN — shelf row visible |
| **IG feed with “#reels” in caption** | Caption text extracted | BLOCK | ALLOW — feed layout, Reels tab not active |
| **Age gate without word “porn”** | WebView generic buttons | ALLOW | BLOCK — modal pattern |
| **“Adult learners” headline** | Keyword trap | BLOCK | ALLOW — news layout, no gate |
| **IMDb mature themes** | “Mature” in metadata | BLOCK | ALLOW — info page, not explicit |
| **shortlisted email** | Substring “short” | WARN/BLOCK | ALLOW — email UI |
| **Blank / loading WebView** | Empty `screenText` | Random guess | WARN — skeleton/spinner |
| **Play Store Mature 17+** | Rating not in a11y | ALLOW on dating app | BLOCK under guardrail |
| **WhatsApp forwarded chain** | “Forwarded” label missing in OCR | WARN | BLOCK — repeated media tiles |
| **PiP lecture while Shorts full screen** | Two surfaces — foreground wrong in tree | Wrong decision | Full-screen foreground wins |

**Bottom line:** Text-only sees **strings**. PhoneCodex needs **layout + modality + foreground activity**. That is the product gap v2 measures.

---

## Eval design: paired modalities

Each vision-critical case should exist in **three rows** (optional ablation):

| Row | screenshotPath | screenText | Purpose |
|-----|----------------|------------|---------|
| A | ✓ full | ✓ clean (v1-like) | Vision ceiling |
| B | ✓ full | ✗ truncated/misleading | **Production-realistic** |
| C | ✗ empty | ✗ truncated | Text-only baseline |

Compare:

- `pc-lab-cheap` + text only (row C)
- `pc-lab-vision` + text only (row C) — expect ~0 lift (proven on v1)
- `pc-lab-vision` + image + text (row B) — **this must win** or vision is rejected

**Runner work (future phase, not this deliverable):**

- Extend `azure_openai.py` to base64-encode `screenshotPath` into multimodal message
- Flag `--vision` or auto when `screenshotPath` present
- Redact API logs — never print image bytes

---

## Fixture production workflow (lab-only)

1. **Synthetic first** — Figma/Android emulator staged states; no user PII
2. **Emulator captures** — Android Studio Pixel device; consistent 1080×2400
3. **Format** — WebP quality 85; max 1080px long edge; ~100–300 KB each
4. **Directory layout:**

```text
evals/fixtures/screenshots/v2/
  yt/
  chrome/
  wa/
  ig/
  ps/
  meta/          # capture notes, no secrets
```

5. **JSONL row** — `screenshotPath`: `evals/fixtures/screenshots/v2/yt/shorts_player_001.webp`
6. **Validator** — extend `validate_dataset.py`: file exists, dimensions, no `.env` in image path
7. **Git** — fixtures in repo if synthetic; real device captures → private blob + hash IDs only

**Do not** scrape real adult sites for fixtures. Stage age-gate **mock** in emulator browser.

---

## How Android should capture screenshots safely (future)

Plan only — **no app implementation in this task.**

### Principles

1. **User consent first** — explicit opt-in for “send screen to advisor” separate from accessibility for OCR
2. **On-device redaction before upload** — crop to app content region; strip status bar notifications when possible
3. **No full-time recording** — single frame on classify trigger, not video stream
4. **Emergency bypass** — never capture/deny on dialer, SOS, incoming call full screen
5. **Local policy short-circuit** — tamper/quota exhausted → decide without cloud image
6. **Retention** — process in memory; upload encrypted; delete after classify response (≤60s TTL)
7. **No banking/password surfaces** — package denylist skips screenshot upload; PolicyEngine WARN only

### Proposed capture pipeline (v1 Android)

```text
Foreground app change (AccessibilityService)
    → PolicyEngine: need cloud classify?
        → No: local rules only
        → Yes:
            → OCR extract screenText (local)
            → ocrConfidence score
            → if ocrConfidence < 0.6 OR ambiguous package (Chrome, WebView, IG, YouTube):
                  captureFrame()  // one PNG, app window bounds only
                  optionalDownscale(1080)
                  stripStatusBarNotifications()  // best-effort
            → send { screenText, screenshotBase64?, promise, counters } to /classify
            → discard frame in memory after response
```

### `captureFrame()` safety rules

| Rule | Implementation sketch |
|------|------------------------|
| **When** | Only on classify trigger; debounce ≥3s same package |
| **What region** | `getRootInActiveWindow()` bounds; exclude IME keyboard |
| **What never capture** | Banking apps, password fields (`View.isPassword`), package denylist |
| **Size** | Max 1080px; WebP/JPEG 0.85 |
| **Storage** | Memory-only buffer; no gallery write |
| **Upload** | TLS to Azure Function; API key from Keystore |
| **User visibility** | Decision Inspector: “Analyzed screen snapshot” toggle in settings |
| **Fallback** | If capture fails → text-only classify + lower confidence → prefer WARN |

### Package tiers (screenshot policy)

| Tier | Packages | Screenshot |
|------|----------|--------------|
| T0 deny | Banking, payment, autofill | Never |
| T1 text-only | Dialer, SMS emergency | Never |
| T2 OCR preferred | WhatsApp, Settings | Only if OCR low confidence |
| T3 vision encouraged | Chrome, YouTube, Instagram, Play Store | If OCR low or WebView |

### Privacy copy (product)

> PhoneCodex sends a **single screenshot** of the app you’re using to interpret your promise — not a recording. Snapshots are deleted after analysis. Banking and password screens are never captured.

---

## Prompt and model plan for v2

| Component | Choice |
|-----------|--------|
| Base prompt | `classifier_v04.txt` + short vision appendix |
| Deployment | `pc-lab-vision` (gpt-4o) for image rows |
| Baseline | `pc-lab-cheap` text-only row C |
| Escalation | strong text if vision confidence low |

**Vision appendix (future `classifier_v04_vision.txt`):**

- Trust image layout over misleading `screenText` when they conflict
- Describe foreground modality: long video / vertical short / feed / DM / age gate / install page
- Never infer password or payment fields from image

---

## Milestones

| Milestone | Deliverable | Cases |
|-----------|-------------|------:|
| M1 | Synthetic fixtures cat 2 + 6 (Shorts, IG) | 20 |
| M2 | Chrome adult + false positive fixtures | 18 |
| M3 | YouTube lecture shelf + Play Store | 22 |
| M4 | WhatsApp + OCR trap cross-cutting | 22 |
| M5 | `v2_visual_cases.jsonl` + validator + vision runner | ~90 |
| M6 | Report: vision lift vs text-only | — |

**Gate to Android:** v2 visual subset ≥5pp lift on vision-critical cluster **and** 0 false allows on cheap+vision pipeline.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Fixture drift (YouTube UI update) | Version tag in `notes`; re-capture quarterly |
| Explicit content in repo | Synthetic gates only; no NSFW pixels |
| Vision overfits emulator theme | 2 OEM skins (Pixel + Samsung) for 20% of cases |
| Cost at scale | Vision only when OCR confidence low — not every frame |
| Label disagreement lecture+shelf BLOCK | Lock labels to v1; document in pairedGroupId |

---

## What this phase does NOT include

- Android `captureFrame()` implementation
- Backend `/classify` multimodal endpoint
- Changes to `app/**` or `backend/**`
- Real user device screenshot collection
- Fine-tuning or new Azure deployments

---

## Immediate next actions (when Ankit approves build)

1. Create `evals/fixtures/screenshots/v2/` directory tree
2. Stage 20 emulator screenshots (IG Reels vs feed, YouTube Shorts vs lecture)
3. Draft first 20 rows of `v2_visual_cases.jsonl` with truncated `screenText`
4. Extend Azure adapter for multimodal input
5. Run ablation A/B/C rows on `pc-lab-vision`

---

*Related: `evals/reports/v1_model_comparison_summary.md`, `evals/reports/classifier_v04_recommendation.md`, `evals/datasets/schema.json`, `docs/cto-strategy-phonecodex-ai.md`*

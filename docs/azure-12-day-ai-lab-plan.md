# Strlix AI Lab — 12-Day Azure Credit Acceleration Plan

**Owner:** Ankit Yadav (founder) + AI Lab  
**Window:** 2026-09-07 → 2026-09-18 (align to remaining Azure credit runway)  
**Account:** `ay186mnc-1561-resource` / westus3  
**Deployments:** `pc-lab-cheap` (gpt-4.1-mini), `pc-lab-strong` (gpt-4.1), `pc-lab-vision` (gpt-4o)  
**Law:** AI suggests. PolicyEngine enforces. Compiler output never auto-wires into phone law.

**Goal:** Convert Azure credits into **long-lived technical assets** — tagged eval corpus, failure taxonomy, prompt/version evidence, model ladder proofs — not idle VMs or vanity demos.

---

## Spend envelope (12 days)

| Line | Target | Hard stop | What you get |
|------|--------|-----------|--------------|
| Promise Compiler evals + prompt iteration | $250–450 | $500 | CSVs, failure clusters, prompt deltas |
| Classifier robustness / multilingual / adult precision | $150–300 | $350 | FA/FB matrices, false-adult proofs |
| Candidate generation (messy NL → review JSONL) | $80–150 | $180 | 2k–5k **candidates**; gold only after human review |
| Model ladder (cheap vs strong; vision only when OCR fails) | $60–120 | $150 | Comparison config + winner tables |
| Buffer / re-runs | $40–80 | $100 | Flaky retry, schema fixes |
| **Total** | **$580–1,100** | **$1,280** | Assets in `evals/` |

**Rule:** Every dollar → JSONL row, CSV report, or markdown decision. No AKS, GPU, PTU, always-on Functions “just because,” no fine-tune until corpus ≥2k **reviewed** gold cases.

---

## Asset targets (end of Day 12)

| Asset | Target | Moat reason |
|-------|--------|-------------|
| Reviewed promise gold set | 800–1,500 | Distinctions competitors cannot scrape |
| Generated candidates (pending review) | 2,000–5,000 | Scale with human filter, not junk clones |
| Classifier edge + multilingual | +300–600 cases | Phone reality: Hinglish, typos, OCR noise |
| Failure taxonomy | Stable codes | Know *why* models fail |
| Model comparison config | Locked | Cheap default; strong/vision gated |
| Reports | Phase docs | Spend discipline for next credit window |

---

## Critical invariants (never burn credits to violate these)

1. **Five clocks stay separate:** session duration ≠ `max_item_minutes` / `min_item_minutes` ≠ entertainment/usage quota ≠ lock duration. (See `promise_compiler_v05` + `v4_temporal_clocks`.)
2. **Compiler output cannot enforce** without confirm-before-start.
3. **Unclear promise → follow-up** (`followUpQuestionRequired: true`).
4. **Adult/porn:** zero false allows; normal entertainment must not be labeled porn.
5. **Same app, opposite decisions** by promise (YouTube lecture vs Shorts; IG DM vs Reels; Chrome study vs doomscroll).

---

## Phase map

| Phase | Days | Focus | Est. spend |
|-------|------|-------|------------|
| **1 — Pipeline + seed** | 1–2 | Schema tags, generator, failure cluster, seed eval | $15–40 |
| **2 — Distinction corpus** | 3–5 | Expand gold by cluster; temporal + follow-up + adult | $120–220 |
| **3 — Classifier hardness** | 6–8 | Multilingual, app-surface, false-adult, OCR noise | $150–280 |
| **4 — Model ladder** | 9–10 | Cheap vs strong on hard subsets; vision only if needed | $80–160 |
| **5 — Freeze + next-spend memo** | 11–12 | Ship reports; freeze prompts; list DO/DON’T spend | $40–80 |

---

## Day-by-day deliverables

### Day 1 — Pipeline skeleton (Phase 1)

| Item | Detail |
|------|--------|
| **Deliverables** | Dimension schema; `generate_messy_promise_candidates.py`; `analyze_promise_failures.py`; `model_comparison.json`; seed JSONL (~30–50) |
| **Compute** | 0–50 gen calls on `pc-lab-cheap`; optional baseline eval (free) |
| **Success** | Seed loads; tags present; failure analyzer runs on any promise CSV |
| **Do NOT** | Full 200+ Azure matrix; touch Android |

**Expected usage:** ~$1–8

---

### Day 2 — Prove end-to-end (Phase 1 close)

| Item | Detail |
|------|--------|
| **Deliverables** | Seed Azure eval (`--limit` full seed); Phase 1 report; temporal clocks note if missing |
| **Compute** | ~30–50 compiler calls × `pc-lab-cheap` + optional strong on 10 hard cases |
| **Success** | CSV + failure clusters; documented spend verdict |
| **Do NOT** | Generate 1k unreviewed cases |

**Expected usage:** $5–25

---

### Day 3 — Gold expansion: follow-up + ambiguity

| Item | Detail |
|------|--------|
| **Deliverables** | +80–120 hand/templated gold cases: duration ambiguous, session_and_content, vague entertainment |
| **Compute** | Eval cheap on new slice only |
| **Success** | Clarification recall tracked separately from exact match |
| **Metric gates** | Follow-up recall ≥85% on ambiguity subset; no rise in adult FA |

**Expected usage:** $15–35

---

### Day 4 — Gold expansion: app surfaces

| Item | Detail |
|------|--------|
| **Deliverables** | +100–150 cases: YouTube (lecture/Shorts/shelf), Instagram (DM/Reels/Stories), Chrome (tabs/search/YouTube-in-Chrome) |
| **Compute** | Compiler eval + classifier re-check on related screens if tagged |
| **Success** | `app_surface` tag coverage balanced; same package opposite labels exist |
| **Do NOT** | Vision spend yet |

**Expected usage:** $25–50

---

### Day 5 — Gold expansion: five clocks + safety

| Item | Detail |
|------|--------|
| **Deliverables** | Grow temporal set to ~150–200; adult true-positive + false-adult negatives; tamper/emergency inert |
| **Compute** | `pc-lab-cheap` full temporal+safety slice; spot-check strong on violations |
| **Success** | Temporal clock OK ≥95% on v05; **0 adult false allows** on safety slice |
| **Reuse** | `v4_temporal_clocks` + v05 prompt — do not regress clocks |

**Expected usage:** $30–60

---

### Day 6 — Candidate generation wave A (2k path)

| Item | Detail |
|------|--------|
| **Deliverables** | Generator run: 400–600 candidates with provenance; review queue markdown |
| **Compute** | Generation on cheap; **no** auto-gold |
| **Success** | Deduped candidates; diversity by language / typo / promise_type |
| **Human gate** | Accept ≤30% of candidates into gold without rewrite |

**Expected usage:** $20–40 (generation) + $0 review labor (you)

---

### Day 7 — Classifier multilingual + messy OCR text

| Item | Detail |
|------|--------|
| **Deliverables** | +100–200 classifier cases: Hinglish goals, typo screenText, mixed scripts |
| **Compute** | `classifier_v04` on cheap; strong only on FA/FB deltas |
| **Success** | Hold **0 false allows** on adult+absolute-ban clusters; log FA/FB separately |
| **Do NOT** | Replace v04 mid-run without version bump |

**Expected usage:** $40–80

---

### Day 8 — Adult precision + entertainment non-porn

| Item | Detail |
|------|--------|
| **Deliverables** | Dedicated `safety_risk` slices: porn, softcore ambiguity, “adult learners”, romance movies, IG swimsuit feed |
| **Compute** | Classifier + compiler guardrail fields |
| **Success** | Adult FA = 0; false-adult overblock rate measured (not ignored) |
| **Report** | Precision/recall style table for `no_adult_content` |

**Expected usage:** $40–90

---

### Day 9 — Model ladder: cheap vs strong

| Item | Detail |
|------|--------|
| **Deliverables** | Run `evals/configs/model_comparison.json` hard subsets only |
| **Compute** | Full hard subset on cheap + strong; **not** full corpus on strong |
| **Success** | Decision: when escalate to strong (parse fail? safety miss? clock confusion?) |
| **Do NOT** | Default production path to strong without cost math |

**Expected usage:** $40–90

---

### Day 10 — Vision only if OCR-failure evidence exists

| Item | Detail |
|------|--------|
| **Deliverables** | If Day 7–8 OCR ambiguity ≥N cases with screenshot fixtures → vision matrix; else skip and reallocate |
| **Compute** | `pc-lab-vision` on ≤50–80 cases |
| **Success** | Vision beats text on **those** cases by ≥X points, or kill vision for this window |
| **Default** | Prefer reallocating to gold review + compiler follow-ups |

**Expected usage:** $0–70 (conditional)

---

### Day 11 — Freeze prompts + corpus inventory

| Item | Detail |
|------|--------|
| **Deliverables** | Inventory markdown: gold counts by dimension; frozen prompt pins (`v05` clocks, `v04` classifier); open bugs |
| **Compute** | One regression pass cheap on frozen pins |
| **Success** | Reproducible command list; no silent prompt drift |

**Expected usage:** $20–40

---

### Day 12 — Spend memo + next Azure-heavy batch

| Item | Detail |
|------|--------|
| **Deliverables** | Final memo: worth / not worth; next 500–1k gold acceptance plan |
| **Compute** | Optional re-run of worst cluster only |
| **Success** | Clear NO-list (fine-tune, PTU, idle infra, full-corpus strong) |

**Expected usage:** $10–30

---

## Dataset expansion strategy (2k–5k high quality)

### Philosophy

Junk at scale is anti-moat. Competitors can generate “block youtube 1 hour” forever. Moat = **labeled distinctions**:

| Distinction family | Example | Why it matters |
|--------------------|---------|----------------|
| Time-role | “videos longer than 20 min” vs “study 20 min” | Wrong clock → wrong phone behavior |
| App-surface | IG DM allowed / Reels blocked | Promise-relative control |
| Follow-up | “lock me for a bit” | Must ask, not invent duration |
| Adult precision | porn BLOCK vs “adult education” ALLOW | Trust + safety |
| Multilingual | Hinglish / typos | Real ICP (India students) |
| Guardrail vs session | “no porn 1 year” vs “focus 2h” | Life Rules vs Worlds |

### Funnel

```text
templates + real phone failures
  → Azure candidate generation (provenance, reviewStatus=pending)
  → human accept / rewrite / reject
  → gold JSONL (reviewStatus=accepted)
  → eval + failure clustering
  → prompt/schema fix
  → regenerate ONLY failing clusters
```

### Volume plan

| Bucket | Candidates | Accepted gold (est.) |
|--------|------------|----------------------|
| Temporal / five clocks | 400 | 150–250 |
| App surface (YT/IG/Chrome) | 600 | 200–350 |
| Follow-up / ambiguity | 500 | 150–250 |
| Adult / false-adult | 400 | 120–200 |
| Multilingual / typo | 500 | 150–250 |
| Quota / lock / tamper / combo | 600 | 200–300 |
| **Total** | **~3,000** | **~970–1,600** |

Push candidates toward 5k only after accept-rate and cluster coverage are healthy. Prefer **rewrite** over blind accept.

### Quality bar for “accepted”

- Expected policy matches the **text**, not a cluster blanket.
- Tags filled: language, typo_level, promise_type, app_surface, time_role, safety_risk, expected_followup, expected_guardrails.
- Safety cases: adult FA impossible if model matches gold.
- No duplicate paraphrases that share the same expected policy without a new distinction.

---

## Model comparison policy

Config file: `evals/configs/model_comparison.json`

| Deployment | Role | When to use |
|------------|------|-------------|
| `pc-lab-cheap` | Default lab + future advisor | All primary evals |
| `pc-lab-strong` | Escalation / disagreement probe | Safety miss, clock confusion, parse fail, hard subset |
| `pc-lab-vision` | OCR failure only | Screenshot fixtures; never default text path |

Never run full 2k corpus on strong/vision in this window.

---

## What Azure SHOULD be used for

1. Promise Compiler prompt/version evidence (cheap primary).
2. Candidate messy-language generation with human review.
3. Classifier FA/FB matrices on hard + multilingual slices.
4. Cheap vs strong **delta** on hard subsets.
5. Optional vision **only** with OCR-failure proof.

## What Azure should NOT be spent on

1. Idle App Service / AKS / GPU / PTU / fine-tune before reviewed gold ≥2k.
2. Full-corpus strong/vision sweeps.
3. Pretty demos without CSV.
4. Auto-wiring compiler into PolicyEngine.
5. Regenerating near-duplicates of already-solved clusters (e.g. pure session-duration after v05 clocks are green).
6. New Azure product surface area (Search, Cosmos, etc.) without a logged product need.

---

## Phase 1 exit criteria (Days 1–2)

- [x] 12-day plan documented (this file)
- [x] Dimension tags schema + seed cases
- [x] Generator script with provenance fields
- [x] Failure clustering for promise reports
- [x] Model comparison config
- [x] Seed batch eval run + Phase 1 report with spend verdict

**Status after Phase 1:** research pipeline proven — **not** production-ready.  
See `evals/reports/phase1_ai_lab_azure_acceleration.md`.

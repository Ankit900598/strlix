# PhoneCodex Model Comparison Plan

**Date:** 2026-09-05  
**Prompt:** `evals/prompts/classifier_v03.txt` (current best: **88%** on `v0_challenge`, **0 false allows**, **0 false blocks**)  
**Azure account:** `ay186mnc-1561-resource` (westus3)  
**Credits expire:** 22 Sep 2026

---

## Purpose

Answer one question with data: **Does a better Azure model improve PhoneCodex decision quality beyond prompt engineering?**

PhoneCodex classifies the same screen as ALLOW / WARN / BLOCK / LOCK depending on the user's promise. Model comparison must optimize for:

1. **Zero false allows** (hard safety gate — user bypasses commitment)
2. **Zero false blocks** (hard UX gate — blocks legitimate use)
3. **Highest accuracy** on ambiguous boundary cases
4. **Acceptable latency** for on-device advisor path (target p95 < 3s later)
5. **Cost per 1k decisions** for production economics

---

## Live deployments (3 tiers — ready now)

| Tier | Deployment | Model | Version | SKU | TPM | Use case |
|------|------------|-------|---------|-----|-----|----------|
| **Cheap baseline** | `pc-lab-cheap` | gpt-4.1-mini | 2025-04-14 | Standard | 100k | High-volume sweeps, smoke, prompt A/B |
| **Strong text** | `pc-lab-strong` | gpt-4.1 | 2025-04-14 | Standard | 100k | Reasoning / ambiguous ALLOW-WARN-BLOCK |
| **Vision-capable** | `pc-lab-vision` | gpt-4o | 2024-11-20 | Standard | 100k | Future screenshot understanding; text-only eval today |

**Premium tier (blocked — quota 0):** `gpt-5.4` (`pc-lab-reasoning`), `claude-opus-5` (`pc-lab-claude-opus`). Request quota before adding to matrix. See `docs/azure-research-plan.md` Appendix B.

**Prerequisites:** Repo-root `.env` with `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION=2024-08-01-preview`. Use **`py -3.12`** on Windows (MSYS Python fails SSL against Azure).

---

## Comparison matrix

### Phase 1 — Core sweep (run first)

| Run ID | Deployment | Dataset | Cases | Prompt | Primary metrics |
|--------|------------|---------|-------|--------|-----------------|
| M1 | `pc-lab-cheap` | `v0_challenge.jsonl` | 50 | v03 | accuracy, FA, FB |
| M2 | `pc-lab-strong` | `v0_challenge.jsonl` | 50 | v03 | accuracy, FA, FB |
| M3 | `pc-lab-vision` | `v0_challenge.jsonl` | 50 | v03 | accuracy, FA, FB |
| M4 | `pc-lab-cheap` | `v0_seed.jsonl` | 100 | v03 | safety regression |
| M5 | `pc-lab-strong` | `v0_seed.jsonl` | 100 | v03 | safety regression |
| M6 | `pc-lab-vision` | `v0_seed.jsonl` | 100 | v03 | safety regression |

**Total API calls:** 450 (6 runs × 75 cases average... actually 50+50+50+100+100+100 = 450)

### Phase 2 — Consistency (top 2 configs from Phase 1)

Re-run the **two best** deployment configs on `v0_challenge.jsonl` **3 times each** (same prompt, same dataset). LLM variance is real; we need mean ± stddev.

| Run ID | Deployment | Pass | Dataset |
|--------|------------|------|---------|
| C1–C3 | winner #1 | 1, 2, 3 | v0_challenge.jsonl |
| C4–C6 | winner #2 | 1, 2, 3 | v0_challenge.jsonl |

### Phase 3 — Hard-case focus (after Phase 1)

Extract cases where **any** model failed from Phase 1 CSVs. Build `evals/datasets/v0_hard_subset.jsonl` (manual or script). Re-run all 3 deployments on that subset only.

**v03 known hard cases (6 failures @ 88% on cheap):**

| Case ID | Expected | v03 got | Severity |
|---------|----------|---------|----------|
| `ch_wa_meme_monk_block_001` | BLOCK | WARN | **High** — under-block on monk meme spam |
| `ch_ig_dm_project_allow_001` | WARN | ALLOW | Medium — social friction miss |
| `ch_set_a11y_list_warn_001` | WARN | ALLOW | Medium — neutral settings during LOCKED |
| `ch_chrome_false_adult_mature_discussion_001` | ALLOW | WARN | Low — over-warn |
| `ch_chrome_shortlisted_trap_allow_001` | ALLOW | WARN | Low — over-warn |
| `ch_chrome_compsci_forum_allow_001` | ALLOW | WARN | Low — over-warn |

Phase 3 success = **fix `ch_wa_meme_monk_block_001` on all models** OR prove stronger model catches it without prompt change.

---

## Exact commands (Windows PowerShell)

From repo root `C:\Users\HP\strlix`:

```powershell
$Prompt = "evals/prompts/classifier_v03.txt"

# --- Phase 1: v0_challenge (50 cases) ---
$env:AZURE_OPENAI_DEPLOYMENT = "pc-lab-cheap"
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt $Prompt

$env:AZURE_OPENAI_DEPLOYMENT = "pc-lab-strong"
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt $Prompt

$env:AZURE_OPENAI_DEPLOYMENT = "pc-lab-vision"
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt $Prompt

# --- Phase 1: v0_seed safety regression (100 cases) ---
$env:AZURE_OPENAI_DEPLOYMENT = "pc-lab-cheap"
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter azure_openai --prompt $Prompt

$env:AZURE_OPENAI_DEPLOYMENT = "pc-lab-strong"
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter azure_openai --prompt $Prompt

$env:AZURE_OPENAI_DEPLOYMENT = "pc-lab-vision"
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter azure_openai --prompt $Prompt
```

Each run writes CSV to `evals/reports/azure_openai_YYYYMMDD_HHMMSS.csv`.

### Phase 2 consistency (example — replace DEPLOYMENT with winner)

```powershell
$env:AZURE_OPENAI_DEPLOYMENT = "pc-lab-strong"
1..3 | ForEach-Object {
  py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt $Prompt
}
```

---

## Metrics definitions

### Primary (must report for every run)

| Metric | Formula | Hard gate |
|--------|---------|-----------|
| **Accuracy** | correct / total | — |
| **False allows (FA)** | expected ∈ {BLOCK, LOCK} AND predicted = ALLOW | **Must be 0** |
| **False blocks (FB)** | expected = ALLOW AND predicted = BLOCK | **Must be 0** |
| **Dangerous miss rate** | FA + (expected BLOCK → predicted WARN) | Track separately |

### Secondary (manual from CSV for now)

| Metric | How to measure |
|--------|----------------|
| **WARN precision** | Of predicted WARN, how many expected WARN |
| **Boundary case accuracy** | Filter cases tagged `ambiguous`, `neutral_navigation`, `social_feed` in notes |
| **Category match** | `expectedReasonCategory` vs `predictedReasonCategory` exact match rate |
| **Confidence calibration** | Failures should have lower confidence than passes (scatter plot later) |

### Severity weights (for ranking configs when accuracy ties)

| Error type | Weight | Why |
|------------|--------|-----|
| False allow | **10×** | User breaks commitment undetected |
| BLOCK → WARN (monk/adult/short-form) | **5×** | Under-enforcement |
| ALLOW → WARN | 1× | Annoying but safe |
| WARN → ALLOW (social friction) | 2× | Missed nudge |
| Category mismatch only | 0.5× | Decision correct, taxonomy wrong |

**Winner rule:** Any config with FA > 0 is **disqualified**. Among remainder, highest accuracy; tie-break by lowest weighted severity on failures.

---

## Latency tracking (add next — not in runner yet)

For each run, record wall-clock manually or extend runner:

```
latency_ms = (run_end - run_start) / case_count
```

Target columns to add to CSV later: `latencyMs`, `promptTokens`, `completionTokens`.

**Rough expected ranges (text-only, 50 cases):**

| Deployment | Expected total run time | Expected p50/call |
|------------|-------------------------|-------------------|
| pc-lab-cheap | ~90–120s | ~2s |
| pc-lab-strong | ~100–140s | ~2.5s |
| pc-lab-vision | ~100–140s | ~2.5s |

Log start/end timestamps in a sidecar file `evals/reports/run_log.jsonl` until runner supports it:

```json
{"runId":"M2","deployment":"pc-lab-strong","dataset":"v0_challenge","startedAt":"...","endedAt":"...","caseCount":50}
```

---

## Cost tracking (estimate until token logging added)

Azure pay-per-token (Standard SKU, westus3 — verify portal pricing):

| Model | Input $/1M | Output $/1M | Est. $/run (50 cases) | Est. $/1k decisions |
|-------|------------|-------------|----------------------|---------------------|
| gpt-4.1-mini | ~$0.40 | ~$1.60 | ~$0.02–0.05 | ~$0.40–1.00 |
| gpt-4.1 | ~$2.00 | ~$8.00 | ~$0.10–0.25 | ~$2.00–5.00 |
| gpt-4o | ~$2.50 | ~$10.00 | ~$0.10–0.30 | ~$2.50–6.00 |

**Phase 1 total estimate:** ~$0.50–1.50 for all 6 runs.  
**Full comparison + 3× consistency:** ~$5–15. Well within credit budget.

After each run, note actual spend in Azure Portal → Cost Management → filter `phonecodex-dev`.

---

## Results template

Fill after Phase 1:

| Run | Deployment | Dataset | Accuracy | FA | FB | Report CSV |
|-----|------------|---------|----------|----|----|------------|
| M1 | pc-lab-cheap | v0_challenge | 88% (44/50) | 0 | 0 | `azure_openai_20260905_112326.csv` |
| M2 | pc-lab-strong | v0_challenge | _TBD_ | | | |
| M3 | pc-lab-vision | v0_challenge | _TBD_ | | | |
| M4 | pc-lab-cheap | v0_seed | _TBD_ | | | |
| M5 | pc-lab-strong | v0_seed | _TBD_ | | | |
| M6 | pc-lab-vision | v0_seed | _TBD_ | | | |

### Decision rubric (after all runs)

| Outcome | Action |
|---------|--------|
| All 3 models ≈ same accuracy (±2%) | **Model tier doesn't matter yet** — invest in prompt v04 + dataset, keep cheap for prod |
| Strong beats cheap by ≥4% with 0 FA/FB | Use **gpt-4.1** for advisor; cheap for smoke only |
| Vision beats strong on text-only | Unexpected — investigate JSON leakage; still use vision for screenshot eval |
| Any model FA > 0 | **Disqualified** — do not ship regardless of accuracy |
| Premium quota approved + beats 4.1 by ≥3% | Add M7/M8 runs; consider prod advisor upgrade |

---

## Future: vision-based classification

Text-only eval (`screenText` field) **under-tests** `pc-lab-vision`. Vision path:

### Dataset design (`v0_vision_v1.jsonl` — to build)

Each case adds:

```json
{
  "id": "vis_yt_shorts_player_001",
  "screenshotPath": "evals/fixtures/screenshots/yt_shorts_player.png",
  "screenText": "",
  "ocrFallback": "optional partial OCR",
  "...": "same promise fields as v0_challenge"
}
```

**100 cases minimum**, covering:

| Category | Count | Why vision helps |
|----------|-------|------------------|
| Short-form UI (no OCR keywords) | 20 | Detect player chrome vs lecture |
| Incomplete/loading screens | 15 | Blank ≠ safe |
| Settings tamper vs browse | 10 | Button state visible |
| Adult gates / age badges | 10 | Visual 18+ markers |
| Home launcher icon layout | 15 | Distraction affordance without text |
| Meme/image-heavy content | 15 | OCR misses humor |
| Guardrail traps (sidebar ads) | 15 | Foreground vs peripheral |

### Vision eval modes (compare later)

| Mode | Input to model | Adapter change |
|------|----------------|----------------|
| **Text-only** | `screenText` JSON field | Current — baseline |
| **OCR-only** | On-device OCR → text | Current — simulates prod v1 |
| **Screenshot** | PNG base64 in multimodal message | Extend `azure_openai.py` with `image_url` |
| **Hybrid** | OCR + screenshot when confidence low | Prod target architecture |

### Vision adapter sketch (do not implement until fixtures exist)

```python
# evals/runner/adapters/azure_openai_vision.py (future)
messages = [
  {"role": "system", "content": prompt},
  {"role": "user", "content": [
    {"type": "text", "text": json_dumps(case_payload)},
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
  ]}
]
```

Run on `pc-lab-vision` only. Compare accuracy vs text-only on same cases.

---

## Premium tier commands (when quota approved)

```powershell
# After deploying pc-lab-reasoning (gpt-5.4 GlobalStandard) or pc-lab-claude-opus
$env:AZURE_OPENAI_DEPLOYMENT = "pc-lab-reasoning"
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt $Prompt

# Claude requires new adapter — see docs/azure-research-plan.md
```

Deploy payloads: `evals/reports/_deploy_gpt54_reasoning.json`, `evals/reports/_deploy_claude_opus.json`

---

## What NOT to do

- Do not deploy Sora / video generation models
- Do not create provisioned throughput (PTU) deployments
- Do not delete existing `pc-lab-*` deployments without approval
- Do not commit `.env` or paste API keys into reports
- Do not tune prompt between M1–M6 runs (invalidates comparison)

---

*Run the matrix. Fill the table. Pick the model with numbers, not vibes.*

# Block Experience — Dataset Generation Notes

**Date:** 2026-09-05  
**Builder:** `evals/datasets/_build_v1_block_experience.py`  
**Output:** `evals/datasets/v1_block_experience.jsonl` — **332 cases**  
**Method:** Deterministic templates (not Azure-generated gold)

---

## Why not LLM-generated gold?

Promise Compiler taught us: LLM gold + LLM predict = circular congratulation.  
Overlay gold must encode **product law** from `trustworthy_block_experience.md`:

- which actions exist  
- which are forbidden under STRICT/LOCKED  
- when cooldown/emergency/promise flags fire  

Azure is used for **prediction eval**, not for labeling ground truth in v1.

---

## Construction method

1. Seed promise lists per domain (study, adult, shorts, WA, IG, rail, Chrome, long-term, monk).  
2. Cross with strictness × decision × screen summaries.  
3. `overlay()` helper stamps schema-valid expectedOverlay.  
4. `forbidden_for()` / `tone_for()` / `secondary_continue_ok()` encode strictness law.  
5. Synthetic fill loop pads to ≥300 if combinatorial coverage is short (tagged `synthetic_fill`).  
6. Soft/smart pads add WARN diversity without inventing new reason categories carelessly.

IDs: `bx_<prefix>_<nnn>` unique; clusters named for failure analysis.

---

## Cluster counts (post-build)

See builder stdout / design doc table. Highlights:

- Heavy on **study_drift**, **chrome_***, **tamper**, **social surface** splits — matches real overlay pain.  
- **playlist_rail_redirect** is small but intentional (Guided Study Rail is future).  
- **emergency_exception** cases are rare on purpose (usually no overlay); when present, primary = EMERGENCY_EXIT.

---

## Known gold limitations (document, don’t hide)

1. **Title/message are templates** — slight paraphrase should still safety-pass; exactMatch is not sacred.  
2. **Baseline exactMatch ~60%** — baseline picks safe action families; gold sometimes prefers OPEN_PLAYLIST vs EXIT_SURFACE. Safety is the shipping metric.  
3. **whatsapp_useful_warn** forces WARN on a useful DM surface — product choice for “stay aligned” nudge; some founders may prefer ALLOW+no overlay (flagged in notes).  
4. **Synthetic fill** cases are thinner narratively — fine for action/flag law, weak for copy nuance.  
5. No Hinglish promises in v1 — add in v2 if product ships Hinglish promise-first UI.  
6. Adult screens described in text without graphic detail — reduces Azure content_filter risk while still testing life-rule tone.

---

## Azure usage plan

| Spend | Purpose |
|-------|---------|
| pc-lab-cheap × full 332 | Primary shipping signal for v01 prompt |
| pc-lab-strong × full or sample | Compare safetyMatch / violation types |
| Not used | Random infra, resource creation, vision |

Credits expire **22 Sep 2026** — prefer eval runs that change prompts/Android templates over idle spend.

---

## Regeneration

```text
py -3.12 evals/datasets/_build_v1_block_experience.py
py -3.12 evals/runner/run_block_experience_eval.py --adapter baseline
```

Do **not** hand-edit the jsonl for bulk fixes — change the builder and rebuild (same lesson as Promise Compiler messy clusters).

---

## Eval command reference

```text
py -3.12 evals/runner/run_block_experience_eval.py --adapter azure_openai --deployment pc-lab-cheap --prompt evals/prompts/block_experience_v01.txt

py -3.12 evals/runner/run_block_experience_eval.py --adapter azure_openai --deployment pc-lab-strong --prompt evals/prompts/block_experience_v01.txt
```

Optional: `--limit N` for smoke tests.

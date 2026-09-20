# Promise Compiler — Temporal Clocks (brief)

**Dataset:** `evals/datasets/v4_temporal_clocks.jsonl` (87 cases)  
**Prompt pin:** `promise_compiler_v05.txt` (FIVE CLOCKS)  
**Deployment:** `pc-lab-cheap`

## Headline

| Run | Exact | Safety | Violations | Temporal clock OK |
|-----|-------|--------|------------|-------------------|
| baseline | 17.2% | 33.3% | 6 | 35.6% |
| v04 cheap | 33.3% | 78.2% | 1 | **65.5%** |
| v05 cheap | 44.8% | 59.8% | **0** | **100%** |

v05 trades some safetyMatch vs v04 on this set but eliminates clock confusion / media-length prose-only failures. Prefer v05 when scoring temporal roles; re-check safety on `v3_commitment_messy_global` before any product talk.

## Failure codes (v05)

From `promise_compiler_temporal_clocks_failures.md`: remaining issues are mostly `field_mismatch_only` / `guardrail_miss` / occasional `followup_overask` — **not** clock-role swaps.

## Invariant

`session duration` ≠ `max_item_minutes` / `min_item_minutes` ≠ `entertainment_minutes` quota ≠ `lock duration` ≠ permanent guardrail duration.

## Next

Expand temporal gold to 150–200 **distinct** cases; do not regenerate solved pure-session paraphrases.

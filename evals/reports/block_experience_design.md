# Block Experience Lab — Design

**Date:** 2026-09-05  
**Prompt:** `evals/prompts/block_experience_v01.txt`  
**Schema:** `evals/schemas/block_experience_schema.json`  
**Dataset:** `evals/datasets/v1_block_experience.jsonl` (332 cases)  
**Authority doc:** `evals/reports/trustworthy_block_experience.md`

---

## 1. Question this lab answers

> For a given **promise + screen + decision + strictness**, what should the overlay **say** and which **actions** are allowed?

This is not classifier accuracy. PolicyEngine already chose WARN/BLOCK/LOCK/REDIRECT/COOLING_OFF. The Block Experience Writer produces the **contract UX** layer.

```text
promise × screen × decision × strictness
        → title, message, actions, flags
```

---

## 2. Why a separate lab (not fold into classifier)

| Classifier | Block Experience |
|------------|------------------|
| ALLOW/WARN/BLOCK/LOCK | Copy + CTAs + forbidden CTAs |
| Safety = false allows | Safety = easy bypass, shame, missing emergency, missing promise citation |
| Wrong answer = wrong severity | Wrong answer = correct severity, toxic/trust-breaking UX |

Shipping a correct BLOCK with “Stay strong, ignore anyway?” is still a product failure.

---

## 3. Schema design choices

**Structured action IDs** (not free-text buttons): so Android maps CTAs to real handlers and evals don’t fail on synonym buttons (“Leave Shorts” vs “Exit Shorts”).

**forbiddenActions as explicit list:** models must *name* what they refuse to offer — forces STRICT/LOCKED discipline.

**Flags:** `showPromise`, `showCooldown`, `allowEmergencyExit` — boolean safety gates independent of prose quality.

**Tone enum:** soft_nudge / smart_cost / strict_guard / locked_vault / contract_life_rule / tamper_cold — maps to visual weight later; not for morality volume.

**COOLING_OFF** is a first-class `decision` (not only a flag) so override-wait UX isn’t confused with LOCK.

---

## 4. Evaluator philosophy (safety-first)

| Metric | Meaning |
|--------|---------|
| **safetyMatch** | Hard gates: no easy bypass under STRICT/LOCKED; LOCK primary = WAIT_LOCK; emergency on; promise reflected; no shame phrases; cooldown flag when required |
| **exactMatch** | Structural fields (actions/flags/tone family) + copy quality — **not** verbatim title strings |
| **safetyViolations** | Count of hard-gate failures (shipping bar) |

Copy is scored for **shame ban-list** + **promise reflection** (token overlap / “promise|guardrail|rail|life rule”), not BLEU against gold titles. Gold titles are templates for Android defaults; models may paraphrase.

**Superset forbiddenActions:** predicted may ban more actions than gold; must include all gold-required bans.

---

## 5. Scenario coverage (332 cases)

| Cluster | n | Intent |
|---------|---|--------|
| study_drift | 40 | Lecture vs entertainment path |
| chrome_drift / chrome_adult | 45 | Research vs movie/meme/porn |
| tamper_attempt | 25 | Settings force-stop / uninstall |
| adult_guardrail | 20 | Life-rule framing |
| whatsapp_* | 30 | Useful vs distracting WA |
| instagram_* | 30 | DM vs Reels |
| shorts / reels / quota | 30 | Temptation + quota |
| playlist_rail (+ redirect) | 20 | Guided Study Rail preview |
| lock_state / escalation | 19 | Strike → LOCK |
| cooling_off | 10 | Override friction |
| long_term / monk / emergency / soft+smart pads | rest | Tone + edge diversity |

---

## 6. Prompt v01 load-bearing rules

1. Decision → primary action recipes (LOCK→WAIT_LOCK, COOLING→cooldown+WAIT, etc.)  
2. STRICT/LOCKED never CONTINUE_WITH_STRIKE as primary; never IGNORE/DISABLE  
3. SOFT/SMART may offer CONTINUE_WITH_STRIKE as **secondary** on WARN  
4. Surface honesty: don’t ban whole Instagram if only Reels blocked  
5. Ban motivational / parental / “AI thinks” language  
6. Always `showPromise=true` when a promise exists; `allowEmergencyExit=true` almost always  

---

## 7. Android consumption path (later — not this track)

```text
PolicyDecision + session.promiseText + reasonCategory + strictness
  → BlockExperienceWriter (on-device template OR cloud v01)
  → OverlayViewModel(actionIds)
  → handlers: EXIT_SURFACE, WAIT_LOCK, EMERGENCY_EXIT, ...
```

v0 Android can ship **template table** keyed by `(reasonCategory × decision × strictness)` using dataset gold as defaults; cloud writer is for iteration + edge paraphrase.

---

## 8. Success bars

| Gate | Target | pc-lab-cheap v01 | pc-lab-strong v01 |
|------|--------|------------------|-------------------|
| parseFailures | 0 | **0** | **0** |
| safetyMatchRate | ≥ 85% | **100%** (332/332) | **100%** (332/332) |
| safetyViolations | ≈ 0 on hard paths | **0** | **0** |
| contentFilterBlocks | low | **0** | **0** |
| exactMatchRate | secondary | 25.6% | 20.5% |

Reports:

- `block_experience_azure_openai_pc-lab-cheap_block_experience_v01_v1_block_experience_20260905_185737.csv`
- `block_experience_azure_openai_pc-lab-strong_block_experience_v01_v1_block_experience_20260905_184242.csv`
- Baseline safety floor: `block_experience_baseline_v1_block_experience_20260905_180938.csv` (100% safety)

**Read of numbers:** Safety gates are shipping-grade for a cloud writer. exactMatch lags on `primaryAction` / `secondaryAction` / `tone` family choices (EXIT vs RETURN_SAFE, etc.) — Android should prefer **template defaults from gold** for action IDs and use the model for title/message paraphrase only, *or* tighten v02 with few-shot action recipes per reasonCategory.

First cheap run (before forbidding-list emphasis in prompt) had forbiddenActions match **2%** and exact **0.3%** with still **99.7%** safety — proof that safety metric is the right shipping bar and exact string/list match is not.

---

## 9. Relation to Promise Compiler & Guided Study Rail

- Compiler outputs scopes (`calculus_only`, playlist ids) → become `OPEN_PLAYLIST` / REDIRECT destinations.  
- Until compiler is wired, `userPromise` string is the citation source.  
- Rail cases in this dataset are **forward-compatible fixtures** for REDIRECT UX.

---

## 10. What we will not do in this lab

- Generate gold with the same model we eval (circular).  
- Score warm tone as a virtue.  
- Allow “Ignore anyway” under STRICT to inflate “helpfulness.”  
- Touch Android/backend in this track.

---

## 11. Recommendation for Android overlay work

1. Ship **deterministic templates** keyed by `(reasonCategory × decision × strictness)` using dataset gold action IDs.  
2. Optionally call Block Experience Writer for title/message only; **clamp** actions through a policy allow-list (same as evaluator hard gates).  
3. Never trust model `forbiddenActions` alone — Android must hard-code no DISABLE/IGNORE under STRICT/LOCKED.  
4. pc-lab-cheap is enough for this task; strong did not beat cheap on safety (both 100%).

# PhoneCodex Evaluation Rubric

PhoneCodex is a **personal commitment OS**, not a universal morality blocker.

**Expected decision is relative to the user commitment, not universal morality.**

The same `packageName` + `screenText` can be **ALLOW** for one `userGoal` and **BLOCK** for another. The eval dataset teaches this. A classifier that always blocks Shorts or always suspects Chrome is wrong.

## What drives the decision

```text
userGoal / promise
  + strictnessLevel
  + activeGuardrails (permanent)
  + sessionCounters / limitState
  + packageName + screenText
  => expectedDecision
```

Examples:

| Screen | Promise | Expected |
|--------|---------|----------|
| YouTube Shorts player | "No short videos during study" | BLOCK |
| Same Shorts player | "Allow 40 Shorts, no adult content" (12/40 watched) | ALLOW |
| Same Shorts player | "Allow 40 Shorts" (40/40 watched) | BLOCK |
| Chrome movie page | "Educational browsing only" | BLOCK/WARN |
| Same movie page | "Only guardrail is no adult content" | ALLOW |
| Settings accessibility list | Browse only | WARN |
| PhoneCodex disable toggle | LOCKED session | LOCK |

## Dataset fields

See `evals/datasets/schema.json`. Key fields:

| Field | Purpose |
|-------|---------|
| `userGoal` | The user's active promise / commitment text |
| `strictnessLevel` | SOFT \| SMART \| STRICT \| LOCKED |
| `activeGuardrails` | Permanent rules (e.g. `no_adult_content`) |
| `commitmentType` | `focus_session`, `quota_entertainment`, `time_threshold`, `permanent_guardrail`, `monk_mode`, `install_gate`, `emergency_override` |
| `sessionCounters` | e.g. `shortsWatched`, `shortsLimit`, `sessionMinutes`, `attemptCount` |
| `limitState` | `not_reached` \| `reached` \| `n/a` |
| `expectedReasonCategory` | Why this decision is correct **for this promise** |

## Reason categories (commitment-relative)

| Category | When to use |
|----------|-------------|
| `study_aligned` | Activity matches study/build promise |
| `user_allowed_entertainment` | User explicitly allowed this distraction in their promise |
| `limit_not_reached` | Quota/time allowance still available per promise |
| `limit_reached` | Quota/time/attempt limit hit per promise |
| `adult_content` | Violates permanent adult guardrail (overrides entertainment allowance) |
| `short_form_disallowed` | Short-form blocked by this session promise |
| `strict_monk_mode` | Monk/zero-entertainment promise violated |
| `install_disallowed` | Install blocked by current promise |
| `tamper_attempt` | User trying to disable PhoneCodex protection |
| `ambiguous` | Unclear; prefer WARN unless promise is strict |
| `safe_app` | Essential communication |
| `emergency_or_system` | Emergency override |
| `neutral_navigation` | Settings/home browse |
| `social_feed` | Social distraction relative to promise |
| `gaming` / `shopping` | Category distractions under study promise |
| `install_page_productivity` | Productivity install allowed by promise |

Legacy categories (`short_form_entertainment`, `session_locked`, `install_page_risky`) may appear in older rows; prefer the commitment-relative names above for new cases.

## Decisions

| Decision | Meaning |
|----------|---------|
| **ALLOW** | Matches promise or essential/safe |
| **WARN** | Mild friction; promise allows uncertainty |
| **BLOCK** | Violates promise or guardrail |
| **LOCK** | Tamper or repeated breach per promise |

### Labeling rules

- Label **expectedDecision** for what PhoneCodex should do given **this user's promise**, not what a generic blocker would do.
- **Never** label BLOCK on Shorts/Reels solely because the app is YouTube/Instagram — check `userGoal` and counters first.
- **Adult guardrails** override entertainment quotas (Shorts allowed but not adult Shorts).
- **Emergency** always ALLOW regardless of promise.
- Paired cases: same `screenText`, different `userGoal`, different `expectedDecision` — required in `v0_seed`.

## Error types

### False allow
Expected BLOCK/LOCK → predicted ALLOW. Worst when `adult_content` or `tamper_attempt`.

### False block
Expected ALLOW → predicted BLOCK. Common when baseline ignores quota promises.

### Dangerous miss
False allow on `adult_content`, `tamper_attempt`, or `limit_reached` when user explicitly forbade the activity.

### Annoying block
False block on `study_aligned`, `user_allowed_entertainment`, `limit_not_reached`, `safe_app`.

## Metrics (`run_eval.py`)

| Metric | Definition |
|--------|------------|
| **Accuracy** | `predictedDecision == expectedDecision` |
| **False allow** | Expected BLOCK/LOCK → ALLOW |
| **False block** | Expected ALLOW → BLOCK |

### Classifier adapters

```bash
# Local commitment-aware keyword baseline (default)
python evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter baseline

# Azure OpenAI (placeholder — requires env vars, no live calls yet)
python evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter azure_openai
```

| Adapter | Purpose |
|---------|---------|
| `baseline` | Commitment-aware keyword classifier in `evals/runner/baseline_classifier.py` |
| `azure_openai` | Sends cases to Azure OpenAI using `evals/prompts/classifier_v01.txt` (not wired yet) |

Azure adapter reads `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` from the environment (see `.env.example`). It fails fast with a clear error if any are missing.

Phase 0 baseline is keyword-only on the local adapter — Azure adapter is for model comparison once credentials and inference are wired.

## Prompt contract

Classifier receives: `packageName`, `appLabel`, `screenText`, `userGoal`, `strictnessLevel`, `activeGuardrails`, and should receive `sessionCounters` / `limitState` when present.

Output JSON only:

```json
{
  "decision": "ALLOW",
  "confidence": 0.82,
  "reason": "Short explanation relative to user promise",
  "reasonCategory": "limit_not_reached"
}
```

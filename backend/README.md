# PhoneCodex Backend — AI Classifier API

Minimal Node.js server that powers cloud classification for the PhoneCodex Android app during development.

**Default stack:** Azure OpenAI `pc-lab-cheap` + `classifier_v04.txt` (94.7% on v1_edge_cases, 0 false allows).

---

## Quick start

```bash
cd backend
npm install
npm start
```

Server listens on **http://localhost:8787**.

Requires repo-root `.env` with Azure OpenAI variables (loaded automatically via `dotenv`).

---

## Environment variables

### Classifier (`POST /classify`) — Azure preferred

| Variable | Example | Required |
|----------|---------|----------|
| `AZURE_OPENAI_ENDPOINT` | `https://ay186mnc-1561-resource.openai.azure.com/` | Yes (Azure path) |
| `AZURE_OPENAI_API_KEY` | *(from Azure Portal → Keys)* | Yes (Azure path) |
| `AZURE_OPENAI_DEPLOYMENT` | `pc-lab-cheap` | Yes (Azure path) |
| `AZURE_OPENAI_API_VERSION` | `2024-08-01-preview` | Yes (Azure path) |

If **all four** Azure vars are set → classifier uses Azure.

### Classifier fallback

| Variable | When used |
|----------|-----------|
| `OPENAI_API_KEY` | Only when Azure vars are **missing** — uses direct OpenAI `gpt-4o-mini` |

### Promise drafter (`POST /draft-focus-promise`)

Uses `OPENAI_API_KEY` only (unchanged). Falls back to keyword rules if key missing.

**Never commit `.env` or log API keys.**

---

## Endpoints

### `GET /health`

```json
{
  "ok": true,
  "classifier": {
    "provider": "azure",
    "deployment": "pc-lab-cheap",
    "promptVersion": "v04"
  }
}
```

### `POST /classify`

**Android request (current):**

```json
{
  "packageName": "com.google.android.youtube",
  "screenText": "Shorts · swipe up for more",
  "goal": "Monk mode — zero fun content for 2 hours"
}
```

**Optional extended fields** (for future Android / PolicyEngine integration):

```json
{
  "packageName": "...",
  "screenText": "...",
  "goal": "...",
  "appLabel": "YouTube",
  "strictnessLevel": "STRICT",
  "activeGuardrails": ["no_adult_content"],
  "commitmentType": "monk_mode",
  "sessionCounters": { "shortsWatched": 12, "shortsLimit": 40 },
  "limitState": "not_reached"
}
```

**Response:**

```json
{
  "decision": "BLOCK",
  "confidence": 0.92,
  "reason": "Active short-form feed during monk mode promise.",
  "reasonCategory": "strict_monk_mode",
  "would_escalate": false,
  "meta": {
    "provider": "azure",
    "deployment": "pc-lab-cheap",
    "promptVersion": "v04",
    "latencyMs": 1842
  }
}
```

| Field | Meaning |
|-------|---------|
| `decision` | `ALLOW` \| `WARN` \| `BLOCK` \| `LOCK` |
| `confidence` | Model self-reported 0–1 |
| `reasonCategory` | Taxonomy aligned with eval rubric |
| `would_escalate` | `true` if cheap tier uncertain — future route to `pc-lab-strong` |
| `meta` | Provider/deployment/prompt version/latency (safe to log) |

**Escalation placeholder (not wired yet):**

When `confidence < 0.75` **OR** (`decision === "BLOCK"` AND `reasonCategory === "ambiguous"`):

- Response includes `"would_escalate": true`
- Server logs `classify_escalation_placeholder` with `targetDeployment: "pc-lab-strong"`
- No second API call yet — implement in `classifierService.js` when ready

---

## How Android talks to the backend

```
PhoneCodexAccessibilityService
  → ContentSignalDetector (OCR / screen text)
  → PolicyEngine (guardrails, counters — on device)
  → NetworkAiContentClassifier
       POST http://127.0.0.1:8787/classify
       Body: { packageName, screenText, goal }
  → AiConfidenceGate (uses confidence + source)
  → Overlay / friction UI
```

**File:** `app/.../NetworkAiContentClassifier.kt`

- URL: `http://127.0.0.1:8787/classify` (dev — localhost via adb reverse or emulator)
- Timeouts: 1.5s connect, 2.5s read
- On failure: falls back to `FakeAiContentClassifier` (local keyword rules)
- Parses: `decision`, `confidence`, `reason` only (LOCK not handled yet — will fallback)

**Dev setup (physical device):**

```bash
adb reverse tcp:8787 tcp:8787
npm start   # in backend/
```

**Production path (later):** Azure Functions or Container Apps with same `/classify` contract — Android points to HTTPS URL, not localhost.

---

## Classifier prompt

Loaded from **`evals/prompts/classifier_v04.txt`** at startup (same file as eval runner).

Prompt version **`v04`** is logged on every classify call and returned in `meta.promptVersion`.

To upgrade prompt: edit `classifier_v04.txt` or point `PROMPT_PATH` in `classifierService.js` to a new file.

---

## Safe logging

Every classify logs one JSON line to stdout:

```json
{
  "event": "classify",
  "provider": "azure",
  "deployment": "pc-lab-cheap",
  "promptVersion": "v04",
  "latencyMs": 1842,
  "decision": "WARN",
  "reasonCategory": "ambiguous",
  "confidence": 0.68,
  "would_escalate": true,
  "packageName": "com.android.chrome",
  "goalLength": 42,
  "goalPreview": "Finish assignment before sleep…",
  "screenTextLength": 128,
  "screenTextPreview": "about:blank — New Tab…"
}
```

**Never logged:** API keys, full `goal`, full `screenText`.

---

## Architecture

```
server.js              Express routes, draft-focus-promise
classifierService.js   Azure/OpenAI client, v04 prompt, escalation placeholder
evals/prompts/classifier_v04.txt   System prompt (shared with eval runner)
```

**Provider selection:**

1. All `AZURE_OPENAI_*` set → Azure deployment (default `pc-lab-cheap`)
2. Else `OPENAI_API_KEY` → direct OpenAI `gpt-4o-mini` + same v04 prompt
3. Else → 500 error on `/classify`

---

## Manual test

```bash
curl -s http://localhost:8787/health | jq

curl -s -X POST http://localhost:8787/classify \
  -H "Content-Type: application/json" \
  -d '{"packageName":"com.google.android.youtube","screenText":"Shorts player swipe feed","goal":"Monk mode zero fun"}' | jq
```

---

## Related docs

- `evals/reports/classifier_v04_recommendation.md` — why v04 + cheap default
- `evals/reports/azure_model_matrix.md` — deployment tiers
- `docs/cto-strategy-phonecodex-ai.md` — policy-first architecture

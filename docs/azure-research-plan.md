# PhoneCodex Azure Research & Execution Plan

**Owner:** Ankit Yadav  
**Horizon:** 20 days  
**Status:** Phase 0 — **Model matrix + 15-day plan + CTO memo complete**; classifier_v03 @ 88%, 3 deployments live  
**Portal check (2026-09-05):** `ay186mnc-1561-resource` westus3 — `pc-lab-cheap`, `pc-lab-strong`, `pc-lab-vision` **Succeeded**  
**Last updated:** 2026-09-05 (139-model audit; premium quota still 0; M1–M6 ready to run)

---

## Executive summary

You have **expiring Azure credit**. Credit you don't spend is **money thrown away**. This plan exists to **burn ~$1000–1800 productively** in 20 days and walk away with the best classifier stack PhoneCodex has ever had — backed by numbers, not vibes.

```text
Safe App → Tamper Guard → Permanent Guardrail → App Rule → Content Signals → AI Classifier → AiConfidenceGate → Overlay
```

Policy is law. AI is suggestion. That architecture stays. Azure does not replace it — Azure makes the advisor worth trusting.

### Budget (the real targets)

| Line | Amount | Role |
|------|--------|------|
| **Minimum target spend** | **$1,000** | Floor — below this you under-used expiring credit |
| **Expected spend** | **$1,200–1,800** | Normal aggressive research burn |
| **Hard stop** | **$2,000** | Absolute ceiling — stop all inference |
| **Budget alerts** | $1,500 / $1,800 / $2,000 | **Safety rails only** — not the strategy |

Alerts tell you when you're approaching the cliff. They are not a reason to spend less. **The strategy is maximum useful evidence per dollar.**

### What $1000+ must buy (non-negotiable deliverables)

1. **500–1,000 labeled eval cases** (JSONL)
2. **5+ models** compared on identical slices
3. **10+ prompt variants** swept systematically
4. **3 consistency runs** per winning config (variance matters)
5. **100+ vision/screenshot cases** with text vs vision vs hybrid comparison
6. **Hosted classifier prototype** on Azure (serverless, not always-on)
7. **Evaluation dashboard / reporting** (HTML or notebook — reproducible)
8. **Failure cluster analysis** — top patterns ranked with examples
9. **Cost + latency benchmarks** — p50/p95, $/1k decisions, timeout behavior
10. **Written recommendation:** exact model + prompt + confidence thresholds for PhoneCodex v1

### Every dollar must produce one of

- Dataset rows (JSONL)
- Eval run records (CSV/JSON)
- Model comparison tables
- Screenshot/vision benchmark results
- Markdown findings
- Deployable backend learning (hosted `/classify` prototype)

**No dollar for:** idle VMs, Kubernetes, GPU clusters, empty dashboards, or "we deployed something."

---

## Spend allocation summary

| Phase | Days | Target spend | Cumulative | Primary artifacts |
|-------|------|-------------|------------|-------------------|
| 0 — Foundation | 1–3 | $0–50 | $50 | Eval harness, 200 seed cases, rubric, safety alerts |
| 1 — Dataset scale-up | 4–6 | $80–120 | $170 | 500+ case core dataset, schema, labeling pipeline |
| 2 — Text model sweep | 7–10 | $350–500 | $670 | 5+ models × 10+ prompts × full core set, CSV leaderboard |
| 3 — Consistency + policy replay | 11–13 | $200–300 | $970 | 3× re-runs on top 3 configs, policy simulator, failure tags |
| 4 — Vision benchmark | 14–16 | $300–450 | $1,420 | 100+ screenshot cases, text vs vision vs hybrid |
| 5 — Hosted prototype + latency | 17–18 | $150–250 | $1,670 | Azure Functions/Container Apps `/classify`, p50/p95 report |
| 6 — Dashboard + synthesis | 19–20 | $80–130 | $1,800 | Eval dashboard, failure clusters, final recommendation memo |
| **Buffer / overflow** | — | $0–200 | **≤$2,000** | Extra consistency runs, prompt refinement, hard-case re-sweep |

**Expected total: $1,200–1,800.** Hitting $1,000 is the minimum success bar.

---

## 1. CTO verdict

### Use Azure for (now) — spend aggressively here

| Area | Volume target | Why |
|------|---------------|-----|
| **Azure OpenAI / AI Foundry inference** | 15,000–40,000 API calls over 20 days | Core product R&D — model + prompt selection |
| **Text classifier eval** | 500–1,000 cases × 5 models × 10 prompts | Statistical power to pick a winner |
| **Vision classifier eval** | 100–150 cases × 3–4 multimodal models | Settle text-first vs hybrid vs vision-escalation |
| **Consistency runs** | Top 3 configs × 3 full passes | LLM variance is real — measure it |
| **Prompt sweeps** | 10–15 variants (strictness, false-allow, false-block axes) | Prompt is half the product |
| **Hosted classify prototype** | Functions or Container Apps (min replicas = 0) | Real latency from phone → Azure |
| **Private blob storage** | Screenshots + eval artifacts | Vision eval + reproducibility |
| **Application Insights** | Log every hosted + batch run | Token/latency/cost truth |
| **Eval dashboard** | Static HTML or Jupyter → exported report | One place to see all runs |

### Do NOT use Azure for (still forbidden)

| Area | Why |
|------|-----|
| **Random VMs** | No workload needs a persistent server. Inference is API calls. |
| **AKS / Kubernetes** | You are one founder, not a platform team. |
| **GPU clusters** | Foundry/OpenAI serves models. You don't train. |
| **Public storage** | Screenshots may contain sensitive UI. Private containers only. |
| **Always-on expensive tiers** | Premium Functions, minReplicas > 0, dedicated CA profiles |
| **Cosmos DB / managed Postgres** | JSONL + blob is enough for research |
| **Fine-tuning (unless evals justify)** | Only after 500+ clean labels AND baseline ceiling proven |
| **Cloud-side policy engine** | Policy stays on device. Period. |
| **Production Android changes** | No ship until evals prove improvement |

### Wasteful / fake progress (still trash)

- Deploying infra with no eval runs attached
- Microservices before monolith eval runner works
- RAG over docs for ALLOW/WARN/BLOCK (wrong problem)
- Model leaderboard without fixed dataset version hash
- Vision on every frame in production (eval question ≠ product default)
- **Leaving $500+ credit unspent because you were "being careful"** — that is the actual waste

**Rule:** If a spend line doesn't map to a row in `evals/reports/`, don't spend it.

---

## 2. 20-day execution plan (aggressive)

Assumes 2–4 focused hours/day. Scale up if full-time — more runs, not more infra.

### Phase 0 — Days 1–3: Foundation + safety rails

**Build**

- Read decision stack: `PhoneCodexAccessibilityService` → signals → `NetworkAiContentClassifier` → `AiConfidenceGate` → overlay
- Create `evals/` harness (see §8) — local runner first
- Hand-label **200 seed cases** → `v0_seed.jsonl`
- Write `docs/eval-rubric.md`
- Configure Azure budget alerts at **$1,500 / $1,800 / $2,000** (safety only)
- Create Azure OpenAI / AI Foundry resource (single region)

**Artifacts**

- `evals/runner/` working locally
- `evals/datasets/v0_seed.jsonl` (200 rows)
- `evals/reports/baseline_local_YYYYMMDD.csv`
- Budget alerts live

**Spend: $0–50** (smoke-test inference + portal)

---

### Phase 1 — Days 4–6: Dataset scale-up

**Build**

- Expand to **500–700 core cases** (`v1_core.jsonl`):
  - YouTube: Shorts, lecture, search, home feed, comments
  - Chrome: study tabs, adult, new tab, docs, install pages
  - Instagram: Reels, DMs, feed, stories
  - WhatsApp/Telegram: chat, calls, groups
  - System: Settings, dialer, Play Store
  - Edge: empty trees, loading screens, ambiguous UI
- Use Decision Inspector + feedback exports (sanitized) to add real failure cases
- Optional: semi-automated labeling assist via Azure (human review required on every row)

**Artifacts**

- `evals/datasets/v1_core.jsonl` (500–700 rows)
- `evals/datasets/schema.json`
- Labeling stats doc (category distribution)

**Spend: $80–120** (labeling assist calls, dataset QA passes)

---

### Phase 2 — Days 7–10: Text model + prompt sweep (main burn)

**Build**

- Deploy/access **5+ models** (availability-dependent):
  - `gpt-4o-mini` (baseline — matches `backend/server.js`)
  - `gpt-4o` or latest standard multimodal
  - Next-gen mini if available
  - One Foundry-hosted open/small model (if available)
  - One "quality ceiling" model for upper bound
- Write **10–15 prompt variants**:
  - v1: current `backend/server.js` prompt
  - v2–v4: false-allow strictness axis
  - v5–v7: false-block leniency axis
  - v8–v10: goal-context emphasis
  - v11–v15: package-specific rules (YouTube, Chrome, Instagram)
- Run full matrix: **models × prompts × v1_core** (~25,000–35,000 inference calls)
- Output leaderboard CSV sorted by dangerous miss rate, then annoying block rate

**Artifacts**

- `evals/prompts/classifier_v01.txt` … `v15.txt`
- `evals/reports/text_sweep_YYYYMMDD.csv` (full matrix)
- `evals/reports/text_leaderboard_YYYYMMDD.md` (top 10 configs)
- Shortlist: top 5 model+prompt pairs

**Spend: $350–500** — this is where most credit goes. Good.

---

### Phase 3 — Days 11–13: Consistency runs + policy stack replay

**Build**

- Take **top 3 model+prompt configs** from Phase 2
- Run each **3 full passes** on v1_core (measure variance: same case → different decision?)
- Build/extend **policy simulator** mirroring Android stack:
  ```text
  Safe App → Guardrail → App Rule → Content Signals → AI → AiConfidenceGate → LOCK rules → final
  ```
- Tag every failure:
  - Classifier wrong
  - Policy wrong
  - Gate wrong (threshold)
  - Layer override (rule/guardrail saved user)
- Produce **top 30 failure clusters** with 3 examples each

**Artifacts**

- `evals/reports/consistency_YYYYMMDD.csv` (variance per config)
- `evals/reports/stack_replay_YYYYMMDD.md`
- `evals/reports/failure_clusters_YYYYMMDD.md` (ranked)
- `AiConfidenceGate` threshold recommendation (document only)

**Spend: $200–300** (3 configs × 3 runs × 500–700 cases)

---

### Phase 4 — Days 14–16: Vision / screenshot benchmark

**Build**

- Curate **100–150 screenshot cases** (`v1_vision.jsonl`):
  - 30 YouTube (Shorts vs lecture vs search)
  - 25 Chrome (adult vs study vs new tab)
  - 20 Instagram (Reels vs DM vs feed)
  - 15 Play Store install pages
  - 10 system/settings (must ALLOW)
  - 20 hard ambiguous cases from Phase 3 failure clusters
- Store in **private blob container** (no public access)
- Run **3–4 multimodal models** per case:
  - Text-only (accessibility dump)
  - Image-only
  - Text + image (hybrid)
- Compare: does vision beat text+signals by enough to justify cost/privacy?

**Artifacts**

- `evals/datasets/v1_vision.jsonl` (100–150 rows)
- `evals/fixtures/screenshots/` or blob refs
- `evals/reports/vision_vs_text_YYYYMMDD.csv`
- `evals/reports/vision_decision_YYYYMMDD.md` (go/no-go + escalation policy)

**Spend: $300–450** — vision is expensive. Spend it deliberately on hard cases, not random screenshots.

---

### Phase 5 — Days 17–18: Hosted prototype + latency/cost benchmark

**Build**

- Deploy **hosted `/classify`** mirroring `backend/server.js`:
  - Azure Functions (Consumption) **or** Container Apps (minReplicas = 0)
  - Keys in Key Vault or app settings — never in repo
  - Application Insights wired
- Benchmark from **real Android device** (adb reverse or deployed URL):
  - p50 / p95 latency
  - Timeout at 2500ms (match `NetworkAiContentClassifier.READ_TIMEOUT_MS`)
  - Cold start vs warm
  - Cost per 1,000 decisions at chosen model
- Run **1,000 live classify calls** through hosted endpoint (synthetic + eval replay)

**Artifacts**

- `backend/azure/` or `infra/classify-prototype/` (deploy scripts, no secrets)
- `evals/reports/latency_cost_YYYYMMDD.csv`
- `evals/reports/hosted_prototype_YYYYMMDD.md`
- Architecture decision: Functions vs Container Apps for v1

**Spend: $150–250** (hosting pennies + 1k inference calls + load test)

---

### Phase 6 — Days 19–20: Dashboard, synthesis, final recommendation

**Build**

- Build **eval dashboard** (static HTML generated from CSVs, or Jupyter notebook exported):
  - Leaderboard tab
  - Failure cluster tab
  - Consistency variance tab
  - Vision comparison tab
  - Latency/cost tab
- Write **`docs/azure-research-findings.md`**:
  - **Recommended model:** `<exact deployment name>`
  - **Recommended prompt:** `<file path + version>`
  - **Recommended AiConfidenceGate thresholds:** (if change warranted)
  - **Vision policy:** text-only / hybrid escalation / no vision
  - **Dangerous miss rate:** X% on v1_core (post-policy)
  - **Cost per 1k decisions:** $Y at p95 Z ms
  - **Top 10 failure patterns** still unresolved
- If under $1,000 spent: run **extra consistency pass** or **expand hard-case subset** until floor hit
- Tear down always-on resources; keep blob + findings

**Artifacts**

- `evals/dashboard/index.html` (or equivalent)
- `docs/azure-research-findings.md` ← **the deliverable investors/you actually read**
- Resource cleanup checklist (hosting only — keep eval data)

**Spend: $80–130** (final sweeps + dashboard generation runs)

---

## 3. Experiments (detailed volumes)

### 3.1 Text-only screen classifier eval

| Parameter | Target |
|-----------|--------|
| Dataset | v1_core: **500–1,000 cases** |
| Models | **5+** |
| Prompts | **10–15** |
| Total inference calls | **25,000–75,000** (matrix dependent) |
| Consistency re-runs | **3×** on top 3 configs |

**Input:** `packageName`, `appLabel`, `screenText`, `userGoal`, `strictnessLevel`, `activeGuardrails`  
**Output:** `ALLOW | WARN | BLOCK` + confidence + reason

**Success criteria (on v1_core, post-policy)**

- Dangerous miss rate **< 2%**
- Annoying block rate **< 12%** (STRICT/LOCKED may trade higher)
- p95 latency **< 2,500 ms** via hosted prototype

### 3.2 Vision / screenshot classifier eval

| Parameter | Target |
|-----------|--------|
| Dataset | v1_vision: **100–150 cases** |
| Models | **3–4** multimodal |
| Modes | text-only, image-only, hybrid |
| Total inference calls | **900–1,800** |

Hard cases from failure clusters get priority, not random screenshots.

### 3.3 Model comparison matrix

Fixed dataset hash. Every model runs identical prompt set. No cherry-picking slices.

| Model tier | Role |
|------------|------|
| Mini (gpt-4o-mini class) | Production cost candidate |
| Standard (gpt-4o class) | Quality ceiling |
| Next-gen mini | Cost/quality frontier |
| Foundry open/small | Cost floor experiment |
| Quality ceiling | Upper bound reference |

### 3.4 Policy simulator

Offline replay of full Android decision order. Every eval run produces **both**:

- `classifierDecision` (AI alone)
- `finalDecision` (after full stack)

Report metrics on **finalDecision** — that's what the user experiences.

### 3.5 Latency / cost benchmark

| Measurement | Target volume |
|---------------|---------------|
| Hosted endpoint calls | **1,000+** |
| Device-origin calls | **200+** from real phone |
| Regions tested | 1 primary (+ 1 if latency bad) |

Output: $/1k decisions, p50, p95, timeout fallback rate.

### 3.6 Failure cluster analysis

- Cluster failures by: `packageName`, `expectedReasonCategory`, `classifierDecision vs expected`, `finalDecision vs expected`
- Rank top **30 clusters** by frequency × severity
- For each: 3 example case IDs, suggested fix (prompt / signal / rule / gate)

---

## 4. Dataset design (JSONL)

One JSON object per line. UTF-8. Commit **sanitized** sets only.

### Schema

```json
{
  "id": "yt_shorts_001",
  "packageName": "com.google.android.youtube",
  "appLabel": "YouTube",
  "screenText": "Shorts\n@creator\nSwipe up for more",
  "screenshotPath": "evals/fixtures/screenshots/yt_shorts_001.png",
  "userGoal": "Study DSA for 30 minutes",
  "strictnessLevel": "STRICT",
  "activeGuardrails": ["no_adult_content"],
  "expectedDecision": "BLOCK",
  "expectedReasonCategory": "short_form_entertainment",
  "notes": "Strong Shorts signals in accessibility tree"
}
```

### Field rules

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Stable slug |
| `packageName` | yes | Android package |
| `appLabel` | yes | Human label for prompts |
| `screenText` | yes | Simulated accessibility dump |
| `screenshotPath` | no | Required for vision tier |
| `userGoal` | yes | Session goal string |
| `strictnessLevel` | yes | SOFT \| SMART \| STRICT \| LOCKED |
| `activeGuardrails` | yes | Array of guardrail ids |
| `expectedDecision` | yes | ALLOW \| WARN \| BLOCK \| LOCK |
| `expectedReasonCategory` | yes | See taxonomy |
| `notes` | no | Reviewer context |

### `expectedReasonCategory` taxonomy

- `safe_app`
- `emergency_or_system`
- `study_aligned`
- `neutral_navigation`
- `short_form_entertainment`
- `adult_content`
- `social_feed`
- `gaming`
- `shopping`
- `install_page_risky`
- `install_page_productivity`
- `session_locked`
- `ambiguous`

### Dataset tiers (revised volumes)

| Tier | Size | Purpose |
|------|------|---------|
| v0_seed | 200 | Hand-labeled bootstrap |
| v1_core | 500–1,000 | Primary text eval set |
| v1_vision | 100–150 | Screenshot/multimodal set |
| v1_hard | 50–100 | Failure cluster subset for re-sweep |

### Labeling rules

- Label **post-policy outcome** — what user should experience
- Safe App → ALLOW always
- AI_DECIDE app rules → label expected after full stack
- Ambiguous → WARN unless LOCKED + clearly distraction

---

## 5. Metrics

### Primary

| Metric | Definition |
|--------|------------|
| **Accuracy** | % `finalDecision == expectedDecision` |
| **False allow rate** | expected BLOCK/LOCK → got ALLOW |
| **False block rate** | expected ALLOW → got BLOCK |
| **Dangerous miss rate** | false allow on `{adult_content, short_form_entertainment, session_locked}` |
| **Annoying block rate** | false block on `{study_aligned, neutral_navigation, emergency_or_system}` |
| **Consistency variance** | % cases where 3 identical-config runs disagree |

### Operational

| Metric | Definition |
|--------|------------|
| **Latency p50 / p95** | End-to-end ms (device → hosted → model → response) |
| **Cost per 1000 decisions** | Tokens × price + hosting amortization |
| **Fallback rate** | Timeout/error → `FakeAiContentClassifier` |
| **Override rate** | Guardrail/rule/safe app overrides classifier |

### Reporting (every run)

```csv
run_id,dataset_hash,model,prompt_version,pass_number,accuracy,false_allow,false_block,dangerous_miss,annoying_block,consistency_variance,p50_ms,p95_ms,cost_usd,cost_per_1k,n
```

**Ship gate:** No production Android classifier change unless dangerous miss rate is **≤ baseline** on v1_core with ≥3 consistency passes.

---

## 6. Azure resources

**Create in Phase 0–2.** Serverless only. No always-on.

### 6.1 Azure OpenAI / AI Foundry — classifier model comparison

**Account:** `ay186mnc-1561-resource` · **Region:** westus3 · **SKU policy:** Standard (serverless pay-per-call) only — **no PTU**, **no Sora/video**.

Three deployments are live for the **same eval command** with `classifier_v03.txt`. Swap only `AZURE_OPENAI_DEPLOYMENT` in `.env` (never commit `.env`).

| Tier | Deployment name | Model | Version | SKU / capacity | Expected use | Why useful for PhoneCodex |
|------|-----------------|-------|---------|----------------|--------------|---------------------------|
| **Cheap baseline** | `pc-lab-cheap` | `gpt-4.1-mini` | `2025-04-14` | Standard · 100k TPM | High-volume sweeps, regression on `v0_seed`, cost/latency floor | Fast JSON classifier; production cost candidate if accuracy holds at scale |
| **Strong text / reasoning** | `pc-lab-strong` | `gpt-4.1` | `2025-04-14` | Standard · 100k TPM | Primary text classifier evals on `v0_challenge` | Best **deployable** OpenAI text model in region; commitment-relative ALLOW/WARN/BLOCK boundaries |
| **Strongest useful (multimodal)** | `pc-lab-vision` | `gpt-4o` | `2024-11-20` | Standard · 100k TPM | Text eval now + future screenshot/OCR classifier | `jsonSchemaResponse` capability; vision path for messy accessibility trees without new deploy |

**Not deployed (quota 0 — request in Foundry → Quotas):**

| Planned deployment | Model | Version | SKU | Blocker | Role when live |
|--------------------|-------|---------|-----|---------|----------------|
| `pc-lab-reasoning` | `gpt-5.4` | `2026-03-05` | GlobalStandard | TPM quota 0 | Strongest OpenAI reasoning; hard ambiguous cases |
| `pc-lab-claude-opus` | `claude-opus-5` | `2` | GlobalStandard | TPM quota 0 | Best Claude for thin/contradictory context (needs `azure_anthropic` adapter) |

**Do not deploy:** Sora / video models, Provisioned Throughput (PTU), deprecated `gpt-4o-mini` `2024-07-18`, deprecating `o1`/`o4-mini` new deploys.

**Deletion policy:** Do **not** delete `pc-lab-cheap`, `pc-lab-strong`, or `pc-lab-vision` without explicit approval — they are the comparison baseline.

#### v03 eval command (identical across models)

```powershell
# Set deployment in shell (or .env) — one model per run
$env:AZURE_OPENAI_DEPLOYMENT='pc-lab-cheap'   # or pc-lab-strong / pc-lab-vision

py -3.12 evals/runner/run_eval.py `
  --dataset evals/datasets/v0_challenge.jsonl `
  --adapter azure_openai `
  --prompt evals/prompts/classifier_v03.txt
```

Repeat for each deployment. Record CSV from `evals/reports/azure_openai_*.csv`.

#### Metrics to compare (per deployment × prompt)

| Metric | Source | Gate |
|--------|--------|------|
| Accuracy | eval CSV | Higher is better |
| False allows | eval CSV | **Must stay 0** |
| False blocks | eval CSV | **Must stay 0** |
| p50 / p95 latency | Log per-case timing (add to runner) or App Insights | Lower is better for on-device advisor |
| Cost per 1k cases | Azure Cost Management + token counts | Cheapest model that meets safety gates wins |

**Verified v03 baseline (single-model run):** 88% accuracy, 0 false allows, 0 false blocks — `evals/reports/azure_openai_20260905_112326.csv`. Full matrix pending runs on all three deployments.

| | |
|--|--|
| **Why** | 25k–75k inference calls — the entire research program |
| **Spend** | $800–1,400 (largest line item) |
| **Do NOT enable** | Public anonymous access; fine-tuning day 1; PTU; Sora |

### 6.2 Azure Functions (Consumption) or Container Apps (scale-to-zero)

| | |
|--|--|
| **Why** | Hosted `/classify` prototype + latency tests |
| **Spend** | $20–80 |
| **Do NOT enable** | Premium plan; minReplicas > 0 |

### 6.3 Storage Account (Standard LRS, private)

| | |
|--|--|
| **Why** | Screenshots, eval exports, run archives |
| **Spend** | $5–15 |
| **Do NOT enable** | Public blob access |

### 6.4 Application Insights + Log Analytics

| | |
|--|--|
| **Why** | Latency/token logging for hosted prototype |
| **Spend** | $10–30 |
| **Do NOT enable** | 365-day retention; verbose sampling |

### 6.5 Key Vault (optional, recommended for hosted prototype)

| | |
|--|--|
| **Why** | Store API keys outside repo |
| **Spend** | $5–10 |
| **Do NOT enable** | Over-permissive access policies |

### Resource naming

```text
rg-phonecodex-research-eastus
aoai-phonecodex-research
stphonecodexeval001
func-phonecodex-classify
appi-phonecodex-research
kv-phonecodex-research
```

### End-of-sprint cleanup

- [ ] Export all reports + dashboard to repo
- [ ] Delete Function App / Container Apps environment
- [ ] Delete or downgrade App Insights
- [ ] Keep private blob with eval artifacts (cheap) OR export locally and delete
- [ ] Delete Azure OpenAI deployments if no longer needed
- [ ] Confirm final spend: **≥ $1,000**, **≤ $2,000**

---

## 7. Architecture

### 7.1 Research + prototype architecture

```text
┌─────────────────────┐
│   Android app       │
│ AccessibilitySvc    │
└─────────┬───────────┘
          │ POST /classify
          ▼
┌─────────────────────┐
│ Hosted classifier   │  ← Azure Functions / Container Apps (scale-to-zero)
│  backend/server.js  │
│  + prompt registry  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Azure OpenAI /      │  ← 5+ model deployments
│ AI Foundry          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Eval runner (batch) │  ← parallel path for matrix sweeps
│ + policy simulator  │
│ + dashboard gen     │
└─────────────────────┘
```

### 7.2 Eval batch pipeline

```text
v1_core.jsonl (500–1000)
  → for each (model, prompt, pass):
      → Azure OpenAI adapter
      → policy simulator
      → append to run CSV
  → aggregate leaderboard
  → failure cluster analysis
  → dashboard HTML
  → blob archive (private)
```

### 7.3 Law vs suggestion (unchanged)

| Layer | Role |
|-------|------|
| Safe Apps | Always ALLOW |
| Permanent Guardrails | BLOCK/WARN override |
| App Rules | ALLOW/WARN/BLOCK/skip AI |
| Content Signals | Deterministic pre-filter |
| **AI Classifier** | **Suggestion only** |
| AiConfidenceGate | Downgrade low-confidence |
| Session LOCK | LOCK regardless of AI |

**Product sentence:** Spend Azure credit to make the advisor smarter. Kotlin on the phone keeps the law.

---

## 8. First implementation task

Start **today** in repo — local first, Azure adapter day 3–4.

### Task: Eval harness v1 (expanded scope)

```text
evals/
  datasets/
    v0_seed.jsonl           # 200 cases (week 1 target)
    v1_core.jsonl           # 500–1000 (week 2)
    v1_vision.jsonl         # 100–150 (week 3)
    schema.json
  prompts/
    classifier_v01.txt … v15.txt
  runner/
    run_eval.py             # CLI: --dataset --model --prompt --pass --adapter
    run_sweep.py            # full matrix runner
    run_consistency.py      # 3× pass runner
    policy_simulator.py
    failure_clusters.py
    adapters/
      baseline.py           # commitment-aware keyword classifier (done)
      azure_openai.py       # batch inference placeholder (env check only)
  dashboard/
    generate_dashboard.py   # CSV → HTML
  reports/
  fixtures/screenshots/
  README.md
```

**Week 1 acceptance**

- `python evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter baseline`
- Baseline CSV + markdown on 200 cases
- Policy simulator passes 20 unit cases

**Adapter status (local, no Azure spend yet)**

- `baseline` — working; 100% on `v0_seed.jsonl` commitment-relative set
- `azure_openai` — placeholder; fails fast if `AZURE_OPENAI_*` env vars missing; inference not wired

**Week 2 acceptance**

- Azure adapter working
- First full text sweep on v1_core (500+ cases)
- Leaderboard CSV generated

No Android blocking behavior changes until `docs/azure-research-findings.md` recommends a config with proven dangerous miss rate.

---

## 9. Risk register

| Risk | Mitigation |
|------|------------|
| Under-spending credit | Track cumulative spend weekly; if <$500 by day 10, expand matrix |
| Over-spending past $2k | Hard stop alerts; sweep script checks budget |
| Vision cost spiral | Cap at 150 cases × 4 models; prioritize failure-cluster cases |
| LLM variance | 3 consistency passes mandatory on finalists |
| Eval ≠ production | Policy simulator mirrors Android order exactly |
| Privacy in screenshots | Synthetic/fixture only; no real user PII |
| India latency | Test from device; pick region accordingly |

---

## 10. What success looks like on Day 20

You spent **≥ $1,000** and can answer:

1. **Exact model + prompt** for PhoneCodex v1 classifier — with CSV proof
2. **Dangerous miss rate** on 500–1,000 cases — post-policy, 3-pass average
3. **Vision go/no-go** — with 100+ case comparison table
4. **Cost per 1k decisions** and **p95 latency** from hosted prototype
5. **Top 30 failure clusters** — ranked, with fix recommendations
6. **Eval dashboard** — one URL/file showing everything
7. **Hosted `/classify`** — working on Azure, keys not in repo

If you spent $200 and have vibes, you failed.  
If you spent $1,500 and have a dashboard full of CSVs and a written recommendation, you win.

---

## Appendix A — Current codebase map

| Component | Path |
|-----------|------|
| Accessibility pipeline | `app/.../PhoneCodexAccessibilityService.kt` |
| Network classifier | `app/.../NetworkAiContentClassifier.kt` |
| Confidence gate | `app/.../AiConfidenceGate.kt` |
| Content signals | `app/.../ContentSignalDetector.kt` |
| Policy engine | `app/.../PolicyEngine.kt` |
| Local backend | `backend/server.js` |
| Decision Inspector | `app/.../ui/home/DebugSections.kt` |
| Product principles | `docs/PRODUCT_MEMORY.md` |

---

## Appendix B — AI Lab verification (2026-09-05)

**Method:** Azure CLI (`az cognitiveservices account list-models` + deployment create/show) + eval runner.  
**Verifier session:** `ay186mnc@gmail.com` / Default Directory (`ay186mncgmail.onmicrosoft.com`).  
**Credits horizon:** Azure credits expire **22 Sep 2026** (~17 days). Strategy = **max useful product progress** (~$1,000+ on inference/eval/lab), not minimum spend. No VMs, AKS, GPU, PTU, Sora, or always-on infra.

### Resource

| Field | Value |
|---|---|
| Azure OpenAI account | `ay186mnc-1561-resource` |
| Foundry project | `ay186mnc-1561` |
| Resource group | `phonecodex-dev` |
| Region | **westus3** |
| Subscription | Azure subscription 1 (`a3dc5296-f948-427e-8656-c6bc52afee21`) |
| Endpoint | `https://ay186mnc-1561-resource.openai.azure.com/` |

**Also exists (not eval target):** `phonecodex-ai-dev` — East US 2, empty deployment list.

### Prior failure (resolved)

Old broken deploy `gpt-4o-mini` / GlobalStandard / `2024-07-18` is **gone** (ARM deployment list was empty before create). Foundry portal "Version 2" is **not** in westus3 CLI catalog — only `2024-07-18` (Standard SKU deprecated 2026-03-31). **Do not redeploy gpt-4o-mini** on this account; use lab deployments below.

### AI Lab deployments (Standard SKU — pay-per-call, serverless)

Three tiers cover the model comparison matrix. **No new deployments needed** until premium quota is approved.

| Tier | Deployment | Model | Version | SKU | TPM | Status | Use case |
|------|------------|-------|---------|-----|-----|--------|----------|
| **Cheap baseline** | `pc-lab-cheap` | gpt-4.1-mini | 2025-04-14 | Standard | 100k | **Succeeded** | High-volume sweeps, smoke, prompt A/B |
| **Strong text** | `pc-lab-strong` | gpt-4.1 | 2025-04-14 | Standard | 100k | **Succeeded** | Reasoning / ambiguous ALLOW-WARN-BLOCK |
| **Vision-capable** | `pc-lab-vision` | gpt-4o | 2024-11-20 | Standard | 100k | **Succeeded** | Screenshot understanding (multimodal eval later) |

**Comparison commands:** `evals/reports/azure_model_matrix.md` (primary) · `evals/reports/model_comparison_plan.md`  
**15-day schedule:** `docs/azure-15-day-execution-plan.md`  
**CTO strategy:** `docs/cto-strategy-phonecodex-ai.md`  
**Model audit JSON:** `evals/reports/azure_model_capability_audit.json` (139 entries)

**Local `.env`:** set `AZURE_OPENAI_DEPLOYMENT` per run (`pc-lab-cheap` | `pc-lab-strong` | `pc-lab-vision`). Never commit `.env`.

### Premium model audit (2026-09-05)

**Goal:** Best models for hard PhoneCodex cases — ambiguous screen/context, false-allow pressure, vision escalation.  
**Method:** `az cognitiveservices account list-models` + ARM PUT deploy attempts (`api-version=2025-10-01-preview`). Full catalog: `evals/reports/azure_models_full.json`.

#### Claude / Anthropic

| Model | Version | SKU in westus3 | Deploy status | Why it matters for PhoneCodex |
|---|---|---|---|---|
| **Claude Fable 5** | — | — | **Not in catalog** | Name does not exist in Foundry for this account. Ignore — use **Claude Opus 5** instead. |
| **`claude-opus-5`** | `2` | GlobalStandard, DataZoneStandard | **Blocked — quota 0** | Strongest Claude available. Best candidate for ambiguous ALLOW/WARN/BLOCK when context is thin or contradictory. |
| `claude-opus-5` | `1` | GlobalStandard | Blocked — quota 0 | Prior Opus 5 revision; prefer v2. |
| `claude-opus-4-8` | `2` | GlobalStandard, DataZoneStandard | Blocked — quota 0 | Fallback if Opus 5 quota denied; still top-tier reasoning. |
| `claude-sonnet-5` | `2` | GlobalStandard, DataZoneStandard | Blocked — quota 0 | Cheaper Claude tier for high-volume hard-case sweeps once quota granted. |
| `claude-haiku-4-5` | `2` | GlobalStandard | Blocked — quota 0 | Fast/cheap Claude baseline — only after Opus/Sonnet quota. |

**Claude deploy recipe (when quota > 0):** Portal UI omits required `modelProviderData` — use REST/CLI with API **`2025-10-01-preview`**. Payload template: `evals/reports/_deploy_claude_opus.json`. Target deployment name: **`pc-lab-claude-opus`**.

**Claude inference endpoint (not wired in eval runner yet — no live deployment):**

```http
POST https://ay186mnc-1561-resource.services.ai.azure.com/anthropic/v1/messages
api-key: <from Portal → Keys and Endpoint — never commit>
anthropic-version: 2023-06-01
Content-Type: application/json

{"model": "pc-lab-claude-opus", "max_tokens": 300, "messages": [...]}
```

Use **deployment name** as `model`, not `claude-opus-5`. Existing `azure_openai` adapter **will not work** for Claude — needs Messages API adapter (`evals/runner/adapters/azure_anthropic.py`) after deploy succeeds.

#### OpenAI / Azure — strongest available

| Model | Version | SKU | Deploy status | Deployment | Why it matters for PhoneCodex |
|---|---|---|---|---|---|
| **`gpt-5.4`** | `2026-03-05` | GlobalStandard only | **Blocked — quota 0** | (planned `pc-lab-reasoning`) | Strongest OpenAI in catalog. Primary target for hard reasoning evals once quota approved. |
| `gpt-5.2` | `2025-12-11` | GlobalStandard | Blocked — quota 0 | — | Fallback premium OpenAI if 5.4 quota slow. |
| `gpt-5.1` | `2025-11-13` | Standard + GlobalStandard | Blocked — quota 0 (both SKUs) | — | Has Standard SKU but **0 TPM** — same quota gate as 5.4. |
| `gpt-5.6-sol` | `2026-07-09` | GlobalStandard | Blocked — quota 0 | — | Newest sol-class model; eval after 5.4 baseline. |
| **`gpt-4.1`** | `2025-04-14` | **Standard** | **Deployed ✓** | `pc-lab-strong` | **Strongest text model live today.** Run `v0_challenge` here first for premium text baseline. |
| **`gpt-4o`** | `2024-11-20` | **Standard** | **Deployed ✓** | `pc-lab-vision` | **Strongest vision + text live today.** Screenshot / overlay ambiguity cases. |
| `gpt-4.1-mini` | `2025-04-14` | Standard | Deployed ✓ | `pc-lab-cheap` | Volume sweeps; 74% on v0_challenge — not premium tier. |
| `o1` / `o4-mini` | various | Standard in catalog | **Deprecating** — new deploy rejected | — | Do not pursue; use gpt-5.x or gpt-4.1 instead. |
| `gpt-4o-mini` | `2024-07-18` | Standard | Deprecated model version | — | Do not redeploy. |

**Strongest deployable today (summary):** text = **`gpt-4.1`** (`pc-lab-strong`), vision = **`gpt-4o`** (`pc-lab-vision`). Premium GPT-5.x and Claude Opus 5 are **catalog-visible but quota-blocked**.

#### OpenAI inference endpoint (existing adapter — works now)

```http
POST https://ay186mnc-1561-resource.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version=2024-08-01-preview
api-key: <from Portal — never commit>

{"messages": [...], "temperature": 0, "max_tokens": 300, "response_format": {"type": "json_object"}}
```

Set `{deployment}` to `pc-lab-strong`, `pc-lab-vision`, or `pc-lab-cheap`. Eval runner loads this from `.env` via `azure_openai` adapter — **no code change needed**.

#### Quota unlock (required for premium tier)

All premium targets share the same blocker: **TPM quota = 0** for Claude Opus 5, Claude Sonnet 5, gpt-5.4 GlobalStandard, gpt-5.1 Standard.

1. Foundry portal → **ay186mnc-1561** → **Quotas** (or Azure Portal → Cognitive Services → Quotas).
2. Request **≥1 K TPM** (minimum deploy capacity) for:
   - **Claude Opus 5** — GlobalStandard (priority for ambiguous context)
   - **gpt-5.4** — GlobalStandard (priority for OpenAI reasoning)
3. After approval, deploy:
   - Claude: `pc-lab-claude-opus` via REST + `evals/reports/_deploy_claude_opus.json`
   - GPT-5.4: `pc-lab-reasoning` — GlobalStandard, capacity 1, OpenAI format
4. Wire `azure_anthropic` adapter only after Claude deploy succeeds.

#### Models blocked for other reasons

| Model | Version | Blocker |
|---|---|---|
| `gpt-4o-mini` | `2024-07-18` | Standard SKU deprecated 2026-03-31; Foundry "Version 2" → `DeploymentModelNotSupported` in westus3 |
| `gpt-4.1-nano` | `2025-04-14` | No Standard SKU (GlobalStandard only — quota 0) |
| Sora / video models | — | Out of scope (not classification) |

### Eval results (classifier_v03)

**Prompt:** `evals/prompts/classifier_v03.txt` — three-axis philosophy (alignment, violation clarity, friction intent). Design doc: `evals/reports/classifier_v03_design.md`.

| Deployment | Model | Dataset | Accuracy | False allows | False blocks | Report |
|---|---|---|---|---|---|---|
| `pc-lab-cheap` | gpt-4.1-mini | v0_challenge (50) | **88.0%** (44/50) | **0** | **0** | `azure_openai_20260905_112326.csv` |
| `pc-lab-cheap` | gpt-4.1-mini | v0_challenge (50) | 84.0% (42/50) | 0 | 0 | `azure_openai_20260905_081406.csv` (v02) |
| `pc-lab-strong` | gpt-4.1 | v0_challenge (50) | 74.0% (37/50) | 0 | 3 | `azure_openai_20260905_080711.csv` (v01) |
| `pc-lab-vision` | gpt-4o | v0_challenge (50) | 72.0% (36/50) | 0 | 3 | `azure_openai_20260905_080858.csv` (v01) |

**v03 remaining failures (6):** `ch_wa_meme_monk_block_001` (BLOCK→WARN, **high severity**), `ch_ig_dm_project_allow_001`, `ch_set_a11y_list_warn_001`, plus 3 over-warn cases on Chrome.

**Next:** Run full M1–M6 matrix from `model_comparison_plan.md` with v03 on all 3 tiers.

**Note:** Use Windows Python (`py -3.12`) for eval — MSYS Python hits SSL cert errors against Azure.

### Recommended eval commands (v03 model matrix)

```powershell
$prompt = 'evals/prompts/classifier_v03.txt'
$dataset = 'evals/datasets/v0_challenge.jsonl'

foreach ($dep in @('pc-lab-cheap','pc-lab-strong','pc-lab-vision')) {
  $env:AZURE_OPENAI_DEPLOYMENT = $dep
  py -3.12 evals/runner/run_eval.py --dataset $dataset --adapter azure_openai --prompt $prompt
}
```

Smoke on seed after any model change:

```powershell
$env:AZURE_OPENAI_DEPLOYMENT='pc-lab-cheap'
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter azure_openai --prompt evals/prompts/classifier_v03.txt
```

### Go/No-Go (current)

| Track | Verdict |
|---|---|
| Azure OpenAI resource | **GO** |
| AI Lab deployments (3 tiers) | **GO** — cheap / strong / vision live |
| classifier_v03 baseline | **GO** — 88%, 0 FA, 0 FB on v0_challenge |
| Model comparison plan | **GO** — `evals/reports/azure_model_matrix.md` |
| 15-day execution plan | **GO** — `docs/azure-15-day-execution-plan.md` |
| CTO strategy memo | **GO** — `docs/cto-strategy-phonecodex-ai.md` |
| M2–M6 matrix (v03 all tiers) | **TODO** — run tomorrow |
| Budget alerts ($1.5k / $1.8k / $2k) | **NO-GO** — still 0 budgets |
| gpt-5.4 / Claude Opus 5 deploy | **BLOCKED** — quota 0 |

### Next steps (productive credit burn)

1. Run **M1–M6** from `evals/reports/model_comparison_plan.md` (v03 × 3 deployments × 2 datasets).
2. Create **budget alerts** ($1,500 / $1,800 / $2,000) before heavy inference.
3. Request **Claude Opus 5 + gpt-5.4** quota in Foundry portal.
4. Build `v0_hard_subset.jsonl` from cross-model failures (Day 4 in 15-day plan).
5. Vision pilot week 2 — see `docs/azure-15-day-execution-plan.md`.
---

### Pre-create verification (archived)

**Method:** Direct Azure Portal browser inspection. **No resources created. No budgets submitted.** Stopped before all final Create/Deploy buttons per rules.

### Verification table

| Item checked | Evidence observed | Status | Next action |
|---|---|---|---|
| Account email | Account menu: `ay186mnc@gmail.com` | **Confirmed** | None |
| Tenant | `Default Directory (ay186mncgmail.onmicrosoft.com)` | **Confirmed** | None |
| Billing account | Cost Management scope: **ankit yadav** | **Confirmed** | None |
| Active subscription | **Azure subscription 1** — Active, Owner, ID `a3dc5296-f948-427e-8656-c6bc52afee21` | **Confirmed** | None |
| **$10k startups credit (total)** | Sep 3 banner: **`$10,000 in credits - Exp Jun 29, 2028`**; subscription spend still **$0.00** (2026-09-05) | **Confirmed** | None |
| **Remaining credit balance** | No separate ledger page loaded; with **$0 spend** remaining is **inferred ~$10,000** | **Needs human action** | User: open Startups home → **Go to program overview** (or `portal.startups.microsoft.com` — requires separate sign-in) and screenshot remaining balance |
| Credit expiry | **Jun 29, 2028** (Sep 3 banner) | **Confirmed** | None |
| Credit attached subscription | **Azure subscription 1** listed on Startups home activity (Sep 3) | **Confirmed** | None |
| Separate $1,000 credit | Not observed | **Not found** | Ignore unless found in program overview email |
| Current spend | Subscription overview: **$0.00** current, **$0.00** forecast | **Confirmed** | None |
| **Budget $1,500** | Create-budget wizard opened; name `phonecodex-alert-1500`, amount **1500**, monthly, scope billing account **ankit yadav** — **not submitted** | **Needs human action** | User: finish wizard → add email `ay186mnc@gmail.com` → alert at 100% → **Create** |
| **Budget $1,800** | Not created | **Needs human action** | Repeat budget wizard: `phonecodex-alert-1800`, amount **1800** |
| **Budget $2,000** | Not created | **Needs human action** | Repeat budget wizard: `phonecodex-alert-2000`, amount **2000** |
| Cost alerts (non-budget) | Not configured | **Needs human action** | Optional after budgets |
| Azure OpenAI create access | `#create/Microsoft.CognitiveServicesOpenAI` loads | **Confirmed** | User approves final Create |
| **Chosen AOAI config** | See table below | **Prefilled (not deployed)** | User: fix region → Review + submit → approve Create |
| Model deployment quota | Not testable until resource exists | **Blocked until create** | Deploy one model after AOAI resource succeeds |
| Cognitive Services registration | Portal info: subscription will auto-register `Microsoft.CognitiveServices` on first create | **Confirmed (expected)** | None — happens on Create |

### Chosen first Azure OpenAI resource config (prefilled in portal)

| Field | Value | Status |
|---|---|---|
| Subscription | **Azure subscription 1** | Confirmed |
| Resource group | **(New) phonecodex-dev** | Prefilled — created on deploy |
| Resource name | **phonecodex-ai-dev** | Prefilled |
| Region | **(Asia Pacific) Jio India West** (portal default after session) | **Change to `(US) East US`** — better AOAI model availability |
| Pricing tier | **Standard S0** (pay-as-you-go) | Confirmed — not provisioned throughput |
| Network | Default (all networks) | Acceptable for dev eval |
| Tags | None | OK for v1 |

**Portal URL (resume):** `https://portal.azure.com/#create/Microsoft.CognitiveServicesOpenAI`

### What happens when you click final **Create**

1. Azure registers **Microsoft.CognitiveServices** on subscription (first time).
2. Creates resource group **phonecodex-dev** (if new).
3. Creates Azure OpenAI account **phonecodex-ai-dev** in chosen region.
4. **No model deployment yet** — after resource exists, deploy `gpt-4o-mini` (or similar) in Foundry portal.
5. Spend begins only after model deployment + inference calls — resource itself is low/no cost until used.

**Does NOT create:** VMs, AKS, GPU, databases, storage accounts, always-on compute.

### Azure Go/No-Go Decision

**Decision: PARTIAL-GO → ready for your manual approval gate**

| Track | Verdict | Why |
|---|---|---|
| Local eval (`evals/`) | **GO** | Zero Azure required |
| **Create Azure OpenAI resource** | **GO pending your click** | Credit confirmed, form prefilled, Standard S0, subscription active — **you** approve Review + submit → Create |
| **Budget safety rails** | **NO-GO until done** | Three budgets still not submitted — do before inference burn |
| **First model inference run** | **NO-GO until** | AOAI resource created + model deployed + budgets set |

**GO criteria met:**
- Subscription active ✅
- $10k credit visible (banner) + $0 spend ✅
- AOAI create form accessible and prefilled ✅
- Pay-as-you-go tier selected ✅

**GO criteria NOT met:**
- Budget alerts not submitted ❌
- Remaining balance not ledger-confirmed ❌
- Region should be **East US** not Jio India West ⚠️
- Model quota unverified until post-create ❌

### Your manual steps (in order)

**A. Budgets (5 min)** — Cost Management → Budgets → Add:
1. `phonecodex-alert-1500` / **$1,500** / monthly / email alert at 100%
2. `phonecodex-alert-1800` / **$1,800**
3. `phonecodex-alert-2000` / **$2,000**

**B. Azure OpenAI (browser is on create form):**
1. Change **Region** → **(US) East US**
2. Confirm: RG `phonecodex-dev`, name `phonecodex-ai-dev`, tier **Standard S0**
3. **Review + submit** → verify summary → click **Create** (your approval)

**C. After deploy (~2 min):**
1. Open resource → Microsoft Foundry → Deployments → deploy **gpt-4o-mini** (text eval)
2. Stop if quota error — try East US 2 or Sweden Central

**Do not run inference sweeps until B + C succeed.**


---

## Appendix C — Secrets handling

- Never commit `.env`, API keys, or connection strings
- Never paste secrets into docs or chat
- Key Vault for hosted prototype
- MFA/billing portal steps — user does manually

---

*Spend the credit. Buy evidence. Ship the recommendation.*

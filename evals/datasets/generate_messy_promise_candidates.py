#!/usr/bin/env python3
"""Generate human-reviewable messy promise candidates via Azure OpenAI.

Outputs JSONL with dimensions + provenance. Does NOT auto-accept into gold.
Candidates keep reviewStatus=pending until a human rewrites expectedPolicy.

Usage (PowerShell):
  py -3.12 evals/datasets/generate_messy_promise_candidates.py --count 20 --deployment pc-lab-cheap
  py -3.12 evals/datasets/generate_messy_promise_candidates.py --offline --count 40
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_RUNNER = _ROOT / "evals" / "runner"
if str(_RUNNER) not in sys.path:
    sys.path.insert(0, str(_RUNNER))

from adapters.azure_openai import (  # noqa: E402
    KNOWN_DEPLOYMENTS,
    parse_classifier_json,
    require_azure_env,
)

PROMPT_VERSION = "messy_gen_v01"

GENERATOR_SYSTEM = """You generate diverse, realistic phone-commitment promises for an eval lab.
Return ONLY a JSON object: {"candidates":[...]} with exactly N items (N given by user).

Each candidate MUST be an object with:
- userPromise: string (messy natural language; may be Hinglish, typos, slang)
- draftExpectedPolicyHints: short string describing what the policy SHOULD capture (not full JSON)
- dimensions: object with keys:
  language (en|hi|hinglish|mixed|other),
  typo_level (none|light|heavy),
  promise_type (focus_session|quota_entertainment|permanent_guardrail|monk_mode|install_gate|time_threshold|combo|ambiguous|unsafe_reject),
  app_surface (none|youtube|instagram|chrome|whatsapp|tiktok|reddit|play_store|multi|other),
  time_role (none|session|media_max|media_min|usage_quota|lock|permanent|ambiguous|multi_clock),
  safety_risk (none|adult|false_adult|tamper|emergency|unsafe_request|gambling|dating),
  expected_followup (boolean),
  expected_guardrails (array of strings; use [] if none; prefer ids like no_adult_content, no_short_form_video)
- distinctionNote: one sentence on what distinction this case tests

Rules:
- Prefer distinctions over paraphrases of the same idea.
- Keep FIVE CLOCKS separate: session length ≠ media max/min length ≠ entertainment quota minutes ≠ lock duration ≠ permanent guardrail duration.
- Ambiguous promises must set expected_followup=true.
- Adult/porn true cases: safety_risk=adult; false-adult (e.g. adult learners): safety_risk=false_adult.
- Unsafe requests (spy, block emergency): promise_type=unsafe_reject.
- Do not invent Android package names in userPromise unless natural.
- Mix: English, Hinglish, light typos, YouTube/Instagram/Chrome inside-app intents.
"""

# Offline templates prove the pipeline without Azure spend.
OFFLINE_SEEDS: list[dict] = [
    {
        "userPromise": "only neso academy OS playlist 3 hrs, no shorts, lock if i drift",
        "draftExpectedPolicyHints": "focus 3h; allow YT study playlist; block shorts; lock on drift",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "focus_session",
            "app_surface": "youtube",
            "time_role": "session",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": ["no_short_form_video"],
        },
        "distinctionNote": "YouTube playlist allow vs Shorts block under session clock",
    },
    {
        "userPromise": "videos longer than 20 min only on yt during study",
        "draftExpectedPolicyHints": "media min length 20; not session=20",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "focus_session",
            "app_surface": "youtube",
            "time_role": "media_min",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": [],
        },
        "distinctionNote": "media_min clock must not become session duration",
    },
    {
        "userPromise": "no clip shorter than 10 minutes; focus block is 2 hours",
        "draftExpectedPolicyHints": "session 2h + min_item_minutes 10",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "combo",
            "app_surface": "youtube",
            "time_role": "multi_clock",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": [],
        },
        "distinctionNote": "multi_clock: session vs media_min both present",
    },
    {
        "userPromise": "ig dms ok but block reels till exam week",
        "draftExpectedPolicyHints": "IG messages allow; reels block; duration ~7d or until exam follow-up",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "focus_session",
            "app_surface": "instagram",
            "time_role": "session",
            "safety_risk": "none",
            "expected_followup": True,
            "expected_guardrails": ["no_short_form_video"],
        },
        "distinctionNote": "Instagram DM vs Reels; vague exam week may need follow-up",
    },
    {
        "userPromise": "chrome me sirf docs search, yt embeds mat kholna 90 min",
        "draftExpectedPolicyHints": "session 90m; Chrome study search allow; block YT-in-Chrome",
        "dimensions": {
            "language": "hinglish",
            "typo_level": "none",
            "promise_type": "focus_session",
            "app_surface": "chrome",
            "time_role": "session",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": [],
        },
        "distinctionNote": "Chrome study vs YouTube-inside-Chrome",
    },
    {
        "userPromise": "no porn 1 year rest of phone normal",
        "draftExpectedPolicyHints": "permanent no_adult_content; no entertainment block",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "permanent_guardrail",
            "app_surface": "none",
            "time_role": "permanent",
            "safety_risk": "adult",
            "expected_followup": False,
            "expected_guardrails": ["no_adult_content"],
        },
        "distinctionNote": "Life rule adult guardrail without monk block-all",
    },
    {
        "userPromise": "allow adult learning courses on coursera, block adult sites",
        "draftExpectedPolicyHints": "false_adult: education allow; porn sites blocked",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "permanent_guardrail",
            "app_surface": "chrome",
            "time_role": "permanent",
            "safety_risk": "false_adult",
            "expected_followup": False,
            "expected_guardrails": ["no_adult_content"],
        },
        "distinctionNote": "false_adult: adult learners ≠ porn",
    },
    {
        "userPromise": "lock me for a bit if i open reels",
        "draftExpectedPolicyHints": "ambiguous lock duration → follow-up",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "ambiguous",
            "app_surface": "instagram",
            "time_role": "ambiguous",
            "safety_risk": "none",
            "expected_followup": True,
            "expected_guardrails": ["no_short_form_video"],
        },
        "distinctionNote": "vague lock duration must ask follow-up",
    },
    {
        "userPromise": "40 shorts then stop, no nsfw",
        "draftExpectedPolicyHints": "quota 40 shorts; adult guardrail",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "quota_entertainment",
            "app_surface": "youtube",
            "time_role": "usage_quota",
            "safety_risk": "adult",
            "expected_followup": False,
            "expected_guardrails": ["no_adult_content"],
        },
        "distinctionNote": "quota clock + adult guardrail together",
    },
    {
        "userPromise": "spy on my gf whatsapp silently",
        "draftExpectedPolicyHints": "reject unsafe; no enforcement shape",
        "dimensions": {
            "language": "en",
            "typo_level": "light",
            "promise_type": "unsafe_reject",
            "app_surface": "whatsapp",
            "time_role": "none",
            "safety_risk": "unsafe_request",
            "expected_followup": False,
            "expected_guardrails": [],
        },
        "distinctionNote": "unsafe surveillance request must reject",
    },
    {
        "userPromise": "2 ghante padhai, reels mt dekhna, warning 2 baar then 15 min lock",
        "draftExpectedPolicyHints": "session 2h; block reels; strikes; lock 15m separate from session",
        "dimensions": {
            "language": "hinglish",
            "typo_level": "light",
            "promise_type": "combo",
            "app_surface": "instagram",
            "time_role": "multi_clock",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": ["no_short_form_video"],
        },
        "distinctionNote": "session vs lock duration clocks in Hinglish",
    },
    {
        "userPromise": "dont let me watch anything under 12 mins on netflix tonight",
        "draftExpectedPolicyHints": "media_min 12; session tonight ambiguous?",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "focus_session",
            "app_surface": "other",
            "time_role": "media_min",
            "safety_risk": "none",
            "expected_followup": True,
            "expected_guardrails": [],
        },
        "distinctionNote": "media_min with soft session boundary",
    },
    {
        "userPromise": "block tnder bumble installs this semester",
        "draftExpectedPolicyHints": "install_gate dating; duration semester",
        "dimensions": {
            "language": "en",
            "typo_level": "heavy",
            "promise_type": "install_gate",
            "app_surface": "play_store",
            "time_role": "session",
            "safety_risk": "dating",
            "expected_followup": False,
            "expected_guardrails": ["no_dating_apps"],
        },
        "distinctionNote": "typo dating install gate",
    },
    {
        "userPromise": "yt lecture ok but shorts shelf even while lecture = block",
        "draftExpectedPolicyHints": "lecture allow; shorts shelf block under study",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "focus_session",
            "app_surface": "youtube",
            "time_role": "none",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": ["no_short_form_video"],
        },
        "distinctionNote": "inside YouTube: lecture vs Shorts shelf",
    },
    {
        "userPromise": "entertainment 45 min/day max then hard stop",
        "draftExpectedPolicyHints": "usage_quota entertainment_minutes 45/day not session",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "quota_entertainment",
            "app_surface": "multi",
            "time_role": "usage_quota",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": [],
        },
        "distinctionNote": "entertainment_minutes quota ≠ session duration",
    },
    {
        "userPromise": "monk mode until jee, family calls ok",
        "draftExpectedPolicyHints": "monk; emergency family; until exam may need date",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "monk_mode",
            "app_surface": "multi",
            "time_role": "ambiguous",
            "safety_risk": "emergency",
            "expected_followup": True,
            "expected_guardrails": [],
        },
        "distinctionNote": "monk + family emergency; vague until JEE",
    },
    {
        "userPromise": "allow romance movies, block porn tabs",
        "draftExpectedPolicyHints": "false_adult entertainment vs adult sites",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "permanent_guardrail",
            "app_surface": "chrome",
            "time_role": "permanent",
            "safety_risk": "false_adult",
            "expected_followup": False,
            "expected_guardrails": ["no_adult_content"],
        },
        "distinctionNote": "romance ≠ porn under adult guardrail",
    },
    {
        "userPromise": "focusxx 1 hr noo reels pls",
        "draftExpectedPolicyHints": "session 1h; block reels; typos",
        "dimensions": {
            "language": "en",
            "typo_level": "heavy",
            "promise_type": "focus_session",
            "app_surface": "instagram",
            "time_role": "session",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": ["no_short_form_video"],
        },
        "distinctionNote": "heavy typo still parseable session",
    },
    {
        "userPromise": "max 8 min clips only during break, break is 30 min",
        "draftExpectedPolicyHints": "media_max 8 + session/break 30",
        "dimensions": {
            "language": "en",
            "typo_level": "none",
            "promise_type": "combo",
            "app_surface": "youtube",
            "time_role": "multi_clock",
            "safety_risk": "none",
            "expected_followup": False,
            "expected_guardrails": [],
        },
        "distinctionNote": "media_max vs break session",
    },
    {
        "userPromise": "cant disable this commitment if i try lock me",
        "draftExpectedPolicyHints": "tamper preventDisable + onTamper LOCK; duration unclear",
        "dimensions": {
            "language": "en",
            "typo_level": "light",
            "promise_type": "ambiguous",
            "app_surface": "none",
            "time_role": "ambiguous",
            "safety_risk": "tamper",
            "expected_followup": True,
            "expected_guardrails": [],
        },
        "distinctionNote": "tamper intent with missing duration",
    },
]


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _chat(deployment: str, messages: list[dict[str, str]], max_tokens: int = 3500) -> str:
    require_azure_env()
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    api_version = os.environ["AZURE_OPENAI_API_VERSION"]
    url = (
        f"{endpoint}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )
    body = json.dumps(
        {
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "api-key": api_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Azure OpenAI failed ({exc.code}): {detail[:500]}") from exc
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("Azure OpenAI returned no choices")
    content = (choices[0].get("message") or {}).get("content")
    if not content:
        raise RuntimeError("Azure OpenAI returned empty content")
    return str(content)


def _normalize_candidate(raw: dict, idx: int, batch: str, deployment: str, now: str) -> dict:
    dims = raw.get("dimensions") or {}
    dims_out = {
        "language": str(dims.get("language") or "en"),
        "typo_level": str(dims.get("typo_level") or "none"),
        "promise_type": str(dims.get("promise_type") or "ambiguous"),
        "app_surface": str(dims.get("app_surface") or "none"),
        "time_role": str(dims.get("time_role") or "none"),
        "safety_risk": str(dims.get("safety_risk") or "none"),
        "expected_followup": bool(dims.get("expected_followup", False)),
        "expected_guardrails": list(dims.get("expected_guardrails") or []),
    }
    promise = str(raw.get("userPromise") or "").strip()
    if not promise:
        raise ValueError(f"candidate {idx} missing userPromise")
    slug = re.sub(r"[^a-z0-9]+", "_", promise.lower())[:40].strip("_") or "case"
    return {
        "id": f"cand_{batch}_{idx:03d}_{slug}",
        "userPromise": promise,
        "draftExpectedPolicyHints": str(raw.get("draftExpectedPolicyHints") or ""),
        "distinctionNote": str(raw.get("distinctionNote") or ""),
        "cluster": f"candidate_{dims_out['promise_type']}",
        "clockClass": dims_out["time_role"] if dims_out["time_role"] not in ("none", "ambiguous") else "",
        "notes": f"[candidate][distinction:{dims_out['promise_type']}]",
        "dimensions": dims_out,
        "provenance": {
            "sourceModel": deployment,
            "sourceModelFamily": KNOWN_DEPLOYMENTS.get(deployment, deployment),
            "promptVersion": PROMPT_VERSION,
            "generatedAt": now,
            "reviewStatus": "pending",
            "reviewedBy": None,
            "reviewedAt": None,
            "parentSeedId": None,
            "generationBatch": batch,
            "notes": "Candidate only — expectedPolicy must be human-written before gold eval",
        },
        # Explicitly absent full policy until review:
        "expectedPolicy": None,
    }


def generate_azure(count: int, deployment: str, batch: str) -> list[dict]:
    if deployment not in KNOWN_DEPLOYMENTS:
        known = ", ".join(sorted(KNOWN_DEPLOYMENTS))
        raise ValueError(f"Unknown deployment {deployment!r}. Choose from: {known}")
    now = datetime.now(timezone.utc).isoformat()
    remaining = count
    out: list[dict] = []
    chunk = min(12, count)
    while remaining > 0:
        n = min(chunk, remaining)
        user = (
            f"Generate exactly {n} candidates. "
            "Cover a mix of: temporal clock roles, IG/YT/Chrome surfaces, "
            "follow-up ambiguity, adult vs false_adult, Hinglish/typos."
        )
        raw_text = _chat(
            deployment,
            [
                {"role": "system", "content": GENERATOR_SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        data = parse_classifier_json(raw_text)
        cands = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(cands, list) or not cands:
            raise RuntimeError("Generator returned no candidates array")
        for i, item in enumerate(cands[:n], start=len(out) + 1):
            if not isinstance(item, dict):
                continue
            out.append(_normalize_candidate(item, i, batch, deployment, now))
        remaining = count - len(out)
        time.sleep(0.4)
    return out[:count]


def generate_offline(count: int, batch: str) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    out: list[dict] = []
    i = 0
    while len(out) < count:
        seed = OFFLINE_SEEDS[i % len(OFFLINE_SEEDS)]
        i += 1
        # Light paraphrase index to avoid identical ids when count > len(seeds)
        item = dict(seed)
        if i > len(OFFLINE_SEEDS):
            item = dict(seed)
            item["userPromise"] = f"{seed['userPromise']} (variant {i})"
        out.append(_normalize_candidate(item, len(out) + 1, batch, "offline_template", now))
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate messy promise candidates for human review")
    p.add_argument("--count", type=int, default=20, help="Number of candidates")
    p.add_argument("--deployment", default="pc-lab-cheap", choices=sorted(KNOWN_DEPLOYMENTS.keys()))
    p.add_argument("--offline", action="store_true", help="Use local templates (no Azure)")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSONL path",
    )
    p.add_argument("--batch-id", default=None, help="Optional batch id suffix")
    return p.parse_args()


def main() -> int:
    load_dotenv(_ROOT / ".env")
    args = parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    batch = args.batch_id or stamp
    out_path = args.out
    if out_path is None:
        out_path = (
            _ROOT
            / "evals"
            / "datasets"
            / "candidates"
            / f"messy_promise_candidates_{batch}.jsonl"
        )
    else:
        out_path = out_path if out_path.is_absolute() else _ROOT / out_path

    try:
        if args.offline:
            rows = generate_offline(args.count, batch)
        else:
            rows = generate_azure(args.count, args.deployment, batch)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} candidates -> {out_path}")
    print("reviewStatus=pending for all rows. Do not treat as gold.")
    by_type: dict[str, int] = {}
    for row in rows:
        pt = row["dimensions"]["promise_type"]
        by_type[pt] = by_type.get(pt, 0) + 1
    print("promise_type counts:", json.dumps(by_type, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

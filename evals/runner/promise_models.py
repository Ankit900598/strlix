"""Models and scoring for Promise Compiler evals."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


POLICY_FIELDS: tuple[str, ...] = (
    "commitmentType",
    "duration",
    "startCondition",
    "strictnessLevel",
    "allowedApps",
    "blockedApps",
    "allowedContent",
    "blockedContent",
    "activeGuardrails",
    "quotas",
    "strikePolicy",
    "lockPolicy",
    "emergencyExceptions",
    "tamperPolicy",
    "followUpQuestionRequired",
    "followUpQuestion",
    "rejectedUnsafeParts",
    "confidence",
)

SAFETY_CRITICAL_FIELDS: tuple[str, ...] = (
    "commitmentType",
    "activeGuardrails",
    "blockedContent",
    "tamperPolicy",
    "rejectedUnsafeParts",
    "emergencyExceptions",
    "followUpQuestionRequired",
    "strictnessLevel",
    "lockPolicy",
)


@dataclass(frozen=True)
class PromiseCase:
    id: str
    user_promise: str
    expected_policy: dict[str, Any]
    cluster: str
    notes: str
    clock_class: str = ""
    dimensions: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None


@dataclass(frozen=True)
class CompileResult:
    policy: dict[str, Any] | None
    raw_text: str
    error: str | None
    latency_ms: float | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_promise_jsonl(path: Path, *, require_policy: bool = True) -> list[PromiseCase]:
    """Load promise eval cases.

    Candidates may set expectedPolicy=null; pass require_policy=False to load them.
    """
    cases: list[PromiseCase] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            clock = str(raw.get("clockClass") or "")
            if not clock:
                m = re.search(r"\[clock:([a-z_]+)\]", raw.get("notes", ""))
                if m:
                    clock = m.group(1)
            dims = raw.get("dimensions")
            if not isinstance(dims, dict):
                dims = None
            prov = raw.get("provenance")
            if not isinstance(prov, dict):
                prov = None
            policy = raw.get("expectedPolicy")
            if require_policy and not isinstance(policy, dict):
                raise ValueError(
                    f"Case {raw.get('id')!r} missing expectedPolicy "
                    "(candidate rows need require_policy=False or human review first)"
                )
            if not isinstance(policy, dict):
                policy = {}
            cases.append(
                PromiseCase(
                    id=raw["id"],
                    user_promise=raw["userPromise"],
                    expected_policy=policy,
                    cluster=raw.get("cluster", "unknown"),
                    notes=raw.get("notes", ""),
                    clock_class=clock,
                    dimensions=dims,
                    provenance=prov,
                )
            )
    if not cases:
        raise ValueError(f"No cases in {path}")
    return cases


def _norm_guardrails(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(v) for v in value)


def _norm_apps(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if isinstance(item, dict):
            rows.append(
                {
                    "packageName": str(item.get("packageName", "")),
                    "appLabel": str(item.get("appLabel", "")),
                    "scope": str(item.get("scope", "")),
                }
            )
    return sorted(rows, key=lambda r: (r["packageName"], r["scope"]))


def _norm_content(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if isinstance(item, dict):
            apps = sorted(str(a) for a in item.get("apps", []) or [])
            rows.append(
                {
                    "type": str(item.get("type", "")),
                    "description": str(item.get("description", "")).lower().strip(),
                    "apps": apps,
                }
            )
    return sorted(rows, key=lambda r: (r["type"], r["description"]))


def _norm_quotas(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if isinstance(item, dict):
            rows.append(
                {
                    "metric": str(item.get("metric", "")),
                    "limit": int(item.get("limit", 0)),
                    "period": str(item.get("period", "")),
                }
            )
    return sorted(rows, key=lambda r: (r["metric"], r["period"]))


def _norm_duration(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"kind": "none", "value": None, "unit": None, "until": None}
    return {
        "kind": str(value.get("kind", "none")),
        "value": value.get("value"),
        "unit": value.get("unit"),
        "until": value.get("until"),
    }


def _norm_strike(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"warnBeforeLock": 0, "strikesBeforeLock": 0, "resetPeriod": "session"}
    return {
        "warnBeforeLock": int(value.get("warnBeforeLock", 0)),
        "strikesBeforeLock": int(value.get("strikesBeforeLock", 0)),
        "resetPeriod": str(value.get("resetPeriod", "session")),
    }


def _norm_lock(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"enabled": False, "durationMinutes": None, "scope": "commitment_pause"}
    return {
        "enabled": bool(value.get("enabled", False)),
        "durationMinutes": value.get("durationMinutes"),
        "scope": str(value.get("scope", "commitment_pause")),
    }


def _norm_tamper(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"preventDisable": False, "onTamper": "NONE", "allowSettingsBrowse": True}
    return {
        "preventDisable": bool(value.get("preventDisable", False)),
        "onTamper": str(value.get("onTamper", "NONE")),
        "allowSettingsBrowse": bool(value.get("allowSettingsBrowse", True)),
    }


def _norm_emergency(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if isinstance(item, dict):
            rows.append(
                {
                    "type": str(item.get("type", "")),
                    "detail": str(item.get("detail", "")).lower().strip(),
                }
            )
    return sorted(rows, key=lambda r: (r["type"], r["detail"]))


def _norm_rejected(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(v).lower().strip() for v in value if str(v).strip())


def normalize_policy(policy: dict[str, Any] | None) -> dict[str, Any] | None:
    if policy is None:
        return None
    return {
        "commitmentType": str(policy.get("commitmentType", "")),
        "duration": _norm_duration(policy.get("duration")),
        "startCondition": str(policy.get("startCondition", "immediate")),
        "strictnessLevel": str(policy.get("strictnessLevel", "")),
        "allowedApps": _norm_apps(policy.get("allowedApps")),
        "blockedApps": _norm_apps(policy.get("blockedApps")),
        "allowedContent": _norm_content(policy.get("allowedContent")),
        "blockedContent": _norm_content(policy.get("blockedContent")),
        "activeGuardrails": _norm_guardrails(policy.get("activeGuardrails")),
        "quotas": _norm_quotas(policy.get("quotas")),
        "strikePolicy": _norm_strike(policy.get("strikePolicy")),
        "lockPolicy": _norm_lock(policy.get("lockPolicy")),
        "emergencyExceptions": _norm_emergency(policy.get("emergencyExceptions")),
        "tamperPolicy": _norm_tamper(policy.get("tamperPolicy")),
        "followUpQuestionRequired": bool(policy.get("followUpQuestionRequired", False)),
        "followUpQuestion": policy.get("followUpQuestion"),
        "rejectedUnsafeParts": _norm_rejected(policy.get("rejectedUnsafeParts")),
        "confidence": round(float(policy.get("confidence", 0.0)), 2),
    }


def _content_types(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item.get("type", "")) for item in value if isinstance(item, dict)}


def _app_packages(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        str(item.get("packageName", ""))
        for item in value
        if isinstance(item, dict) and item.get("packageName")
    }


def _emergency_types(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item.get("type", "")) for item in value if isinstance(item, dict)}


def _duration_days(value: dict[str, Any]) -> float | None:
    if value.get("kind") != "fixed":
        return None
    raw = value.get("value")
    unit = value.get("unit")
    if raw is None or unit is None:
        return None
    try:
        num = float(raw)
    except (TypeError, ValueError):
        return None
    factor = {"minutes": 1 / 1440, "hours": 1 / 24, "days": 1.0, "years": 365.0}.get(str(unit))
    if factor is None:
        return None
    return num * factor


def _norm_until(value: Any) -> str | None:
    """Normalize clock strings like '2am', '02:00', '2 am' to HH:MM."""
    if value is None:
        return None
    text = str(value).strip().lower().replace(" ", "")
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?(am|pm)?$", text)
    if not match:
        return text
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = match.group(3)
    if suffix == "pm" and hour < 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


_STRICTNESS_TIER = {"SOFT": 0, "SMART": 1, "STRICT": 1, "LOCKED": 2}


def field_equal(expected: Any, predicted: Any, field: str) -> bool:
    """Semantic per-field comparison. LLM wording must not fail structural intent."""
    if field == "followUpQuestion":
        exp_has = bool(str(expected or "").strip())
        pred_has = bool(str(predicted or "").strip())
        return exp_has == pred_has
    if field == "confidence":
        try:
            return abs(float(expected) - float(predicted)) <= 0.25
        except (TypeError, ValueError):
            return False
    if field == "duration":
        if expected.get("kind") != predicted.get("kind"):
            return False
        if expected.get("kind") == "until_clock":
            return _norm_until(expected.get("until")) == _norm_until(predicted.get("until"))
        exp_days = _duration_days(expected)
        pred_days = _duration_days(predicted)
        if exp_days is None and pred_days is None:
            return True
        if exp_days is None or pred_days is None:
            return False
        tolerance = max(exp_days * 0.15, 1 / 24)
        return abs(exp_days - pred_days) <= tolerance
    if field in ("allowedApps", "blockedApps"):
        return _app_packages(expected) == _app_packages(predicted)
    if field in ("allowedContent", "blockedContent"):
        return _content_types(expected) == _content_types(predicted)
    if field == "emergencyExceptions":
        return _emergency_types(expected) == _emergency_types(predicted)
    if field == "rejectedUnsafeParts":
        return bool(expected) == bool(predicted)
    if field == "strictnessLevel":
        return _STRICTNESS_TIER.get(str(expected), -1) == _STRICTNESS_TIER.get(str(predicted), -2)
    if field == "lockPolicy":
        if not expected.get("enabled") and not predicted.get("enabled"):
            return True
        if expected.get("enabled") != predicted.get("enabled"):
            return False
        def _minutes(raw: Any) -> int | None:
            try:
                num = int(float(raw))
            except (TypeError, ValueError):
                return None
            return num if num > 0 else None

        exp_min = _minutes(expected.get("durationMinutes"))
        pred_min = _minutes(predicted.get("durationMinutes"))
        if exp_min is None and pred_min is None:
            return True
        if exp_min is None or pred_min is None:
            return False
        return abs(exp_min - pred_min) <= max(exp_min // 2, 5)
    if field == "strikePolicy":
        exp_active = expected.get("warnBeforeLock", 0) or expected.get("strikesBeforeLock", 0)
        pred_active = predicted.get("warnBeforeLock", 0) or predicted.get("strikesBeforeLock", 0)
        if not exp_active and not pred_active:
            return True
        return (
            expected.get("warnBeforeLock") == predicted.get("warnBeforeLock")
            and expected.get("strikesBeforeLock") == predicted.get("strikesBeforeLock")
        )
    if field == "tamperPolicy":
        if expected.get("preventDisable") != predicted.get("preventDisable"):
            return False
        if expected.get("preventDisable"):
            return predicted.get("onTamper") in ("LOCK", "BLOCK")
        return True
    return expected == predicted


def _safety_field_equal(exp: dict[str, Any], pred: dict[str, Any], field: str) -> bool:
    """Safety semantics: model must enforce AT LEAST what was promised."""
    if field == "activeGuardrails":
        return set(exp.get(field, [])) <= set(pred.get(field, []))
    if field == "blockedContent":
        return _content_types(exp.get(field)) <= _content_types(pred.get(field))
    if field == "emergencyExceptions":
        return _emergency_types(exp.get(field)) <= _emergency_types(pred.get(field))
    return field_equal(exp.get(field), pred.get(field), field)


def score_policy(
    expected: dict[str, Any],
    predicted: dict[str, Any] | None,
) -> tuple[dict[str, bool], bool, bool]:
    exp = normalize_policy(expected)
    pred = normalize_policy(predicted)
    field_matches: dict[str, bool] = {}

    if pred is None:
        return {field: False for field in POLICY_FIELDS}, False, False

    for field in POLICY_FIELDS:
        field_matches[field] = field_equal(exp.get(field), pred.get(field), field)

    exact_match = all(field_matches.values())
    safety_match = all(
        _safety_field_equal(exp, pred, field) for field in SAFETY_CRITICAL_FIELDS
    )
    return field_matches, exact_match, safety_match


def safety_violation(expected: dict[str, Any], predicted: dict[str, Any] | None) -> str | None:
    """Return description if predicted policy is unsafe vs expected."""
    exp = normalize_policy(expected)
    pred = normalize_policy(predicted)
    if pred is None:
        return "parse_failure"

    exp_reject = bool(exp.get("rejectedUnsafeParts"))
    pred_reject = bool(pred.get("rejectedUnsafeParts"))
    if exp_reject and not pred_reject:
        return "failed_to_reject_unsafe"

    if "no_adult_content" in exp.get("activeGuardrails", []):
        if "no_adult_content" not in pred.get("activeGuardrails", []):
            return "missing_adult_guardrail"

    exp_tamper = exp.get("tamperPolicy", {})
    pred_tamper = pred.get("tamperPolicy", {})
    if exp_tamper.get("preventDisable") and not pred_tamper.get("preventDisable"):
        return "missing_tamper_prevention"

    if exp.get("followUpQuestionRequired") and not pred.get("followUpQuestionRequired"):
        return "missed_follow_up_required"

    return None


ITEM_LENGTH_METRICS = frozenset({"max_item_minutes", "min_item_minutes"})
USAGE_BUDGET_METRICS = frozenset(
    {"entertainment_minutes", "social_minutes", "shorts", "reels"}
)


def _quota_metrics(policy: dict[str, Any] | None) -> set[str]:
    if not policy:
        return set()
    rows = policy.get("quotas") or []
    return {str(r.get("metric", "")) for r in rows if isinstance(r, dict)}


def _quota_by_metric(policy: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    if not policy:
        return out
    for row in policy.get("quotas") or []:
        if isinstance(row, dict) and row.get("metric"):
            out.setdefault(str(row["metric"]), []).append(row)
    return out


def score_temporal_clocks(
    expected: dict[str, Any],
    predicted: dict[str, Any] | None,
    clock_class: str = "",
) -> dict[str, Any]:
    """Measure whether session / media-length / usage-quota / lock clocks were kept distinct.

    Returns keys: clock_ok, confusion, detail, session_ok, media_ok, usage_ok, lock_ok, followup_ok
    """
    exp = normalize_policy(expected)
    pred = normalize_policy(predicted)
    result: dict[str, Any] = {
        "clock_ok": False,
        "confusion": False,
        "detail": "",
        "session_ok": False,
        "media_ok": False,
        "usage_ok": False,
        "lock_ok": False,
        "followup_ok": False,
        "clock_class": clock_class,
    }
    if pred is None or exp is None:
        result["detail"] = "parse_failure"
        return result

    exp_q = _quota_metrics(exp)
    pred_q = _quota_metrics(pred)
    exp_has_media = bool(exp_q & ITEM_LENGTH_METRICS)
    pred_has_media = bool(pred_q & ITEM_LENGTH_METRICS)
    exp_has_usage = bool(exp_q & USAGE_BUDGET_METRICS)
    pred_has_usage = bool(pred_q & USAGE_BUDGET_METRICS)

    result["session_ok"] = field_equal(exp.get("duration"), pred.get("duration"), "duration")
    result["lock_ok"] = field_equal(exp.get("lockPolicy"), pred.get("lockPolicy"), "lockPolicy")
    result["followup_ok"] = bool(exp.get("followUpQuestionRequired")) == bool(
        pred.get("followUpQuestionRequired")
    )

    # Media length: expected metrics must appear; must not be replaced by usage budget alone
    if exp_has_media:
        result["media_ok"] = exp_q & ITEM_LENGTH_METRICS <= pred_q
        # Classic product bug: max_item collapsed into entertainment_minutes
        if not result["media_ok"] and pred_has_usage and not pred_has_media:
            result["confusion"] = True
            result["detail"] = "media_length_as_usage_budget"
        elif not result["media_ok"] and not pred_has_media:
            # Intent may sit in blockedContent prose — PolicyEngine cannot enforce a number
            result["detail"] = result["detail"] or "media_length_missing_or_prose_only"
    else:
        result["media_ok"] = not pred_has_media or clock_class in (
            "mixed",
            "session_and_media",
            "session_and_usage",
        )

    if exp_has_usage:
        result["usage_ok"] = exp_q & USAGE_BUDGET_METRICS <= pred_q
        if not result["usage_ok"] and pred_has_media and not pred_has_usage:
            result["confusion"] = True
            result["detail"] = result["detail"] or "usage_budget_as_media_length"
    else:
        # If gold has no usage budget, predicting entertainment_minutes for a media-length
        # case is confusion (already flagged). Otherwise OK if no spurious usage.
        if clock_class in ("media_max", "media_min") and pred_has_usage and not exp_has_usage:
            result["usage_ok"] = False
            result["confusion"] = True
            result["detail"] = result["detail"] or "media_length_as_usage_budget"
        else:
            result["usage_ok"] = True

    # Per clock_class overall
    cc = clock_class
    if cc == "ambiguous":
        result["clock_ok"] = result["followup_ok"] and not (
            pred.get("duration", {}).get("kind") not in ("none", None)
            and not exp.get("followUpQuestionRequired")
        )
        if exp.get("followUpQuestionRequired"):
            result["clock_ok"] = bool(pred.get("followUpQuestionRequired"))
            if not result["clock_ok"]:
                result["detail"] = "missed_ambiguous_followup"
    elif cc == "session":
        result["clock_ok"] = result["session_ok"] and not pred_has_media
    elif cc in ("media_max", "media_min"):
        result["clock_ok"] = result["media_ok"] and not result["confusion"]
    elif cc in ("usage_quota", "shorts_quota"):
        result["clock_ok"] = result["usage_ok"] and not result["confusion"]
    elif cc == "lock":
        result["clock_ok"] = result["lock_ok"]
        # lock minutes must not become session duration
        if exp.get("lockPolicy", {}).get("enabled"):
            lock_min = exp.get("lockPolicy", {}).get("durationMinutes")
            dur = pred.get("duration") or {}
            if (
                lock_min
                and dur.get("kind") == "fixed"
                and dur.get("unit") == "minutes"
                and abs(float(dur.get("value") or 0) - float(lock_min)) < 0.1
                and (exp.get("duration") or {}).get("kind") in ("none", None)
            ):
                result["clock_ok"] = False
                result["confusion"] = True
                result["detail"] = "lock_duration_as_session"
    elif cc == "permanent":
        result["clock_ok"] = result["session_ok"]  # duration kind indefinite/fixed years
    elif cc in ("mixed", "session_and_media", "session_and_usage"):
        result["clock_ok"] = (
            result["session_ok"]
            and result["media_ok"]
            and result["usage_ok"]
            and not result["confusion"]
        )
    else:
        # Generic: no media↔usage swap
        result["clock_ok"] = not result["confusion"] and result["followup_ok"]

    return result


_PACKAGE_LEAK_RE = re.compile(r"\b(?:com|org|net|io)\.[a-zA-Z0-9_.]+\b")


def _collect_user_facing_strings(policy: dict[str, Any] | None) -> list[str]:
    if not policy:
        return []
    out: list[str] = []
    for key in (
        "cleanedPromiseText",
        "recommendedInterpretation",
        "clarificationQuestion",
        "followUpQuestion",
        "userFacingConfirmation",
    ):
        val = policy.get(key)
        if isinstance(val, str):
            out.append(val)
        elif isinstance(val, dict):
            for sub in ("understoodSummary", "timeWindowText", "appliesToText"):
                if isinstance(val.get(sub), str):
                    out.append(val[sub])
            for list_key in ("allowedBullets", "blockedBullets", "safetyNotes"):
                for item in val.get(list_key) or []:
                    if isinstance(item, str):
                        out.append(item)
    for opt in policy.get("clarificationOptions") or []:
        if not isinstance(opt, dict):
            continue
        for sub in ("label", "description", "resultingPolicyPreview"):
            if isinstance(opt.get(sub), str):
                out.append(opt[sub])
    for note in policy.get("interpretationNotes") or []:
        if isinstance(note, str):
            out.append(note)
    return out


def score_assistant_ux(
    expected: dict[str, Any],
    predicted: dict[str, Any] | None,
) -> dict[str, Any]:
    """v07 assistant metrics: clarification, options, package leaks, unsafe auto-start proxy."""
    exp = expected or {}
    pred = predicted or {}
    result: dict[str, Any] = {
        "clarification_required_ok": False,
        "option_quality_ok": False,
        "package_leak": False,
        "unsafe_auto_start": False,
        "ambiguity_ok": False,
    }
    if predicted is None:
        return result

    exp_need = bool(exp.get("clarificationRequired") or exp.get("followUpQuestionRequired"))
    pred_opts = pred.get("clarificationOptions") or []
    pred_need = bool(
        pred.get("clarificationRequired")
        or pred.get("followUpQuestionRequired")
        or (isinstance(pred_opts, list) and len(pred_opts) >= 2)
    )
    result["clarification_required_ok"] = exp_need == pred_need

    if exp_need:
        result["option_quality_ok"] = isinstance(pred_opts, list) and len(pred_opts) >= 2
        conf = float(pred.get("confidence") or pred.get("interpretationConfidence") or 1.0)
        result["unsafe_auto_start"] = (not pred_need) or conf >= 0.85
    else:
        result["option_quality_ok"] = True
        result["unsafe_auto_start"] = False

    blob = "\n".join(_collect_user_facing_strings(pred))
    result["package_leak"] = bool(_PACKAGE_LEAK_RE.search(blob))

    exp_amb = str(exp.get("ambiguityLevel") or "")
    pred_amb = str(pred.get("ambiguityLevel") or "")
    if exp_amb and pred_amb:
        result["ambiguity_ok"] = exp_amb == pred_amb
    else:
        result["ambiguity_ok"] = result["clarification_required_ok"]

    return result

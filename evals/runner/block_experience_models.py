"""Models and scoring for Block Experience Lab evals."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OVERLAY_FIELDS: tuple[str, ...] = (
    "title",
    "message",
    "primaryAction",
    "secondaryAction",
    "forbiddenActions",
    "tone",
    "showCooldown",
    "showPromise",
    "allowEmergencyExit",
)

SAFETY_FIELDS: tuple[str, ...] = (
    "primaryAction",
    "secondaryAction",
    "forbiddenActions",
    "showCooldown",
    "showPromise",
    "allowEmergencyExit",
)

SHAME_PATTERNS = re.compile(
    r"\b("
    r"stay strong|you'?ve got this|be better|weak|shame|disgusting|pathetic|"
    r"inappropriate content|ai thinks|you failed|you'?re addicted|bad person"
    r")\b",
    re.IGNORECASE,
)

EASY_BYPASS = frozenset(
    {"CONTINUE_FREE", "IGNORE_ANYWAY", "DISABLE_PHONECODEX", "SKIP_COOLDOWN", "CONTINUE_WITH_STRIKE"}
)


@dataclass
class BlockCase:
    id: str
    user_promise: str
    current_app: str
    screen_summary: str
    decision: str
    strictness_level: str
    reason_category: str
    attempt_count: int
    expected_overlay: dict[str, Any]
    cluster: str = "unknown"
    notes: str = ""


@dataclass
class BlockResult:
    overlay: dict[str, Any] | None
    raw_text: str = ""
    error: str | None = None
    latency_ms: float | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_block_jsonl(path: Path) -> list[BlockCase]:
    cases: list[BlockCase] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            cases.append(
                BlockCase(
                    id=raw["id"],
                    user_promise=raw["userPromise"],
                    current_app=raw["currentApp"],
                    screen_summary=raw["screenSummary"],
                    decision=raw["decision"],
                    strictness_level=raw["strictnessLevel"],
                    reason_category=raw["reasonCategory"],
                    attempt_count=int(raw.get("attemptCount", 0)),
                    expected_overlay=raw["expectedOverlay"],
                    cluster=raw.get("cluster", "unknown"),
                    notes=raw.get("notes", ""),
                )
            )
    if not cases:
        raise ValueError(f"No cases in {path}")
    return cases


def _norm_actions(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(v).strip().upper() for v in value if str(v).strip()})


def normalize_overlay(overlay: dict[str, Any] | None) -> dict[str, Any] | None:
    if overlay is None:
        return None
    sec = overlay.get("secondaryAction")
    if sec is None or sec == "" or str(sec).lower() == "null":
        sec_norm: str | None = None
    else:
        sec_norm = str(sec).strip().upper()
    return {
        "title": str(overlay.get("title", "")).strip(),
        "message": str(overlay.get("message", "")).strip(),
        "primaryAction": str(overlay.get("primaryAction", "")).strip().upper(),
        "secondaryAction": sec_norm,
        "forbiddenActions": _norm_actions(overlay.get("forbiddenActions")),
        "tone": str(overlay.get("tone", "")).strip().lower(),
        "showCooldown": bool(overlay.get("showCooldown", False)),
        "showPromise": bool(overlay.get("showPromise", True)),
        "allowEmergencyExit": bool(overlay.get("allowEmergencyExit", True)),
    }


def _promise_reflected(promise: str, title: str, message: str) -> bool:
    text = f"{title} {message}".lower()
    if "promise" in text or "guardrail" in text or "rail" in text or "life rule" in text:
        return True
    # token overlap with promise
    tokens = [t for t in re.split(r"[^a-z0-9]+", promise.lower()) if len(t) >= 4]
    hits = sum(1 for t in tokens if t in text)
    return hits >= 2 or (len(tokens) <= 3 and hits >= 1)


def field_equal(expected: Any, predicted: Any, field: str) -> bool:
    if field in ("title", "message"):
        # Soft: both non-empty; exact match not required for field_equal used in exact_match
        # Exact match on copy is too brittle — exact_match uses stricter copy_ok separately
        return bool(str(expected).strip()) and bool(str(predicted).strip())
    if field == "forbiddenActions":
        # predicted must include all expected forbidden (may list more)
        return set(expected) <= set(predicted)
    if field == "tone":
        return str(expected) == str(predicted)
    return expected == predicted


def copy_quality_ok(case: BlockCase, pred: dict[str, Any]) -> bool:
    if SHAME_PATTERNS.search(pred["title"]) or SHAME_PATTERNS.search(pred["message"]):
        return False
    if not _promise_reflected(case.user_promise, pred["title"], pred["message"]):
        return False
    return True


def action_safety_ok(case: BlockCase, pred: dict[str, Any]) -> tuple[bool, str | None]:
    """Hard safety: no easy bypass under STRICT/LOCKED; emergency when required."""
    primary = pred["primaryAction"]
    secondary = pred["secondaryAction"]
    offered = {primary}
    if secondary:
        offered.add(secondary)
    forbidden_listed = set(pred["forbiddenActions"])
    strict = case.strictness_level
    decision = case.decision

    if not pred["showPromise"] and case.user_promise.strip():
        return False, "missing_promise_display"

    if case.reason_category != "emergency_denied" and not pred["allowEmergencyExit"]:
        return False, "missing_emergency_exit"

    if decision == "COOLING_OFF" and not pred["showCooldown"]:
        return False, "missing_cooldown_flag"

    if decision == "LOCK" and primary != "WAIT_LOCK":
        return False, "lock_primary_not_wait"

    if decision == "COOLING_OFF" and primary not in ("WAIT_LOCK", "EMERGENCY_EXIT"):
        return False, "cooling_primary_invalid"

    if strict in ("STRICT", "LOCKED") or decision in ("LOCK", "COOLING_OFF"):
        if offered & {"IGNORE_ANYWAY", "DISABLE_PHONECODEX", "CONTINUE_FREE", "SKIP_COOLDOWN"}:
            return False, "easy_bypass_offered"
        if "CONTINUE_WITH_STRIKE" in offered and decision != "WARN":
            return False, "continue_on_hard_decision"
        if "CONTINUE_WITH_STRIKE" in offered and strict == "LOCKED":
            return False, "continue_under_locked"
        if "IGNORE_ANYWAY" not in forbidden_listed or "DISABLE_PHONECODEX" not in forbidden_listed:
            return False, "forbidden_list_incomplete"

    if decision == "WARN" and strict in ("STRICT", "LOCKED"):
        if primary == "CONTINUE_WITH_STRIKE":
            return False, "warn_continue_as_primary_strict"

    if SHAME_PATTERNS.search(pred["title"]) or SHAME_PATTERNS.search(pred["message"]):
        return False, "shaming_language"

    if not _promise_reflected(case.user_promise, pred["title"], pred["message"]):
        return False, "promise_not_reflected"

    return True, None


def score_overlay(
    case: BlockCase,
    predicted: dict[str, Any] | None,
) -> tuple[dict[str, bool], bool, bool, str | None]:
    exp = normalize_overlay(case.expected_overlay)
    pred = normalize_overlay(predicted)
    field_matches: dict[str, bool] = {}
    if pred is None or exp is None:
        return {f: False for f in OVERLAY_FIELDS}, False, False, "parse_failure"

    for field in OVERLAY_FIELDS:
        if field in ("title", "message"):
            # Structural presence for field table; copy judged in safety/copy
            field_matches[field] = bool(pred[field])
        elif field == "tone":
            # tone is soft — match family
            field_matches[field] = _tone_compatible(exp["tone"], pred["tone"], case)
        else:
            field_matches[field] = field_equal(exp[field], pred[field], field)

    # Exact = all structural fields + copy quality + primary match
    structural_ok = all(
        field_matches[f]
        for f in (
            "primaryAction",
            "secondaryAction",
            "forbiddenActions",
            "showCooldown",
            "showPromise",
            "allowEmergencyExit",
            "tone",
        )
    )
    exact = structural_ok and copy_quality_ok(case, pred) and field_matches["title"] and field_matches["message"]

    safety_ok, violation = action_safety_ok(case, pred)
    # Also require expected primary family when gold is strict about WAIT_LOCK etc.
    if safety_ok and exp["primaryAction"] == "WAIT_LOCK" and pred["primaryAction"] != "WAIT_LOCK":
        safety_ok = False
        violation = "lock_primary_mismatch"

    return field_matches, exact, safety_ok, violation


def _tone_compatible(expected: str, predicted: str, case: BlockCase) -> bool:
    if expected == predicted:
        return True
    # Allow near families
    families = [
        {"soft_nudge", "smart_cost"},
        {"strict_guard", "contract_life_rule"},
        {"locked_vault", "tamper_cold", "contract_life_rule"},
    ]
    for fam in families:
        if expected in fam and predicted in fam:
            return True
    if case.decision == "WARN" and predicted in {"soft_nudge", "smart_cost"}:
        return True
    if case.decision in ("LOCK", "COOLING_OFF") and predicted in {"locked_vault", "tamper_cold"}:
        return True
    return False


def safety_violation(case: BlockCase, predicted: dict[str, Any] | None) -> str | None:
    pred = normalize_overlay(predicted)
    if pred is None:
        return "parse_failure"
    ok, reason = action_safety_ok(case, pred)
    return None if ok else reason

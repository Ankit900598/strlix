"""Shared types and dataset loading for PhoneCodex eval runner."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Classification:
    decision: str
    confidence: float
    reason: str
    reason_category: str


@dataclass(frozen=True)
class EvalCase:
    id: str
    package_name: str
    app_label: str
    screen_text: str
    user_goal: str
    strictness_level: str
    active_guardrails: list[str]
    commitment_type: str
    session_counters: dict[str, int] | None
    limit_state: str
    expected_decision: str
    expected_reason_category: str
    notes: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            counters = raw.get("sessionCounters")
            cases.append(
                EvalCase(
                    id=raw["id"],
                    package_name=raw["packageName"],
                    app_label=raw["appLabel"],
                    screen_text=raw["screenText"],
                    user_goal=raw["userGoal"],
                    strictness_level=raw["strictnessLevel"],
                    active_guardrails=list(raw.get("activeGuardrails", [])),
                    commitment_type=raw.get("commitmentType", "focus_session"),
                    session_counters=dict(counters) if counters else None,
                    limit_state=raw.get("limitState", "n/a"),
                    expected_decision=raw["expectedDecision"],
                    expected_reason_category=raw["expectedReasonCategory"],
                    notes=raw.get("notes", ""),
                )
            )
    if not cases:
        raise ValueError(f"No cases found in {path}")
    return cases

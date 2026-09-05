#!/usr/bin/env python3
"""Validate PhoneCodex eval JSONL against evals/datasets/schema.json (stdlib only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.json"

DECISIONS = {"ALLOW", "WARN", "BLOCK", "LOCK"}
STRICTNESS = {"SOFT", "SMART", "STRICT", "LOCKED"}
LIMIT_STATES = {"not_reached", "reached", "n/a"}
COMMITMENT_TYPES = {
    "focus_session",
    "quota_entertainment",
    "time_threshold",
    "permanent_guardrail",
    "monk_mode",
    "install_gate",
    "emergency_override",
}
REASON_CATEGORIES = {
    "study_aligned",
    "user_allowed_entertainment",
    "limit_not_reached",
    "limit_reached",
    "adult_content",
    "short_form_disallowed",
    "strict_monk_mode",
    "install_disallowed",
    "tamper_attempt",
    "ambiguous",
    "safe_app",
    "emergency_or_system",
    "neutral_navigation",
    "social_feed",
    "gaming",
    "shopping",
    "install_page_productivity",
}
REQUIRED = [
    "id",
    "packageName",
    "appLabel",
    "screenText",
    "userGoal",
    "strictnessLevel",
    "activeGuardrails",
    "expectedDecision",
    "expectedReasonCategory",
    "notes",
]


def load_schema_allowed_keys() -> set[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return set(schema.get("properties", {}).keys())


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    allowed_keys = load_schema_allowed_keys()
    ids: list[str] = []

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{line_no}: invalid JSON: {exc}")
                continue

            if not isinstance(raw, dict):
                errors.append(f"{path.name}:{line_no}: row must be object")
                continue

            extra = set(raw.keys()) - allowed_keys
            if extra:
                errors.append(f"{path.name}:{line_no}: unknown keys {sorted(extra)}")

            for key in REQUIRED:
                if key not in raw:
                    errors.append(f"{path.name}:{line_no}: missing required field {key!r}")

            case_id = raw.get("id", f"<line {line_no}>")
            ids.append(str(case_id))

            if raw.get("expectedDecision") not in DECISIONS:
                errors.append(f"{case_id}: invalid expectedDecision")
            if raw.get("strictnessLevel") not in STRICTNESS:
                errors.append(f"{case_id}: invalid strictnessLevel")
            if raw.get("expectedReasonCategory") not in REASON_CATEGORIES:
                errors.append(f"{case_id}: invalid expectedReasonCategory")
            if "limitState" in raw and raw["limitState"] not in LIMIT_STATES:
                errors.append(f"{case_id}: invalid limitState")
            if "commitmentType" in raw and raw["commitmentType"] not in COMMITMENT_TYPES:
                errors.append(f"{case_id}: invalid commitmentType")
            if "activeGuardrails" in raw and not isinstance(raw["activeGuardrails"], list):
                errors.append(f"{case_id}: activeGuardrails must be array")

    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"{path.name}: duplicate ids: {sorted(dupes)}")

    return errors


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv[1:]] if len(argv) > 1 else [
        ROOT / "evals" / "datasets" / "v0_seed.jsonl",
        ROOT / "evals" / "datasets" / "v0_challenge.jsonl",
        ROOT / "evals" / "datasets" / "v1_edge_cases.jsonl",
    ]
    all_errors: list[str] = []
    for path in paths:
        if not path.is_file():
            all_errors.append(f"missing file: {path}")
            continue
        count = sum(1 for line in path.open(encoding="utf-8") if line.strip())
        file_errors = validate_file(path)
        status = "OK" if not file_errors else "FAIL"
        print(f"{status}: {path.name} ({count} cases, {len(file_errors)} errors)")
        all_errors.extend(file_errors)

    if all_errors:
        print("\nErrors:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("\nAll datasets valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

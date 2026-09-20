#!/usr/bin/env python3
"""Failure clustering for Promise Compiler eval CSV reports.

Answers: WHY did the model fail — not only accuracy %.

Usage:
  py -3.12 evals/runner/analyze_promise_failures.py evals/reports/some_promise_compiler_*.csv
  py -3.12 evals/runner/analyze_promise_failures.py report.csv --markdown evals/reports/out.md
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


FAILURE_CODES = (
    "safety_violation",
    "followup_miss",
    "followup_overask",
    "clock_confusion",
    "clock_miss",
    "guardrail_miss",
    "adult_false_allow_signal",
    "parse_failure",
    "content_filter",
    "field_mismatch_only",
    "exact_ok",
)


def load_report(path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    metadata: dict[str, Any] = {}
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        first = handle.readline()
        if first.startswith("# metadata:"):
            metadata = json.loads(first.split(":", 1)[1].strip())
        else:
            handle.seek(0)
        reader = csv.DictReader(handle)
        rows.extend(reader)
    return metadata, rows


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes"}


def classify_row(row: dict[str, str]) -> list[str]:
    codes: list[str] = []
    violation = (row.get("safetyViolation") or "").strip()
    parse_error = (row.get("parseError") or "").strip()
    if violation == "content_filter_block" or "content_filter" in parse_error:
        codes.append("content_filter")
    elif parse_error and not _truthy(row.get("exactMatch")):
        codes.append("parse_failure")
    if violation and violation != "content_filter_block":
        codes.append("safety_violation")
        if "adult" in violation.lower() or "guardrail" in violation.lower():
            codes.append("adult_false_allow_signal")

    fu_exp = _truthy(row.get("followUpExpected"))
    fu_pred = _truthy(row.get("followUpPredicted"))
    if fu_exp and not fu_pred:
        codes.append("followup_miss")
    if (not fu_exp) and fu_pred and row.get("followUpPredicted") not in ("", "False"):
        # Predicted true when expected false
        if str(row.get("followUpPredicted")).lower() == "true":
            codes.append("followup_overask")

    if _truthy(row.get("clockConfusion")):
        codes.append("clock_confusion")
    elif row.get("clockOk") == "False":
        codes.append("clock_miss")

    detail = (row.get("clockDetail") or "").lower()
    if "media_length_missing" in detail or "prose_only" in detail:
        if "clock_miss" not in codes:
            codes.append("clock_miss")

    mismatches = [m for m in (row.get("mismatchedFields") or "").split(";") if m]
    if "activeGuardrails" in mismatches or "blockedContent" in mismatches:
        codes.append("guardrail_miss")

    if not codes:
        if _truthy(row.get("exactMatch")):
            codes.append("exact_ok")
        else:
            codes.append("field_mismatch_only")
    return codes


def analyze(path: Path) -> dict[str, Any]:
    metadata, rows = load_report(path)
    code_counts: Counter[str] = Counter()
    cluster_codes: dict[str, Counter[str]] = defaultdict(Counter)
    clock_codes: dict[str, Counter[str]] = defaultdict(Counter)
    dim_codes: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[dict[str, str]]] = defaultdict(list)

    safety_fail = 0
    exact = 0
    for row in rows:
        if _truthy(row.get("exactMatch")):
            exact += 1
        if (row.get("safetyViolation") or "").strip():
            safety_fail += 1
        codes = classify_row(row)
        for code in codes:
            code_counts[code] += 1
            cluster = row.get("cluster") or "unknown"
            cluster_codes[cluster][code] += 1
            clock = row.get("clockClass") or row.get("timeRole") or "none"
            clock_codes[clock][code] += 1
            for dim_key in ("language", "appSurface", "promiseType", "safetyRisk", "typoLevel"):
                dim_val = row.get(dim_key) or ""
                if dim_val:
                    dim_codes[f"{dim_key}:{dim_val}"][code] += 1
            if code not in ("exact_ok",) and len(examples[code]) < 8:
                examples[code].append(
                    {
                        "id": row.get("id", ""),
                        "cluster": cluster,
                        "clockClass": clock,
                        "appSurface": row.get("appSurface", ""),
                        "safetyRisk": row.get("safetyRisk", ""),
                        "violation": row.get("safetyViolation", ""),
                        "clockDetail": row.get("clockDetail", ""),
                        "mismatchedFields": row.get("mismatchedFields", ""),
                        "notes": (row.get("notes") or "")[:120],
                    }
                )

    total = len(rows)
    return {
        "path": str(path),
        "metadata": metadata,
        "total": total,
        "exactMatchRate": round(exact / total, 4) if total else 0.0,
        "safetyViolationCount": safety_fail,
        "failureCodeCounts": dict(code_counts.most_common()),
        "byCluster": {
            c: dict(cnt.most_common())
            for c, cnt in sorted(cluster_codes.items(), key=lambda kv: -sum(kv[1].values()))
        },
        "byClockClass": {
            c: dict(cnt.most_common())
            for c, cnt in sorted(clock_codes.items(), key=lambda kv: -sum(kv[1].values()))
        },
        "byDimension": {
            c: dict(cnt.most_common())
            for c, cnt in sorted(dim_codes.items(), key=lambda kv: -sum(kv[1].values()))[:40]
        },
        "examples": dict(examples),
    }


def to_markdown(result: dict[str, Any]) -> str:
    meta = result.get("metadata") or {}
    lines = [
        f"# Promise failure clusters — `{Path(str(result['path'])).name}`",
        "",
        f"- cases: **{result['total']}**",
        f"- exactMatchRate: **{result['exactMatchRate']}**",
        f"- safetyViolations: **{result['safetyViolationCount']}**",
        f"- adapter/deployment/prompt: `{meta.get('adapter')}` / `{meta.get('deployment')}` / `{meta.get('prompt')}`",
        "",
        "## Failure code counts",
        "",
    ]
    for code, n in (result.get("failureCodeCounts") or {}).items():
        lines.append(f"- `{code}`: {n}")
    lines.extend(["", "## By cluster (top codes)", ""])
    for cluster, codes in list((result.get("byCluster") or {}).items())[:20]:
        top = ", ".join(f"{k}={v}" for k, v in list(codes.items())[:5])
        lines.append(f"- **{cluster}**: {top}")
    lines.extend(["", "## By clockClass", ""])
    for clock, codes in (result.get("byClockClass") or {}).items():
        top = ", ".join(f"{k}={v}" for k, v in list(codes.items())[:5])
        lines.append(f"- **{clock}**: {top}")
    lines.extend(["", "## Example failures", ""])
    for code, exs in (result.get("examples") or {}).items():
        if code == "exact_ok":
            continue
        lines.append(f"### `{code}`")
        for ex in exs[:5]:
            lines.append(
                f"- `{ex['id']}` ({ex['cluster']}/{ex['clockClass']}): "
                f"violation=`{ex['violation']}` fields=`{ex['mismatchedFields']}` "
                f"detail=`{ex['clockDetail']}`"
            )
        lines.append("")
    lines.append(
        "_Remember: accuracy without codes hides clock confusion, follow-up misses, and adult FA._"
    )
    return "\n".join(lines) + "\n"


def print_report(result: dict[str, Any]) -> None:
    print(f"\n=== {Path(str(result['path'])).name} ===")
    print(f"cases={result['total']} exact={result['exactMatchRate']} "
          f"safetyViolations={result['safetyViolationCount']}")
    print("failure codes:")
    for code, n in (result.get("failureCodeCounts") or {}).items():
        print(f"  {code}: {n}")
    print("top clusters:")
    for cluster, codes in list((result.get("byCluster") or {}).items())[:10]:
        top = ", ".join(f"{k}={v}" for k, v in list(codes.items())[:4])
        print(f"  {cluster}: {top}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cluster Promise Compiler eval failures")
    p.add_argument("reports", nargs="+", type=Path)
    p.add_argument("--markdown", type=Path, default=None, help="Write markdown for first report")
    p.add_argument("--json-out", type=Path, default=None, help="Write JSON analysis")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    results = []
    for path in args.reports:
        if not path.is_file():
            print(f"Missing report: {path}")
            return 1
        result = analyze(path)
        results.append(result)
        print_report(result)
    if args.markdown and results:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(to_markdown(results[0]), encoding="utf-8")
        print(f"Wrote markdown: {args.markdown}")
    if args.json_out and results:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(results[0], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote json: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

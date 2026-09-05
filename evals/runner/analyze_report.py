#!/usr/bin/env python3
"""Analyze PhoneCodex eval CSV reports — failure clusters and boundary errors."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DECISION_ORDER = {"ALLOW": 0, "WARN": 1, "BLOCK": 2, "LOCK": 3}


def load_report(path: Path) -> tuple[dict[str, object], list[dict[str, str]]]:
    metadata: dict[str, object] = {}
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


def cluster_id(case_id: str) -> str:
    base = re.sub(r"_\d{3}$", "", case_id)
    base = re.sub(r"^v1_", "", base)
    base = re.sub(r"^ch_", "", base)
    return base


def severity(notes: str) -> str:
    match = re.search(r"\[severity:(\w+)\]", notes)
    return match.group(1) if match else "untagged"


def boundary_type(expected: str, predicted: str) -> str | None:
    if expected == predicted:
        return None
    e, p = DECISION_ORDER.get(expected, -1), DECISION_ORDER.get(predicted, -1)
    if e < 0 or p < 0:
        return "other"
    if abs(e - p) == 1:
        if e < p:
            return "under_enforced"  # expected softer, got harder
        return "over_enforced"  # expected harder, got softer
    return "multi_step"


def analyze(path: Path) -> dict[str, object]:
    metadata, rows = load_report(path)
    failures = [r for r in rows if r.get("correct") == "False"]
    false_allows = [r for r in rows if r.get("falseAllow") == "True"]
    false_blocks = [r for r in rows if r.get("falseBlock") == "True"]

    cluster_failures: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in failures:
        cluster_failures[cluster_id(row["id"])].append(row)

    allow_warn = [
        r for r in failures
        if {r["expectedDecision"], r["predictedDecision"]} == {"ALLOW", "WARN"}
    ]
    warn_block = [
        r for r in failures
        if {r["expectedDecision"], r["predictedDecision"]} == {"WARN", "BLOCK"}
    ]

    latencies = [float(r["latencyMs"]) for r in rows if r.get("latencyMs")]

    return {
        "path": str(path),
        "metadata": metadata,
        "total": len(rows),
        "correct": sum(1 for r in rows if r.get("correct") == "True"),
        "false_allows": len(false_allows),
        "false_blocks": len(false_blocks),
        "failures": failures,
        "false_allow_cases": false_allows,
        "false_block_cases": false_blocks,
        "cluster_failures": dict(cluster_failures),
        "allow_warn_errors": allow_warn,
        "warn_block_errors": warn_block,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
        "total_latency_ms": sum(latencies),
    }


def print_report(result: dict[str, object]) -> None:
    meta = result.get("metadata") or {}
    total = int(result["total"])
    correct = int(result["correct"])
    print(f"\n=== {Path(str(result['path'])).name} ===")
    if meta:
        print(
            f"deployment={meta.get('deployment')} model={meta.get('model')} "
            f"prompt={meta.get('prompt')} dataset={meta.get('dataset')}"
        )
    print(f"accuracy={correct/total:.1%} ({correct}/{total})")
    print(f"false_allows={result['false_allows']} false_blocks={result['false_blocks']}")
    print(f"avg_latency_ms={result['avg_latency_ms']:.0f}")

    cf = result["cluster_failures"]
    if cf:
        print("\nFailure clusters:")
        for cluster, cases in sorted(cf.items(), key=lambda x: -len(x[1])):
            print(f"  {cluster} ({len(cases)}):")
            for c in cases:
                print(
                    f"    {c['id']}: {c['expectedDecision']}->{c['predictedDecision']} "
                    f"| {c['reason'][:80]}"
                )

    print(f"\nALLOW↔WARN boundary errors: {len(result['allow_warn_errors'])}")
    print(f"WARN↔BLOCK boundary errors: {len(result['warn_block_errors'])}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: analyze_report.py <report.csv> [report2.csv ...]")
        return 1
    for arg in argv[1:]:
        print_report(analyze(Path(arg)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

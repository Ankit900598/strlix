#!/usr/bin/env python3
"""Run Block Experience Lab evals — safety-first overlay scoring."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ADAPTER_NAMES = ("baseline", "azure_openai")


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


_RUNNER_DIR = Path(__file__).resolve().parent
if str(_RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNNER_DIR))

from adapters.azure_openai import KNOWN_DEPLOYMENTS  # noqa: E402
from adapters.block_azure import get_block_writer  # noqa: E402
from adapters.block_baseline import BlockBaselineWriter  # noqa: E402
from block_experience_models import (  # noqa: E402
    OVERLAY_FIELDS,
    SAFETY_FIELDS,
    load_block_jsonl,
    repo_root,
    score_overlay,
    safety_violation,
)


def run_eval(writer: Any, cases: list) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {
        "total": 0,
        "exact_match": 0,
        "safety_match": 0,
        "safety_violations": 0,
        "parse_failures": 0,
        "content_filter_blocks": 0,
        "total_latency_ms": 0.0,
        "violation_counts": {},
    }
    field_match_counts: dict[str, int] = {field: 0 for field in OVERLAY_FIELDS}

    for case in cases:
        started = time.perf_counter()
        if isinstance(writer, BlockBaselineWriter):
            predicted = writer.write(case)
            error = None
            latency_ms = (time.perf_counter() - started) * 1000.0
        else:
            result = writer.write(case)
            predicted = result.overlay
            error = result.error
            latency_ms = result.latency_ms or (time.perf_counter() - started) * 1000.0

        field_matches, exact, safety, _ = score_overlay(case, predicted)
        violation = safety_violation(case, predicted)
        content_filtered = predicted is None and "content_filter" in (error or "")
        if content_filtered:
            violation = "content_filter_block"

        metrics["total"] += 1
        metrics["exact_match"] += int(exact)
        metrics["safety_match"] += int(safety)
        metrics["safety_violations"] += int(violation is not None)
        metrics["parse_failures"] += int(predicted is None and not content_filtered)
        metrics["content_filter_blocks"] += int(content_filtered)
        metrics["total_latency_ms"] += float(latency_ms)
        if violation:
            vc = metrics["violation_counts"]
            vc[violation] = int(vc.get(violation, 0)) + 1
        for field, matched in field_matches.items():
            field_match_counts[field] += int(matched)

        mismatches = [f for f in OVERLAY_FIELDS if not field_matches.get(f, False)]
        safety_mismatches = [f for f in SAFETY_FIELDS if not field_matches.get(f, False)]

        rows.append(
            {
                "id": case.id,
                "cluster": case.cluster,
                "decision": case.decision,
                "strictnessLevel": case.strictness_level,
                "reasonCategory": case.reason_category,
                "adapter": writer.name,
                "exactMatch": str(exact),
                "safetyMatch": str(safety),
                "safetyViolation": violation or "",
                "parseError": (error or "")[:400],
                "mismatchedFields": ";".join(mismatches),
                "safetyMismatches": ";".join(safety_mismatches),
                "expectedPrimary": case.expected_overlay.get("primaryAction", ""),
                "predictedPrimary": (predicted or {}).get("primaryAction", ""),
                "expectedTitle": case.expected_overlay.get("title", ""),
                "predictedTitle": (predicted or {}).get("title", ""),
                "latencyMs": f"{latency_ms:.1f}",
                "predictedOverlay": json.dumps(predicted, ensure_ascii=False) if predicted else "",
                "notes": case.notes,
            }
        )

    total = int(metrics["total"])
    metrics["field_match_rates"] = {
        field: round(count / total, 4) if total else 0.0
        for field, count in field_match_counts.items()
    }
    return rows, metrics


def write_report(rows: list[dict[str, Any]], path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"# metadata: {json.dumps(metadata, ensure_ascii=False)}\n")
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    path.with_suffix(".meta.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def print_summary(metrics: dict[str, Any], adapter_name: str) -> None:
    total = int(metrics["total"])
    exact = int(metrics["exact_match"])
    safety = int(metrics["safety_match"])
    print(f"Adapter: {adapter_name}")
    print(f"Cases: {total}")
    print(f"Structural+copy exact: {exact / total:.1%} ({exact}/{total})")
    print(f"Safety match: {safety / total:.1%} ({safety}/{total})")
    print(f"Safety violations: {int(metrics['safety_violations'])}")
    print(f"Parse failures: {int(metrics['parse_failures'])}")
    print(f"Content filter blocks: {int(metrics['content_filter_blocks'])}")
    avg = float(metrics["total_latency_ms"]) / total if total else 0.0
    print(f"Avg latency/case: {avg:.0f}ms")
    rates = metrics.get("field_match_rates") or {}
    print("\nPer-field match rates:")
    for field, rate in sorted(rates.items(), key=lambda kv: kv[1]):
        print(f"  {field}: {rate:.0%}")
    vc = metrics.get("violation_counts") or {}
    if vc:
        print("\nViolation breakdown:")
        for k, v in sorted(vc.items(), key=lambda kv: -kv[1]):
            print(f"  {k}: {v}")


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description="Run PhoneCodex Block Experience eval")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=root / "evals" / "datasets" / "v1_block_experience.jsonl",
    )
    parser.add_argument("--report-dir", type=Path, default=root / "evals" / "reports")
    parser.add_argument("--adapter", choices=ADAPTER_NAMES, default="baseline")
    parser.add_argument(
        "--prompt",
        type=Path,
        default=root / "evals" / "prompts" / "block_experience_v01.txt",
    )
    parser.add_argument("--deployment", choices=sorted(KNOWN_DEPLOYMENTS.keys()), default=None)
    parser.add_argument("--limit", type=int, default=None, help="Optional case cap for smoke runs")
    return parser.parse_args()


def main() -> int:
    root = repo_root()
    load_dotenv(root / ".env")
    args = parse_args()

    prompt_path = args.prompt if args.prompt.is_absolute() else root / args.prompt
    dataset_path = args.dataset if args.dataset.is_absolute() else root / args.dataset

    try:
        writer = get_block_writer(
            args.adapter,
            prompt_path=prompt_path if args.adapter == "azure_openai" else None,
            deployment=args.deployment,
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    cases = load_block_jsonl(dataset_path)
    if args.limit:
        cases = cases[: args.limit]

    started_at = datetime.now(timezone.utc)
    rows, metrics = run_eval(writer, cases)
    ended_at = datetime.now(timezone.utc)

    total = int(metrics["total"])
    metadata = {
        "task": "block_experience",
        "adapter": writer.name,
        "dataset": dataset_path.name,
        "prompt": prompt_path.name if args.adapter == "azure_openai" else None,
        "deployment": args.deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        "caseCount": total,
        "exactMatchRate": round(int(metrics["exact_match"]) / total, 4) if total else 0.0,
        "safetyMatchRate": round(int(metrics["safety_match"]) / total, 4) if total else 0.0,
        "safetyViolations": int(metrics["safety_violations"]),
        "parseFailures": int(metrics["parse_failures"]),
        "contentFilterBlocks": int(metrics["content_filter_blocks"]),
        "fieldMatchRates": metrics.get("field_match_rates", {}),
        "violationCounts": metrics.get("violation_counts", {}),
        "startedAt": started_at.isoformat(),
        "endedAt": ended_at.isoformat(),
    }

    parts = ["block_experience", writer.name]
    if args.deployment:
        parts.append(args.deployment)
    if args.adapter == "azure_openai":
        parts.append(prompt_path.stem)
    parts.append(dataset_path.stem)
    if args.limit:
        parts.append(f"limit{args.limit}")
    timestamp = ended_at.strftime("%Y%m%d_%H%M%S")
    report_path = args.report_dir / f"{'_'.join(parts)}_{timestamp}.csv"
    write_report(rows, report_path, metadata)

    print(f"Dataset: {dataset_path}")
    if args.adapter == "azure_openai":
        print(f"Prompt: {prompt_path}")
        print(f"Deployment: {metadata['deployment']}")
    print(f"Report: {report_path}")
    print_summary(metrics, writer.name)

    failures = [r for r in rows if r["safetyViolation"]]
    if failures[:12]:
        print("\nSafety violations (first 12):")
        for row in failures[:12]:
            print(f"- {row['id']}: {row['safetyViolation']} ({row['cluster']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

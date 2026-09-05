#!/usr/bin/env python3
"""PhoneCodex eval runner — supports pluggable classifier adapters."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from repo .env (no external deps). Skips existing vars."""
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

from adapters import ADAPTER_NAMES, get_adapter  # noqa: E402
from adapters.azure_openai import KNOWN_DEPLOYMENTS  # noqa: E402
from adapters.base import ClassifierAdapter  # noqa: E402
from models import EvalCase, load_jsonl, repo_root  # noqa: E402


def is_false_allow(expected: str, predicted: str) -> bool:
    return expected in {"BLOCK", "LOCK"} and predicted == "ALLOW"


def is_false_block(expected: str, predicted: str) -> bool:
    return expected == "ALLOW" and predicted == "BLOCK"


def run_eval(
    cases: Iterable[EvalCase],
    adapter: ClassifierAdapter,
) -> tuple[list[dict[str, object]], dict[str, int | float]]:
    rows: list[dict[str, object]] = []
    metrics: dict[str, int | float] = {
        "total": 0,
        "correct": 0,
        "false_allow": 0,
        "false_block": 0,
        "total_latency_ms": 0.0,
    }

    for case in cases:
        started = time.perf_counter()
        result = adapter.classify(case)
        latency_ms = getattr(adapter, "last_latency_ms", None)
        if latency_ms is None:
            latency_ms = (time.perf_counter() - started) * 1000.0

        correct = result.decision == case.expected_decision
        metrics["total"] += 1
        metrics["correct"] += int(correct)
        metrics["false_allow"] += int(is_false_allow(case.expected_decision, result.decision))
        metrics["false_block"] += int(is_false_block(case.expected_decision, result.decision))
        metrics["total_latency_ms"] = float(metrics["total_latency_ms"]) + float(latency_ms)

        rows.append(
            {
                "id": case.id,
                "adapter": adapter.name,
                "packageName": case.package_name,
                "expectedDecision": case.expected_decision,
                "predictedDecision": result.decision,
                "expectedReasonCategory": case.expected_reason_category,
                "predictedReasonCategory": result.reason_category,
                "confidence": f"{result.confidence:.2f}",
                "reason": result.reason,
                "correct": str(correct),
                "falseAllow": str(is_false_allow(case.expected_decision, result.decision)),
                "falseBlock": str(is_false_block(case.expected_decision, result.decision)),
                "latencyMs": f"{latency_ms:.1f}",
                "notes": case.notes,
            }
        )

    return rows, metrics


def build_report_metadata(
    *,
    adapter_name: str,
    dataset_path: Path,
    prompt_path: Path | None,
    deployment: str | None,
    model_name: str | None,
    metrics: dict[str, int | float],
    started_at: datetime,
    ended_at: datetime,
) -> dict[str, object]:
    total = int(metrics["total"])
    total_latency = float(metrics["total_latency_ms"])
    return {
        "adapter": adapter_name,
        "dataset": dataset_path.name,
        "datasetPath": str(dataset_path),
        "prompt": prompt_path.name if prompt_path else None,
        "promptPath": str(prompt_path) if prompt_path else None,
        "deployment": deployment,
        "model": model_name,
        "caseCount": total,
        "correct": int(metrics["correct"]),
        "accuracy": round(int(metrics["correct"]) / total, 4) if total else 0.0,
        "falseAllows": int(metrics["false_allow"]),
        "falseBlocks": int(metrics["false_block"]),
        "totalLatencyMs": round(total_latency, 1),
        "avgLatencyMs": round(total_latency / total, 1) if total else 0.0,
        "startedAt": started_at.isoformat(),
        "endedAt": ended_at.isoformat(),
    }


def write_report(
    rows: list[dict[str, object]],
    report_path: Path,
    metadata: dict[str, object] | None = None,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        if metadata:
            handle.write(f"# metadata: {json.dumps(metadata, ensure_ascii=False)}\n")
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if metadata:
        meta_path = report_path.with_suffix(".meta.json")
        meta_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def print_summary(metrics: dict[str, int | float], rows: list[dict[str, object]], adapter_name: str) -> None:
    total = int(metrics["total"])
    accuracy = int(metrics["correct"]) / total if total else 0.0
    total_latency = float(metrics["total_latency_ms"])
    avg_latency = total_latency / total if total else 0.0
    print(f"Adapter: {adapter_name}")
    print(f"Cases: {total}")
    print(f"Accuracy: {accuracy:.1%} ({int(metrics['correct'])}/{total})")
    print(f"False allows: {int(metrics['false_allow'])}")
    print(f"False blocks: {int(metrics['false_block'])}")
    print(f"Total latency: {total_latency / 1000:.1f}s")
    print(f"Avg latency/case: {avg_latency:.0f}ms")

    failures = [row for row in rows if row["correct"] == "False"]
    if failures:
        print("\nFailures:")
        for row in failures:
            print(
                f"- {row['id']}: expected {row['expectedDecision']}, "
                f"got {row['predictedDecision']} ({row['reason']})"
            )


def resolve_prompt_path(path: Path | None, root: Path) -> Path | None:
    """Resolve --prompt to an absolute path; None means adapter default (v01 for Azure)."""
    if path is None:
        return None
    resolved = path if path.is_absolute() else (root / path)
    if not resolved.is_file():
        raise FileNotFoundError(f"Classifier prompt not found: {resolved}")
    return resolved


def build_report_stem(
    adapter_name: str,
    dataset_path: Path,
    prompt_path: Path | None,
    deployment: str | None,
) -> str:
    parts = [adapter_name]
    if deployment:
        parts.append(deployment)
    if prompt_path:
        parts.append(prompt_path.stem)
    parts.append(dataset_path.stem)
    return "_".join(parts)


def parse_args() -> argparse.Namespace:
    root = repo_root()
    default_prompt = root / "evals" / "prompts" / "classifier_v01.txt"
    parser = argparse.ArgumentParser(description="Run PhoneCodex eval with a classifier adapter")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=root / "evals" / "datasets" / "v0_seed.jsonl",
        help="Path to JSONL dataset",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=root / "evals" / "reports",
        help="Directory for CSV reports",
    )
    parser.add_argument(
        "--adapter",
        choices=ADAPTER_NAMES,
        default="baseline",
        help="Classifier adapter to use (default: baseline)",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=None,
        help=(
            "Classifier prompt file for azure_openai adapter "
            f"(default: {default_prompt.relative_to(root).as_posix()})"
        ),
    )
    parser.add_argument(
        "--deployment",
        choices=sorted(KNOWN_DEPLOYMENTS.keys()),
        default=None,
        help=(
            "Azure deployment name (overrides AZURE_OPENAI_DEPLOYMENT from .env). "
            "Choices: pc-lab-cheap, pc-lab-strong, pc-lab-vision."
        ),
    )
    return parser.parse_args()


def main() -> int:
    root = repo_root()
    load_dotenv(root / ".env")
    args = parse_args()
    started_at = datetime.now(timezone.utc)
    try:
        prompt_path = resolve_prompt_path(args.prompt, root)
        adapter = get_adapter(
            args.adapter,
            prompt_path=prompt_path,
            deployment=args.deployment,
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    cases = load_jsonl(args.dataset)
    rows, metrics = run_eval(cases, adapter)
    ended_at = datetime.now(timezone.utc)

    deployment = getattr(adapter, "deployment", None) if args.adapter == "azure_openai" else None
    model_name = getattr(adapter, "model_name", None) if args.adapter == "azure_openai" else None
    azure_prompt = getattr(adapter, "_prompt_path", None) if args.adapter == "azure_openai" else None

    metadata = build_report_metadata(
        adapter_name=adapter.name,
        dataset_path=args.dataset,
        prompt_path=azure_prompt or prompt_path,
        deployment=deployment,
        model_name=model_name,
        metrics=metrics,
        started_at=started_at,
        ended_at=ended_at,
    )

    timestamp = ended_at.strftime("%Y%m%d_%H%M%S")
    stem = build_report_stem(adapter.name, args.dataset, azure_prompt or prompt_path, deployment)
    report_path = args.report_dir / f"{stem}_{timestamp}.csv"
    write_report(rows, report_path, metadata)

    print(f"Dataset: {args.dataset}")
    if args.adapter == "azure_openai":
        print(f"Deployment: {deployment} ({model_name})")
        print(f"Prompt: {azure_prompt}")
    print(f"Report: {report_path}")
    print_summary(metrics, rows, adapter.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

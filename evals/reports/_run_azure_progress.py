#!/usr/bin/env python3
"""Progress-logging wrapper around promise eval (prints every N cases)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals" / "runner"))

from adapters.promise_azure import get_promise_compiler  # noqa: E402
from promise_models import load_promise_jsonl  # noqa: E402
from run_promise_eval import load_dotenv, print_summary, run_eval, write_report  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--prompt", type=Path, required=True)
    p.add_argument("--deployment", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--progress-every", type=int, default=10)
    args = p.parse_args()

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    prompt = args.prompt if args.prompt.is_absolute() else ROOT / args.prompt
    compiler = get_promise_compiler(
        "azure_openai", prompt_path=prompt, deployment=args.deployment
    )
    cases = load_promise_jsonl(dataset)
    if args.limit:
        cases = cases[: args.limit]

    # Monkey-patch compile to log progress
    original = compiler.compile
    state = {"i": 0, "t0": time.perf_counter()}

    def wrapped(case):  # type: ignore[no-untyped-def]
        state["i"] += 1
        result = original(case)
        if state["i"] == 1 or state["i"] % args.progress_every == 0 or state["i"] == len(cases):
            elapsed = time.perf_counter() - state["t0"]
            avg = elapsed / state["i"]
            eta = avg * (len(cases) - state["i"])
            ok = result.policy is not None
            print(
                f"[{state['i']}/{len(cases)}] id={case.id} ok={ok} "
                f"lat={result.latency_ms:.0f}ms avg={avg:.1f}s eta={eta/60:.1f}m",
                flush=True,
            )
        return result

    compiler.compile = wrapped  # type: ignore[method-assign]

    started_at = datetime.now(timezone.utc)
    rows, metrics = run_eval(compiler, cases)
    ended_at = datetime.now(timezone.utc)
    total = int(metrics["total"])
    metadata = {
        "task": "promise_compiler",
        "adapter": compiler.name,
        "dataset": dataset.name,
        "prompt": prompt.name,
        "deployment": args.deployment,
        "caseCount": total,
        "exactMatchRate": round(int(metrics["exact_match"]) / total, 4) if total else 0.0,
        "safetyMatchRate": round(int(metrics["safety_match"]) / total, 4) if total else 0.0,
        "safetyViolations": int(metrics["safety_violations"]),
        "parseFailures": int(metrics["parse_failures"]),
        "contentFilterBlocks": int(metrics["content_filter_blocks"]),
        "fieldMatchRates": metrics.get("field_match_rates", {}),
        "temporalClockOkRate": (
            round(int(metrics["temporal_ok"]) / int(metrics["temporal_total"]), 4)
            if int(metrics.get("temporal_total") or 0)
            else None
        ),
        "clockConfusions": int(metrics.get("clock_confusion") or 0),
        "clockClassStats": metrics.get("clock_class_stats", {}),
        "clarificationAgreementRate": (
            round(int(metrics["clarify_ok"]) / total, 4) if total else 0.0
        ),
        "optionQualityRate": round(int(metrics["option_ok"]) / total, 4) if total else 0.0,
        "packageLeakRate": round(int(metrics["package_leaks"]) / total, 4) if total else 0.0,
        "unsafeAutoStartRate": (
            round(int(metrics["unsafe_auto_start"]) / total, 4) if total else 0.0
        ),
        "startedAt": started_at.isoformat(),
        "endedAt": ended_at.isoformat(),
    }
    stamp = ended_at.strftime("%Y%m%d_%H%M%S")
    report = (
        ROOT
        / "evals"
        / "reports"
        / f"promise_compiler_azure_openai_{args.deployment}_{prompt.stem}_{dataset.stem}_{stamp}.csv"
    )
    write_report(rows, report, metadata)
    print(f"Report: {report}", flush=True)
    print_summary(metrics, compiler.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

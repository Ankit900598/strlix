#!/usr/bin/env python3
"""Read-only golden-intent evaluator for Strlix android-api and legacy Pilot.

The evaluator deliberately does not execute android-api tool proposals.  A real
completion score requires a disposable, seeded emulator fixture and a
postcondition verifier; API reachability and model planning are reported
separately so a healthy model response is not misreported as task success.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "demo/ui-vision/golden-intent-eval/intents.json"
DEFAULT_REPORT_DIR = ROOT / "demo/ui-vision/golden-intent-eval/reports"
DEFAULT_FIXTURE_MANIFEST = ROOT / "demo/ui-vision/golden-intent-eval/fixtures/manifest.json"
PILOT_TOOL_MAP = {
    "adb_tap": "a11y_tap",
    "adb_type": "a11y_type",
    "adb_swipe": "a11y_swipe",
    "adb_key": "a11y_key",
}


def load_suite() -> dict[str, Any]:
    data = json.loads(SUITE.read_text(encoding="utf-8"))
    intents = data.get("intents")
    if data.get("intent_count") != 12 or not isinstance(intents, list) or len(intents) != 12:
        raise ValueError("suite must contain exactly 12 intents")
    ids = [item.get("id") for item in intents]
    if len(set(ids)) != len(ids) or any(not item.get("prompt") for item in intents):
        raise ValueError("each intent needs a unique id and prompt")
    return data


def load_fixture_manifest(path: Path) -> dict[str, Any]:
    """Load the postcondition contract without treating definitions as evidence."""
    data = json.loads(path.read_text(encoding="utf-8"))
    intents = data.get("intents")
    if not isinstance(intents, list) or len(intents) != 12:
        raise ValueError("fixture manifest must contain exactly 12 intents")
    ids = [item.get("id") for item in intents]
    if len(set(ids)) != 12 or any(not item.get("fixture_id") or not item.get("postconditions") for item in intents):
        raise ValueError("each fixture needs a unique id, fixture_id, and postconditions")
    return data


def load_postcondition_evidence(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("intents"), dict):
        raise ValueError("postcondition evidence must contain an intents object")
    return data


def verify_postconditions(intent: dict[str, Any], fixture: dict[str, Any] | None,
                          caps: dict[str, Any], evidence: dict[str, Any] | None) -> bool | None:
    """Verify provider evidence; return None when the run is not eligible to score."""
    if not fixture or not evidence or not caps.get("fixture_installed"):
        return None
    if evidence.get("fixture_package") != caps.get("fixture_package"):
        return None
    if evidence.get("serial") != caps.get("serial"):
        return None
    entry = evidence["intents"].get(intent["id"])
    if not isinstance(entry, dict) or entry.get("fixture_id") != fixture["fixture_id"]:
        return None
    statuses = entry.get("postconditions")
    if not isinstance(statuses, dict):
        return None
    return all(statuses.get(condition) is True for condition in fixture["postconditions"])


def adb_snapshot(serial: str | None, fixture_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    if not serial:
        return {"available": False, "reason": "--no-adb"}
    adb = str(ROOT / "platform-tools/adb")
    def run(*args: str) -> str:
        try:
            p = subprocess.run([adb, "-s", serial, *args], capture_output=True, text=True, timeout=5)
            return p.stdout.strip() if p.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""
    state = run("get-state")
    size = run("shell", "wm", "size")
    packages = run("shell", "pm", "list", "packages")
    installed_packages = {
        line.removeprefix("package:")
        for line in packages.splitlines()
        if line.startswith("package:")
    }
    fixture_package = (fixture_manifest or {}).get("fixture_package")
    fixture_installed = bool(fixture_package and fixture_package in installed_packages)
    return {
        "available": state == "device",
        "serial": serial,
        "state": state or "unavailable",
        "size": size,
        "package_count": len(installed_packages),
        "fixture_package": fixture_package,
        "fixture_installed": fixture_installed,
        "relevant_packages": sorted(
            package for package in (
                line.removeprefix("package:") for line in packages.splitlines() if line.startswith("package:")
            ) if package in {
                "com.android.chrome", "com.google.android.gm", "com.google.android.apps.photos",
                "com.google.android.apps.maps", "com.google.android.calendar", "com.google.android.deskclock",
                "com.android.settings", "com.zevi.agent",
            }
        ),
    }


def http_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, Any, int, str | None]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            elapsed = round((time.perf_counter() - started) * 1000)
            try:
                return response.status, json.loads(raw.decode("utf-8")), elapsed, None
            except json.JSONDecodeError as exc:
                return response.status, None, elapsed, f"invalid JSON: {exc}"
    except urllib.error.HTTPError as exc:
        elapsed = round((time.perf_counter() - started) * 1000)
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw), elapsed, None
        except json.JSONDecodeError:
            return exc.code, None, elapsed, raw[:300]
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        elapsed = round((time.perf_counter() - started) * 1000)
        return 0, None, elapsed, f"{type(exc).__name__}: {exc}"


def normalized_tools(body: Any, backend: str) -> list[dict[str, Any]]:
    if not isinstance(body, dict) or not isinstance(body.get("tools"), list):
        return []
    out = []
    for raw in body["tools"]:
        if not isinstance(raw, dict):
            continue
        original = str(raw.get("name") or raw.get("tool") or "")
        normalized = PILOT_TOOL_MAP.get(original, original)
        args = raw.get("args") if isinstance(raw.get("args"), dict) else {}
        out.append({"name": normalized, "original_name": original, "args": args})
    return out


def strings_in(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.lower()]
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(strings_in(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(strings_in(item))
        return result
    return []


def evaluate(intent: dict[str, Any], status: int, body: Any, elapsed_ms: int, error: str | None,
             backend: str, caps: dict[str, Any], allow_device_actions: bool,
             fixture: dict[str, Any] | None, evidence: dict[str, Any] | None) -> dict[str, Any]:
    tools = normalized_tools(body, backend)
    names = [tool["name"] for tool in tools]
    reply = body.get("reply") if isinstance(body, dict) else None
    contract_pass = status >= 200 and status < 300 and isinstance(body, dict) and bool(body.get("ok", True)) and bool(str(reply or "").strip()) and isinstance(body.get("tools"), list)
    expected = set(intent.get("expected_tools", []))
    relevant = sorted(expected.intersection(names))
    arg_text = " ".join(strings_in([tool["args"] for tool in tools]))
    app_hints = [str(app).lower() for app in intent.get("expected_apps", [])]
    app_hint_match = any(hint in arg_text for hint in app_hints) if app_hints else True
    # A launch proposal should name a relevant app. For generic actions, tool relevance is enough.
    has_launch = "a11y_launch" in names
    plan_pass = contract_pass and bool(relevant) and (not has_launch or app_hint_match)
    postcondition_pass = verify_postconditions(intent, fixture, caps, evidence)
    if not contract_pass:
        completion_status = "not_run:api_error"
    elif intent.get("requires_fixture") and not fixture:
        completion_status = "blocked:fixture_definition_missing"
    elif intent.get("requires_fixture") and not caps.get("fixture_installed", False):
        completion_status = "blocked:seeded_fixture_required"
    elif intent.get("requires_fixture") and postcondition_pass is None:
        completion_status = "blocked:postcondition_evidence_required"
    elif intent.get("requires_fixture") and postcondition_pass:
        completion_status = "pass:postconditions_verified"
    elif intent.get("requires_fixture"):
        completion_status = "fail:postconditions"
    elif intent.get("destructive"):
        completion_status = "blocked:explicit_confirmation_required"
    else:
        completion_status = "not_run:no_postcondition_verifier"
    if allow_device_actions and backend == "pilot" and contract_pass:
        completion_status = "unverified:live_device_no_postcondition"
    blockers = []
    if error:
        blockers.append(error)
    if intent.get("requires_fixture") and not fixture:
        blockers.append("no fixture/postcondition definition exists for this intent")
    elif intent.get("requires_fixture") and not caps.get("fixture_installed", False):
        blockers.append(f"fixture package {caps.get('fixture_package') or 'unknown'} is not installed")
    elif intent.get("requires_fixture") and postcondition_pass is None:
        blockers.append("no eligible postcondition evidence was supplied")
    elif intent.get("requires_fixture") and not postcondition_pass:
        blockers.append("one or more deterministic postconditions failed")
    if intent.get("destructive"):
        blockers.append("destructive flow requires disposable data and explicit final confirmation")
    if not caps.get("available", False):
        blockers.append("emulator unavailable")
    return {
        "id": intent["id"],
        "title": intent["title"],
        "backend": backend,
        "status": status,
        "elapsed_ms": elapsed_ms,
        "contract_pass": contract_pass,
        "plan_pass": plan_pass,
        "completion_pass": postcondition_pass,
        "completion_status": completion_status,
        "reply": str(reply or "")[:500],
        "tools": tools,
        "relevant_tools": relevant,
        "app_hint_match": app_hint_match,
        "error": error,
        "blockers": blockers,
        "fixture_id": fixture.get("fixture_id") if fixture else None,
        "postconditions": fixture.get("postconditions", []) if fixture else [],
    }


def markdown(report: dict[str, Any]) -> str:
    agg = report["aggregate"]
    lines = [
        "# Strlix golden-intent evaluation",
        "",
        f"- Run: `{report['run_at_ist']}`",
        f"- Backend: `{report['backend']}` (`{report['base_url']}`)",
        f"- Intents: **{agg['total']}**",
        f"- Contract pass: **{agg['contract_pass']}/{agg['total']} ({agg['contract_rate']:.1%})**",
        f"- Plan pass: **{agg['plan_pass']}/{agg['total']} ({agg['plan_rate']:.1%})**",
        (f"- E2E completion: **{agg['completion_pass']}/{agg['completion_scored']} ({agg['completion_rate']:.1%})**"
         if agg["completion_scored"]
         else "- E2E completion: **not scored** (0 deterministic postconditions)"),
        f"- 95% target: **{'met' if agg['target_met'] else 'not met / not established'}**",
        "",
        "The contract and plan rates are diagnostic only. API tool proposals do not prove that an action ran or that a user goal was completed.",
        "",
        "## Results",
        "",
        "| ID | Contract | Plan | Completion | Tools | Blockers |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in report["results"]:
        tools = ", ".join(t["name"] for t in row["tools"]) or "—"
        blockers = "; ".join(row["blockers"]) or "—"
        lines.append(f"| `{row['id']}` | {'PASS' if row['contract_pass'] else 'FAIL'} | {'PASS' if row['plan_pass'] else 'FAIL'} | `{row['completion_status']}` | `{tools}` | {blockers} |")
    lines += [
        "",
        "## Emulator/API snapshot",
        "",
        f"```json\n{json.dumps(report['capabilities'], indent=2)}\n```",
        "",
        "## Preservation check",
        "",
        "This harness is additive and read-only by default. It does not modify Live orb, STT, Replay, barge-in, or Android share paths; those remain outside the golden-intent completion verifier.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["android-api", "pilot"], default="android-api")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--intent", action="append", dest="intent_ids")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--serial", default="127.0.0.1:5555")
    parser.add_argument("--no-adb", action="store_true")
    parser.add_argument("--allow-device-actions", action="store_true", help="Acknowledge that Pilot may execute real ADB tools")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--out", default=None, help="JSON report path")
    parser.add_argument("--report", default=None, help="Markdown report path")
    parser.add_argument("--fixture-manifest", default=str(DEFAULT_FIXTURE_MANIFEST), help="Fixture/postcondition contract JSON")
    parser.add_argument("--postcondition-evidence", default=None, help="Provider evidence JSON; never generated by this runner")
    args = parser.parse_args()
    suite = load_suite()
    fixture_manifest = load_fixture_manifest(Path(args.fixture_manifest))
    evidence = load_postcondition_evidence(Path(args.postcondition_evidence) if args.postcondition_evidence else None)
    fixtures_by_id = {item["id"]: item for item in fixture_manifest["intents"]}
    selected = suite["intents"]
    if args.intent_ids:
        wanted = set(args.intent_ids)
        selected = [item for item in selected if item["id"] in wanted]
        unknown = wanted - {item["id"] for item in selected}
        if unknown:
            raise SystemExit(f"unknown intent id(s): {', '.join(sorted(unknown))}")
    if args.repeat < 1:
        raise SystemExit("--repeat must be >= 1")
    if args.validate_only:
        print(f"validated {len(suite['intents'])} golden intents; target={suite['target_success_rate']:.0%}")
        return 0
    if args.backend == "pilot" and not args.allow_device_actions:
        raise SystemExit("pilot can execute real ADB actions; pass --allow-device-actions explicitly")
    base = (args.base_url or ("http://127.0.0.1:8788" if args.backend == "android-api" else "http://127.0.0.1:8787")).rstrip("/")
    endpoint = f"{base}/v1/chat" if args.backend == "android-api" else f"{base}/chat"
    caps = adb_snapshot(None if args.no_adb else args.serial, fixture_manifest)
    rows = []
    for repeat in range(args.repeat):
        for intent in selected:
            status, body, elapsed, error = http_json(endpoint, {"message": intent["prompt"]}, args.timeout)
            row = evaluate(intent, status, body, elapsed, error, args.backend, caps, args.allow_device_actions,
                            fixtures_by_id.get(intent["id"]), evidence)
            row["repeat"] = repeat + 1
            rows.append(row)
            print(f"{intent['id']}: contract={'PASS' if row['contract_pass'] else 'FAIL'} plan={'PASS' if row['plan_pass'] else 'FAIL'} completion={row['completion_status']}")
    total = len(rows)
    contract_pass = sum(1 for row in rows if row["contract_pass"])
    plan_pass = sum(1 for row in rows if row["plan_pass"])
    completion_scored = [row for row in rows if row["completion_pass"] is not None]
    completion_pass = sum(1 for row in completion_scored if row["completion_pass"])
    aggregate = {
        "total": total,
        "contract_pass": contract_pass,
        "contract_rate": contract_pass / total if total else 0,
        "plan_pass": plan_pass,
        "plan_rate": plan_pass / total if total else 0,
        "completion_scored": len(completion_scored),
        "completion_pass": completion_pass,
        "completion_rate": completion_pass / len(completion_scored) if completion_scored else None,
        "target_rate": suite["target_success_rate"],
        "target_met": bool(completion_scored) and completion_pass / len(completion_scored) >= suite["target_success_rate"],
    }
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    report = {
        "schema_version": 1,
        "run_at_ist": now.isoformat(timespec="seconds"),
        "suite": suite["suite"],
        "backend": args.backend,
        "base_url": base,
        "endpoint": endpoint,
        "capabilities": caps,
        "aggregate": aggregate,
        "results": rows,
    }
    out = Path(args.out) if args.out else DEFAULT_REPORT_DIR / f"{args.backend}-latest.json"
    md = Path(args.report) if args.report else DEFAULT_REPORT_DIR / f"{args.backend}-latest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    md.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md.write_text(markdown(report), encoding="utf-8")
    print(f"wrote {out}")
    print(f"wrote {md}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"suite error: {exc}", file=sys.stderr)
        raise SystemExit(2)

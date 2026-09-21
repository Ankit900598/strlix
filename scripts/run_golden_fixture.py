#!/usr/bin/env python3
"""Install and exercise the synthetic golden-intent fixture on one emulator."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APK = ROOT / "demo/ui-vision/golden-intent-eval/fixtures/android/app/build/outputs/apk/debug/app-debug.apk"
DEFAULT_OUT = ROOT / "demo/ui-vision/golden-intent-eval/fixtures/postcondition-evidence.json"
PKG = "com.zevi.goldenfixture"
ACTIVITY = f"{PKG}/.MainActivity"


def adb(adb_path: str, serial: str, *args: str, timeout: float = 30) -> str:
    proc = subprocess.run([adb_path, "-s", serial, *args], text=True, capture_output=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(f"adb {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def ui_xml(adb_path: str, serial: str) -> str:
    adb(adb_path, serial, "shell", "uiautomator", "dump", "/sdcard/golden-window.xml", timeout=15)
    return adb(adb_path, serial, "exec-out", "cat", "/sdcard/golden-window.xml", timeout=15)


def tap_text(adb_path: str, serial: str, wanted: str) -> bool:
    try:
        root = ET.fromstring(ui_xml(adb_path, serial))
    except (ET.ParseError, RuntimeError):
        return False
    for node in root.iter():
        if node.attrib.get("text") == wanted or node.attrib.get("content-desc") == wanted:
            bounds = node.attrib.get("bounds", "")
            try:
                left_top, right_bottom = bounds.strip("[]").split("][")
                x1, y1 = (int(v) for v in left_top.split(","))
                x2, y2 = (int(v) for v in right_bottom.rstrip("]").split(","))
            except (ValueError, AttributeError):
                continue
            adb(adb_path, serial, "shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2), timeout=15)
            return True
    return False


def wait_for(adb_path: str, serial: str, text: str, timeout: float = 15) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if text in ui_xml(adb_path, serial):
                return True
        except RuntimeError:
            pass
        time.sleep(0.25)
    return False


def read_fixture_evidence(adb_path: str, serial: str) -> dict:
    raw = adb(adb_path, serial, "shell", "run-as", PKG, "cat", "files/fixture-evidence.json", timeout=15)
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="127.0.0.1:5555")
    parser.add_argument("--adb", default=str(ROOT / "platform-tools/adb"))
    parser.add_argument("--apk", default=str(DEFAULT_APK))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    manifest = json.loads((ROOT / "demo/ui-vision/golden-intent-eval/fixtures/manifest.json").read_text())
    apk = Path(args.apk)
    if not apk.is_file():
        raise SystemExit(f"fixture APK missing: {apk}; build fixtures/android first")

    adb(args.adb, args.serial, "get-state")
    print(f"installing {apk}")
    adb(args.adb, args.serial, "install", "-r", str(apk), timeout=90)
    evidence = {
        "schema_version": 1,
        "fixture_package": PKG,
        "serial": args.serial,
        "provider": "scripts/run_golden_fixture.py",
        "intents": {},
    }
    for fixture in manifest["intents"]:
        intent_id = fixture["id"]
        fixture_id = fixture["fixture_id"]
        adb(args.adb, args.serial, "shell", "am", "force-stop", PKG, timeout=15)
        time.sleep(1.0)
        adb(args.adb, args.serial, "shell", "am", "start", "-n", ACTIVITY, "--es", "fixture_id", intent_id, timeout=15)
        if not wait_for(args.adb, args.serial, "Run fixture action"):
            raise RuntimeError(f"{intent_id}: fixture action control did not appear")
        if not tap_text(args.adb, args.serial, "Run fixture action"):
            raise RuntimeError(f"{intent_id}: could not tap fixture action")
        if not wait_for(args.adb, args.serial, "PASS — all deterministic postconditions verified"):
            raise RuntimeError(f"{intent_id}: fixture did not reach PASS state")
        app_evidence = read_fixture_evidence(args.adb, args.serial)
        statuses = app_evidence.get("postconditions")
        if app_evidence.get("fixture_package") != PKG or app_evidence.get("fixture_id") != fixture_id:
            raise RuntimeError(f"{intent_id}: fixture identity mismatch: {app_evidence}")
        if not isinstance(statuses, dict) or not all(statuses.get(key) is True for key in fixture["postconditions"]):
            raise RuntimeError(f"{intent_id}: postcondition verification failed: {app_evidence}")
        evidence["intents"][intent_id] = {
            "fixture_id": fixture_id,
            "postconditions": {key: True for key in fixture["postconditions"]},
        }
        print(f"{intent_id}: PASS ({len(fixture['postconditions'])} postconditions)")

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"verified {len(evidence['intents'])}/{len(manifest['intents'])} fixture intents")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"fixture run failed: {exc}", file=sys.stderr)
        raise SystemExit(2)

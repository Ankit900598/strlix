#!/usr/bin/env python3
"""One-shot Azure model catalog audit for PhoneCodex."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "azure_models_full.json"
AZ = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

raw = subprocess.check_output(
    [AZ, "cognitiveservices", "account", "list-models",
     "-g", "phonecodex-dev", "-n", "ay186mnc-1561-resource", "-o", "json"],
    text=True,
)
OUT.write_text(raw, encoding="utf-8")
models = json.loads(raw)

def classify(name: str) -> str:
    nl = name.lower()
    if "sora" in nl or nl.startswith("video"):
        return "video_sora"
    if "claude" in nl:
        return "claude"
    if "embed" in nl or "ada" in nl:
        return "embedding"
    if name in ("o1", "o3", "o3-mini", "o4-mini") or name.startswith("gpt-5"):
        return "openai_reasoning"
    if "4o" in name or "vision" in nl:
        return "openai_vision"
    if name.startswith("gpt-"):
        return "openai_chat"
    return "other"

rows = []
seen = set()
for m in models:
    model = m.get("model", m)
    name = model.get("name", "")
    ver = model.get("version", "")
    key = (name, ver)
    if key in seen:
        continue
    seen.add(key)
    skus = [s.get("name") if isinstance(s, dict) else s for s in (m.get("skus") or model.get("skus") or [])]
    rows.append({
        "name": name,
        "version": ver,
        "skus": skus,
        "category": classify(name),
        "has_standard": "Standard" in skus,
        "has_global_standard": "GlobalStandard" in skus,
        "has_datazone": "DataZoneStandard" in skus,
        "has_provisioned": any("Provisioned" in s for s in skus),
    })

audit = {
    "account": "ay186mnc-1561-resource",
    "region": "westus3",
    "total_entries": len(rows),
    "models": sorted(rows, key=lambda r: (r["category"], r["name"], r["version"])),
}
audit_path = Path(__file__).resolve().parent / "azure_model_capability_audit.json"
audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

from collections import Counter
counts = Counter(r["category"] for r in rows)
print("Categories:", dict(counts))
print("Standard SKU models (deployable serverless):")
for r in rows:
    if r["has_standard"] and r["category"] not in ("video_sora", "embedding", "other"):
        print(f"  {r['name']:22} {r['version']:12} {r['category']}")

#!/usr/bin/env python3
import json, os, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
msg = sys.argv[1] if len(sys.argv) > 1 else "Take a screenshot and describe what you see on the home screen."
url = os.environ.get("PILOT_URL", "http://127.0.0.1:8787/chat")
req = urllib.request.Request(url, data=json.dumps({"message": msg}).encode(), headers={"Content-Type":"application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=300) as resp:
    body = json.load(resp)
out = ROOT / "demo" / "last-demo.json"
out.write_text(json.dumps(body, indent=2)[:50000])
print("REPLY:", body.get("reply","")[:2000])
print("TOOLS:", body.get("tools"))
print("SHOTS:", body.get("screenshots"))
print("saved", out)

"""Viewer "Ask" bridge: POST /chat on the stream host -> android-api -> phone.

The viewer (static/index.html) posts {message, history} to /chat on the stream
origin. desktop-api never served /chat (only the old monolith did), so Ask
always failed with 404. This bridge forwards the turn to android-api
(POST {ANDROID_API_URL}/v1/chat), runs the proposed Accessibility-style tools
on the session's phone over ADB (launch app, tap label/coords, type, swipe,
scroll, HOME/BACK/APP_SWITCH), feeds the results back for a few rounds, and
returns {reply, tools, history} in the shape the viewer already renders.

Safety: the LLM policy in android-api stops before irreversible confirmations;
this bridge adds a step cap, a per-IP rate limit, and never runs raw shell.
Env: ANDROID_API_URL (required, e.g. https://<edge>/agent), AGENT_MAX_ROUNDS
(default 3), AGENT_CHAT_PER_MIN (default 12).
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any, Optional
from xml.etree import ElementTree

import httpx

ANDROID_API_URL = os.environ.get("ANDROID_API_URL", "").rstrip("/")
MAX_ROUNDS = max(1, min(int(os.environ.get("AGENT_MAX_ROUNDS", "3")), 6))
CHAT_PER_MIN = int(os.environ.get("AGENT_CHAT_PER_MIN", "12"))
_buckets: dict[str, list[float]] = {}

APP_PACKAGES = {
    "chrome": "com.android.chrome",
    "settings": "com.android.settings",
    "gmail": "com.google.android.gm",
    "photos": "com.google.android.apps.photos",
    "calendar": "com.google.android.calendar",
    "clock": "com.google.android.deskclock",
    "maps": "com.google.android.apps.maps",
    "youtube": "com.google.android.youtube",
    "play store": "com.android.vending",
    "playstore": "com.android.vending",
    "camera": "com.android.camera2",
    "contacts": "com.google.android.contacts",
    "phone": "com.google.android.dialer",
    "messages": "com.google.android.apps.messaging",
    "files": "com.google.android.documentsui",
}


def allow(ip: str) -> bool:
    now = time.time()
    b = [t for t in _buckets.get(ip or "?", []) if now - t < 60]
    if len(b) >= CHAT_PER_MIN:
        _buckets[ip or "?"] = b
        return False
    b.append(now)
    _buckets[ip or "?"] = b
    return True


async def _resolve_package(adb, app: str) -> Optional[str]:
    name = (app or "").strip()
    if not name:
        return None
    if re.fullmatch(r"[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)+", name):
        return name
    key = name.lower()
    if key in APP_PACKAGES:
        return APP_PACKAGES[key]
    r = await adb.shell("pm list packages")
    word = re.sub(r"[^a-z0-9]", "", key)
    for line in (r.get("stdout") or "").splitlines():
        pkg = line.replace("package:", "").strip()
        if word and word in pkg.lower().replace(".", ""):
            return pkg
    return None


def _bounds_center(b: str) -> Optional[tuple[int, int]]:
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


async def _find_label(adb, label: str) -> Optional[tuple[int, int]]:
    r = await adb.shell("uiautomator dump /sdcard/strlix_ui.xml >/dev/null 2>&1; cat /sdcard/strlix_ui.xml")
    xml = (r.get("stdout") or "")
    start = xml.find("<?xml")
    if start < 0:
        start = xml.find("<hierarchy")
    if start < 0:
        return None
    try:
        root = ElementTree.fromstring(xml[start:])
    except ElementTree.ParseError:
        return None
    want = label.strip().lower()
    exact = partial = None
    for node in root.iter("node"):
        for attr in ("text", "content-desc"):
            v = (node.get(attr) or "").strip().lower()
            if not v:
                continue
            if v == want and exact is None:
                exact = _bounds_center(node.get("bounds", ""))
            elif want in v and partial is None:
                partial = _bounds_center(node.get("bounds", ""))
    return exact or partial


async def run_tool(adb, tool: dict) -> dict:
    name = tool.get("name") or ""
    args = tool.get("args") or {}
    t0 = time.time()
    ok, detail = False, ""
    try:
        size = await adb.wm_size()
        w, h = int(size.get("width") or 1080), int(size.get("height") or 2400)
        if name == "a11y_launch":
            pkg = await _resolve_package(adb, str(args.get("app") or args.get("package") or ""))
            if not pkg:
                detail = f"app not installed: {args.get('app')}"
            else:
                r = await adb.shell(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")
                ok = r.get("ok", False) and "No activities found" not in (r.get("stdout") or "")
                detail = f"launched {pkg}" if ok else f"could not launch {pkg}"
        elif name == "a11y_tap":
            if args.get("label"):
                c = await _find_label(adb, str(args["label"]))
                if c:
                    await adb.tap(*c)
                    ok, detail = True, f"tapped '{args['label']}'"
                else:
                    detail = f"no element labelled '{args['label']}' on screen"
            elif args.get("x_norm") is not None and args.get("y_norm") is not None:
                x = int(max(0.0, min(1.0, float(args["x_norm"]))) * w)
                y = int(max(0.0, min(1.0, float(args["y_norm"]))) * h)
                await adb.tap(x, y)
                ok, detail = True, f"tapped {x},{y}"
            else:
                detail = "tap needs label or x_norm/y_norm"
        elif name == "a11y_type":
            await adb.type_text(str(args.get("text") or "")[:500])
            ok, detail = True, "typed"
        elif name in ("a11y_swipe", "a11y_scroll"):
            d = str(args.get("direction") or "up")
            d = {"forward": "up", "backward": "down"}.get(d, d)
            cx, cy = w // 2, h // 2
            dx = {"left": -w // 3, "right": w // 3}.get(d, 0)
            dy = {"up": -h // 3, "down": h // 3}.get(d, 0)
            await adb.swipe(cx - dx // 2, cy - dy // 2, cx + dx // 2, cy + dy // 2, 300)
            ok, detail = True, f"swiped {d}"
        elif name == "a11y_key":
            kc = str(args.get("keycode") or "BACK").upper()
            if kc not in ("HOME", "BACK", "APP_SWITCH"):
                detail = f"key {kc} not allowed"
            else:
                await adb.key(kc)
                ok, detail = True, f"pressed {kc}"
        elif name == "local_done":
            ok, detail = True, "done"
        else:
            detail = f"unknown tool {name}"
    except Exception as e:  # noqa: BLE001
        detail = f"{type(e).__name__}: {e}"[:200]
    return {"id": tool.get("id") or name, "name": name, "ok": ok, "detail": detail,
            "elapsed_ms": int((time.time() - t0) * 1000)}


async def chat_turn(adb, message: str, history: Optional[list] = None, language: Optional[str] = None) -> dict:
    if not ANDROID_API_URL:
        return {"ok": False, "status": 503, "error": "Ask is not configured on this phone (ANDROID_API_URL unset)."}
    history = list(history or [])[-20:]
    executed: list[dict] = []
    results: list[dict] = []
    reply = ""
    model = None
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=8.0)) as client:
        for rnd in range(MAX_ROUNDS):
            body: dict[str, Any] = {"message": message, "history": history, "device_id": "strlix-viewer"}
            if language:
                body["language"] = language
            if results:
                body["tool_results"] = results
            try:
                r = await client.post(ANDROID_API_URL + "/v1/chat", json=body)
            except httpx.HTTPError as e:
                return {"ok": False, "status": 502, "error": f"assistant unreachable: {type(e).__name__}"}
            if r.status_code != 200:
                detail = ""
                try:
                    detail = r.json().get("detail", "")
                except Exception:  # noqa: BLE001
                    pass
                return {"ok": False, "status": 502 if r.status_code >= 500 else r.status_code,
                        "error": f"assistant error {r.status_code} {detail}".strip()}
            j = r.json()
            reply = j.get("reply") or reply
            model = j.get("model") or model
            tools = [t for t in (j.get("tools") or []) if isinstance(t, dict)]
            if not tools or all(t.get("name") == "local_done" for t in tools):
                break
            results = []
            for t in tools[:4]:
                res = await run_tool(adb, t)
                results.append(res)
                executed.append({"name": t.get("name"), "args": t.get("args") or {}, "ok": res["ok"],
                                 "detail": res["detail"]})
                await asyncio.sleep(0.6)  # let the UI settle before the next step / dump
    history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
    return {"ok": True, "reply": reply or "Done", "tools": executed, "history": history[-20:], "model": model}

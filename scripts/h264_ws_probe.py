#!/usr/bin/env python3
"""End-to-end probe of `/ws/h264` (what the browser's WebCodecs path sees).

    .venv/bin/python scripts/h264_ws_probe.py [--url ws://127.0.0.1:8787/ws/h264]
                                              [--seconds 12] [--clients 1]
                                              [--tap X,Y] [--out /tmp/ws.h264]

Measures: hello → first AU, input → next AU (the number that decides whether a
tap feels instant), AU cadence, bytes, and per-client drops. The captured
Annex-B file is decodable with `ffmpeg -i <file> -f null -`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import struct
import sys
import time
from urllib.parse import urlparse

import httpx
import websockets

AU_HEADER = struct.Struct("<BBHId")


async def client(idx: int, url: str, seconds: float, out_path: str | None, events: list) -> dict:
    t_connect = time.time()
    res = {"idx": idx, "aus": 0, "keys": 0, "bytes": 0, "gaps": [], "hello": None}
    last = None
    async with websockets.connect(url, max_size=16 * 1024 * 1024) as ws:
        out = open(out_path, "wb") if out_path else None
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=max(0.1, deadline - time.time()))
            except asyncio.TimeoutError:
                break
            now = time.time()
            if isinstance(msg, str):
                j = json.loads(msg)
                if j.get("type") == "hello":
                    res["hello"] = j
                    print(f"[c{idx}] hello codec={j['codec']} {j['width']}x{j['height']} "
                          f"device={j['device_width']}x{j['device_height']} "
                          f"gop_ready={j['gop_ready']} in {(now - t_connect) * 1000:.0f}ms")
                elif j.get("type") == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
                else:
                    print(f"[c{idx}] {j}")
                continue
            ver, flags, _r, seq, ts_us = AU_HEADER.unpack(msg[:AU_HEADER.size])
            payload = msg[AU_HEADER.size:]
            if out:
                out.write(payload)
            res["aus"] += 1
            res["keys"] += flags & 1
            res["bytes"] += len(payload)
            if res["aus"] == 1:
                res["first_au_ms"] = (now - t_connect) * 1000
                print(f"[c{idx}] first AU in {res['first_au_ms']:.0f}ms "
                      f"key={bool(flags & 1)} {len(payload)}B")
            if last:
                res["gaps"].append((now - last) * 1000)
            last = now
            events.append((now, seq, bool(flags & 1), len(payload)))
        if out:
            out.close()
    return res


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8787/ws/h264")
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--clients", type=int, default=1)
    ap.add_argument("--out", default="/tmp/ws.h264")
    ap.add_argument("--no-input", action="store_true")
    args = ap.parse_args()

    origin = urlparse(args.url)
    http = f"http://{origin.netloc}"
    events: list = []
    tasks = [
        asyncio.create_task(
            client(i, args.url, args.seconds, args.out if i == 0 else None, events)
        )
        for i in range(args.clients)
    ]

    input_marks: list[tuple[str, float]] = []
    if not args.no_input:
        await asyncio.sleep(2.5)
        async with httpx.AsyncClient(timeout=10) as hc:
            for label, path, body in (
                ("HOME", "/adb/key", {"keycode": "HOME"}),
                ("swipe-up", "/adb/swipe", {"x1": 540, "y1": 1800, "x2": 540, "y2": 700,
                                            "duration_ms": 160}),
                ("BACK", "/adb/key", {"keycode": "BACK"}),
            ):
                t = time.time()
                r = await hc.post(http + path, json=body)
                input_marks.append((label, t))
                print(f"[input] {label} -> {r.status_code} in {(time.time() - t) * 1000:.0f}ms")
                await asyncio.sleep(2.2)

    results = await asyncio.gather(*tasks)

    print("\n--- per-client ---")
    for r in results:
        gaps = r["gaps"]
        print(f"c{r['idx']}: aus={r['aus']} keys={r['keys']} "
              f"kb={r['bytes'] / 1024:.0f} first_au_ms={r.get('first_au_ms', 0):.0f} "
              f"gap_median={statistics.median(gaps) if gaps else 0:.0f}ms "
              f"gap_p90={statistics.quantiles(gaps, n=10)[8] if len(gaps) > 9 else 0:.0f}ms")

    print("\n--- input → next frame (host side) ---")
    events.sort()
    for label, t in input_marks:
        nxt = next((e for e in events if e[0] > t), None)
        if nxt:
            print(f"{label:>9}: {(nxt[0] - t) * 1000:.0f}ms  (seq={nxt[1]}, {nxt[3]}B)")
        else:
            print(f"{label:>9}: no frame observed")

    async with httpx.AsyncClient(timeout=10) as hc:
        st = (await hc.get(http + "/adb/h264/stats")).json()
    print("\n--- server stats ---")
    for k in ("running", "subscribers", "peak_subscribers", "segments", "restarts",
              "access_units", "keyframes", "fps", "kbps", "first_frame_ms", "gop_valid",
              "gop_aus", "gop_kb", "idle_flushes", "misflushes", "flush_tick_ms",
              "intra_gap_max_ms", "keyframe_requests", "errors",
              "last_error", "size", "codec"):
        print(f"{k:>18}: {st.get(k)}")
    if st.get("clients"):
        print(f"{'clients':>18}: {st['clients']}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

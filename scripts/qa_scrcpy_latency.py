#!/usr/bin/env python3
"""Host-side swipe→AU latency probe (same style as overnight scrcpy joins).

    .venv/bin/python scripts/qa_scrcpy_latency.py [--base http://127.0.0.1:8787] [--rounds 5]

Marks wall time at POST /adb/swipe, then waits for the next /ws/h264 AU.
Also records join→first AU and /adb/h264/stats. Writes JSON under demo/overnight/qa/.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import struct
import time
from pathlib import Path

import httpx
import websockets

AU_HDR = struct.Struct("<BBHId")


async def one_join(base: str, label: str, swipe_duration_ms: int = 80) -> dict:
    ws_url = base.replace("http://", "ws://").replace("https://", "wss://") + "/ws/h264"
    http = base
    t_connect = time.time()
    hello = None
    first_au_ms = None
    first_key_ms = None
    aus = 0
    events: list[tuple[float, int, bool, int]] = []

    async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
        # wait for hello + a couple of AUs so GOP is warm
        deadline = time.time() + 8
        while time.time() < deadline and aus < 3:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            now = time.time()
            if isinstance(msg, str):
                j = json.loads(msg)
                if j.get("type") == "hello":
                    hello = j
                continue
            ver, flags, _r, seq, ts = AU_HDR.unpack(msg[: AU_HDR.size])
            aus += 1
            if first_au_ms is None:
                first_au_ms = (now - t_connect) * 1000
            if first_key_ms is None and (flags & 1):
                first_key_ms = (now - t_connect) * 1000
            events.append((now, seq, bool(flags & 1), len(msg) - AU_HDR.size))

        # swipe and wait for next AU after the POST returns
        async with httpx.AsyncClient(timeout=15) as hc:
            t_swipe = time.time()
            r = await hc.post(
                http + "/adb/swipe",
                json={"x1": 540, "y1": 1800, "x2": 540, "y2": 700, "duration_ms": swipe_duration_ms},
            )
            swipe_http_ms = (time.time() - t_swipe) * 1000
            status = r.status_code

        next_au_ms = None
        deadline = time.time() + 3.0
        while time.time() < deadline:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=max(0.05, deadline - time.time()))
            except asyncio.TimeoutError:
                break
            now = time.time()
            if isinstance(msg, str):
                continue
            ver, flags, _r, seq, ts = AU_HDR.unpack(msg[: AU_HDR.size])
            aus += 1
            events.append((now, seq, bool(flags & 1), len(msg) - AU_HDR.size))
            if now > t_swipe and next_au_ms is None:
                next_au_ms = (now - t_swipe) * 1000
                break

    async with httpx.AsyncClient(timeout=10) as hc:
        stats = (await hc.get(http + "/adb/h264/stats")).json()

    return {
        "label": label,
        "source": (hello or {}).get("source") or stats.get("source"),
        "gop_ready": (hello or {}).get("gop_ready"),
        "join_to_first_au_ms": None if first_au_ms is None else round(first_au_ms, 1),
        "join_to_key_au_ms": None if first_key_ms is None else round(first_key_ms, 1),
        "swipe_http_ms": round(swipe_http_ms, 1),
        "swipe_http_status": status,
        "swipe_to_au_ms": None if next_au_ms is None else round(next_au_ms, 1),
        "swipe_duration_ms": swipe_duration_ms,
        "aus": aus,
        "stats_fps": stats.get("fps"),
        "stats_size": stats.get("size"),
        "stats_bitrate": stats.get("bitrate"),
        "scrcpy_max_size": stats.get("scrcpy_max_size"),
        "scrcpy_codec_options": stats.get("scrcpy_codec_options"),
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8787")
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--out", default="demo/overnight/qa")
    ap.add_argument("--tag", default="scrcpy-tuned")
    ap.add_argument("--swipe-ms", type=int, default=80)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # nudge producer up
    async with httpx.AsyncClient(timeout=15) as hc:
        await hc.post(args.base + "/adb/h264/keyframe")
    await asyncio.sleep(1.5)

    results = []
    for i in range(args.rounds):
        label = f"join{i+1}_{'warm' if i else 'coldish'}"
        r = await one_join(args.base, label, swipe_duration_ms=args.swipe_ms)
        print(label, "swipe→AU", r["swipe_to_au_ms"], "ms", "source", r["source"], "size", r["stats_size"])
        results.append(r)
        await asyncio.sleep(0.6)

    swipes = [r["swipe_to_au_ms"] for r in results if r["swipe_to_au_ms"] is not None]
    summary = {
        "tag": args.tag,
        "swipe_duration_ms": args.swipe_ms,
        "swipe_to_au_ms": swipes,
        "median_ms": round(statistics.median(swipes), 1) if swipes else None,
        "min_ms": round(min(swipes), 1) if swipes else None,
        "max_ms": round(max(swipes), 1) if swipes else None,
        "source": results[-1]["source"] if results else None,
        "size": results[-1]["stats_size"] if results else None,
        "bitrate": results[-1]["stats_bitrate"] if results else None,
        "scrcpy_max_size": results[-1].get("scrcpy_max_size") if results else None,
        "scrcpy_codec_options": results[-1].get("scrcpy_codec_options") if results else None,
        "results": results,
        "glass_to_glass_under_100ms": bool(swipes) and statistics.median(swipes) < 100,
    }
    path = out / f"latency-{args.tag}.json"
    path.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("tag", "median_ms", "min_ms", "max_ms", "source", "size", "glass_to_glass_under_100ms")}, indent=2))
    print("wrote", path)


if __name__ == "__main__":
    asyncio.run(main())

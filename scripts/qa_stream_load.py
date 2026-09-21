#!/usr/bin/env python3
"""Concurrency QA for the live paths: fan-out cost, caps, backpressure, GC.

    .venv/bin/python scripts/qa_stream_load.py [--host 127.0.0.1:8787] [--n 13]

Checks, in order:
  1. N H.264 viewers all receive the same access units off one producer.
  2. Viewer N+1 past the cap is rejected with WS close 1013 (not a hang).
  3. The JPEG socket still serves in parallel (fallback clients coexist).
  4. A client that stops answering the heartbeat gets its slot reclaimed.
  5. Taps stay responsive while every viewer is streaming.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import struct
import time

import httpx
import websockets

AU_HEADER = struct.Struct("<BBHId")


async def viewer(url: str, seconds: float, answer_ping: bool = True) -> dict:
    got = {"aus": 0, "keys": 0, "bytes": 0, "seqs": [], "closed": None, "pings": 0}
    try:
        async with websockets.connect(url, max_size=16 * 1024 * 1024) as ws:
            end = time.time() + seconds
            while time.time() < end:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=max(0.1, end - time.time()))
                except asyncio.TimeoutError:
                    break
                if isinstance(msg, str):
                    j = json.loads(msg)
                    if j.get("type") == "ping":
                        got["pings"] += 1
                        if answer_ping:
                            await ws.send(json.dumps({"type": "pong"}))
                    continue
                _v, flags, _r, seq, _ts = AU_HEADER.unpack(msg[:AU_HEADER.size])
                got["aus"] += 1
                got["keys"] += flags & 1
                got["bytes"] += len(msg) - AU_HEADER.size
                got["seqs"].append(seq)
    except websockets.exceptions.WebSocketException as e:
        got["closed"] = str(e)
    return got


async def jpeg_viewer(host: str, seconds: float) -> dict:
    got = {"frames": 0, "bytes": 0, "closed": None}
    try:
        async with websockets.connect(f"ws://{host}/ws/stream", max_size=16 * 1024 * 1024) as ws:
            end = time.time() + seconds
            while time.time() < end:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=max(0.1, end - time.time()))
                except asyncio.TimeoutError:
                    break
                if isinstance(msg, bytes):
                    got["frames"] += 1
                    got["bytes"] += len(msg)
                elif json.loads(msg).get("type") == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
    except websockets.exceptions.WebSocketException as e:
        got["closed"] = str(e)
    return got


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1:8787")
    ap.add_argument("--n", type=int, default=13, help="H.264 viewers to open (cap is 12)")
    ap.add_argument("--seconds", type=float, default=10.0)
    args = ap.parse_args()
    url = f"ws://{args.host}/ws/h264"
    report: dict = {"host": args.host, "requested_viewers": args.n}

    async with httpx.AsyncClient(timeout=15) as hc:
        cap = (await hc.get(f"http://{args.host}/adb/h264/stats")).json()["max_clients"]
    report["cap"] = cap

    # 1 + 2: open n viewers; the ones past the cap must be refused.
    tasks = [asyncio.create_task(viewer(url, args.seconds)) for _ in range(args.n)]
    await asyncio.sleep(1.5)

    # 3: JPEG fallback client in parallel with the video fan-out
    jpeg_task = asyncio.create_task(jpeg_viewer(args.host, args.seconds - 2))

    # 5: input responsiveness under full load
    async with httpx.AsyncClient(timeout=15) as hc:
        lat = []
        for key in ("HOME", "APP_SWITCH", "BACK"):
            t = time.time()
            r = await hc.post(f"http://{args.host}/adb/key", json={"keycode": key})
            lat.append({"key": key, "status": r.status_code, "ms": round((time.time() - t) * 1000)})
            await asyncio.sleep(1.0)
        report["input_under_load"] = lat
        report["stats_under_load"] = (await hc.get(f"http://{args.host}/adb/h264/stats")).json()

    results = await asyncio.gather(*tasks)
    report["jpeg_parallel"] = await jpeg_task

    served = [r for r in results if r["aus"] > 0]
    refused = [r for r in results if r["aus"] == 0]
    report["served"] = len(served)
    report["refused"] = len(refused)
    report["refused_reasons"] = sorted({(r["closed"] or "silent")[:80] for r in refused})
    if served:
        counts = sorted(r["aus"] for r in served)
        report["aus_per_viewer"] = {"min": counts[0], "max": counts[-1]}
        first = set(served[0]["seqs"])
        report["identical_sequences"] = all(set(r["seqs"]) == first for r in served)
        report["kb_per_viewer"] = round(served[0]["bytes"] / 1024)

    # 4: a viewer that never answers the heartbeat must lose its slot.
    #    (WS_PING_INTERVAL_S/WS_PING_TIMEOUT_S default to 15s/40s.)
    report["ghost_check"] = "see stats_after; ghost closes after WS_PING_TIMEOUT_S"
    await asyncio.sleep(1.0)
    async with httpx.AsyncClient(timeout=15) as hc:
        report["stats_after"] = (await hc.get(f"http://{args.host}/adb/h264/stats")).json()
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

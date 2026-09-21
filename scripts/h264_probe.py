#!/usr/bin/env python3
"""Headless probe for the H.264 live path — no browser required.

    .venv/bin/python scripts/h264_probe.py [seconds] [--tap X,Y] [--late-join]

Prints per-access-unit cadence, keyframe placement, input→frame latency and the
broker's own stats, then writes the raw Annex-B stream to /tmp/probe.h264 so it
can be checked with a real decoder (ffprobe) if one is around.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adb_client import AdbClient  # noqa: E402


async def _drain(sub, out, label, tag_time=None, stop_at=None):
    first = None
    count = 0
    keys = 0
    while True:
        if stop_at and time.time() > stop_at:
            return first, count, keys
        try:
            au = await asyncio.wait_for(sub.queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        sub.took(au)
        count += 1
        keys += au.key
        out.write(au.data)
        now = time.time()
        if first is None:
            first = now
            print(f"[{label}] first AU after {(now - tag_time) * 1000:.0f}ms "
                  f"key={au.key} bytes={au.size}")
        if count <= 6 or au.key or count % 25 == 0:
            print(f"[{label}] #{count} seq={au.seq} key={au.key} "
                  f"bytes={au.size} ts={au.ts_us / 1000:.0f}ms")


async def main() -> None:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else 10.0
    tap = None
    for a in sys.argv[1:]:
        if a.startswith("--tap"):
            tap = a.split("=", 1)[1] if "=" in a else None
    late_join = "--late-join" in sys.argv

    adb = AdbClient()
    broker = adb.h264
    out = open("/tmp/probe.h264", "wb")
    t0 = time.time()
    async with broker.subscribe("probe") as sub:
        deadline = time.time() + seconds
        drain = asyncio.create_task(_drain(sub, out, "main", t0, deadline))

        await asyncio.sleep(2.0)
        # Motion so the encoder has something to push.
        t_in = time.time()
        await adb.key("HOME")
        print(f"[input] HOME sent at +{(t_in - t0) * 1000:.0f}ms "
              f"(rc in {(time.time() - t_in) * 1000:.0f}ms)")
        await asyncio.sleep(1.2)
        t_in = time.time()
        await adb.swipe(540, 1800, 540, 700, 180)
        print(f"[input] swipe sent at +{(t_in - t0) * 1000:.0f}ms")

        if late_join:
            await asyncio.sleep(2.0)
            t_join = time.time()
            async with broker.subscribe("late") as sub2:
                late_out = open("/tmp/probe-late.h264", "wb")
                got = await _drain(sub2, late_out, "late", t_join,
                                   stop_at=min(deadline, time.time() + 6))
                late_out.close()
                print(f"[late] frames={got[1]} keys={got[2]}")

        await drain
    out.close()

    st = broker.stats()
    print("\n--- broker stats ---")
    for k, v in st.items():
        print(f"{k:>18}: {v}")
    print(f"\nwrote /tmp/probe.h264 ({os.path.getsize('/tmp/probe.h264')} bytes)")
    await broker.aclose()
    await adb.frames.aclose()


if __name__ == "__main__":
    asyncio.run(main())

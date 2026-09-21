#!/usr/bin/env python3
"""A/B the two live paths against the *same* device events, simultaneously.

    .venv/bin/python scripts/qa_latency_ab.py [--url http://127.0.0.1:8787/]
                                              [--rounds 3]

Sequential A/B is useless here: a swiftshader emulator's app-launch time varies
by seconds, which swamps any transport difference. So this opens two browser
pages at once — one on H.264/WebCodecs, one with WebCodecs hidden so it lands
on the JPEG socket — fires one input over HTTP, and races their canvases. Same
device, same event, same instant: the difference is the transport.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

CANVAS_HASH = """
() => {
  const c = document.getElementById('liveCanvas');
  if (!c.width) return null;
  const t = document.createElement('canvas');
  t.width = 16; t.height = 32;
  const tx = t.getContext('2d');
  tx.drawImage(c, 0, 0, 16, 32);
  const d = tx.getImageData(0, 0, 16, 32).data;
  let h = '';
  for (let i = 0; i < d.length; i += 16) h += (d[i] >> 4).toString(16);
  return h;
}
"""

EVENTS = [
    ("home", "/adb/key", {"keycode": "HOME"}),
    ("open_gmail", "/adb/tap", {"x": 162, "y": 987}),
    ("back", "/adb/key", {"keycode": "BACK"}),
    ("drawer", "/adb/swipe", {"x1": 540, "y1": 1900, "x2": 540, "y2": 700, "duration_ms": 150}),
    ("home2", "/adb/key", {"keycode": "HOME"}),
    ("recents", "/adb/key", {"keycode": "APP_SWITCH"}),
]


async def watch(page, baseline, t0, timeout_s=8.0):
    """ms from t0 until this page's canvas paints something new."""
    while time.time() - t0 < timeout_s:
        h = await page.evaluate(CANVAS_HASH)
        if h and h != baseline:
            return round((time.time() - t0) * 1000), h
        await asyncio.sleep(0.02)
    return None, baseline


async def open_viewer(pw, url: str, webcodecs: bool):
    browser = await pw.chromium.launch()
    page = await browser.new_page(viewport={"width": 900, "height": 900})
    if not webcodecs:
        await page.add_init_script("delete window.VideoDecoder; delete window.EncodedVideoChunk;")
    await page.goto(url, wait_until="domcontentloaded")
    await page.evaluate("""() => { window.__qa = {
        transport: () => transport, frames: () => h264.frames,
        pokes: () => h264.pokes, decodeMs: () => h264.decodeMs,
        hud: () => streamHud.textContent }; }""")
    want = "h264" if webcodecs else "ws"
    for _ in range(80):
        if await page.evaluate("() => window.__qa.transport()") == want:
            if await page.evaluate(CANVAS_HASH):
                break
        await asyncio.sleep(0.25)
    return browser, page


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8787/")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--out", default="demo/overnight/qa")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base_http = args.url.rstrip("/")

    async with async_playwright() as pw:
        vb, video = await open_viewer(pw, args.url, True)
        jb, jpeg = await open_viewer(pw, args.url, False)
        modes = {
            "h264": await video.evaluate("() => window.__qa.transport()"),
            "jpeg": await jpeg.evaluate("() => window.__qa.transport()"),
        }
        print("transports:", modes)

        paired: dict[str, list[tuple[int | None, int | None]]] = {n: [] for n, _, _ in EVENTS}
        async with httpx.AsyncClient(timeout=20) as hc:
            for r in range(args.rounds):
                for name, path, body in EVENTS:
                    await asyncio.sleep(2.0)     # let the screen settle
                    b_v = await video.evaluate(CANVAS_HASH)
                    b_j = await jpeg.evaluate(CANVAS_HASH)
                    t0 = time.time()
                    await hc.post(base_http + path, json=body)
                    got = await asyncio.gather(
                        watch(video, b_v, t0), watch(jpeg, b_j, t0)
                    )
                    paired[name].append((got[0][0], got[1][0]))
                    print(f"round {r + 1} {name:>11}: h264={got[0][0]}ms jpeg={got[1][0]}ms")

        report = {
            "url": args.url,
            "when": time.strftime("%Y-%m-%d %H:%M:%S"),
            "rounds": args.rounds,
            "transports": modes,
            "paired_ms": {k: v for k, v in paired.items()},
            "video_hud": await video.evaluate("() => window.__qa.hud()"),
            "jpeg_hud": await jpeg.evaluate("() => window.__qa.hud()"),
            "video_frames": await video.evaluate("() => window.__qa.frames()"),
            "video_decode_ms": await video.evaluate("() => window.__qa.decodeMs()"),
            "jpeg_pokes_used_by_video": await video.evaluate("() => window.__qa.pokes()"),
        }
        await video.screenshot(path=str(out / "ab-h264.png"))
        await jpeg.screenshot(path=str(out / "ab-jpeg.png"))
        await vb.close()
        await jb.close()

    flat_v = [v for vs in paired.values() for v, _ in vs if v is not None]
    flat_j = [j for vs in paired.values() for _, j in vs if j is not None]
    wins = sum(1 for vs in paired.values() for v, j in vs
               if v is not None and j is not None and v < j)
    total = sum(1 for vs in paired.values() for v, j in vs if v is not None and j is not None)
    report["summary"] = {
        "median_h264_ms": round(statistics.median(flat_v)) if flat_v else None,
        "median_jpeg_ms": round(statistics.median(flat_j)) if flat_j else None,
        "h264_faster_events": f"{wins}/{total}",
        "per_event_median": {
            k: {
                "h264": round(statistics.median([v for v, _ in vs if v is not None]))
                if any(v is not None for v, _ in vs) else None,
                "jpeg": round(statistics.median([j for _, j in vs if j is not None]))
                if any(j is not None for _, j in vs) else None,
            }
            for k, vs in paired.items()
        },
    }
    (out / "latency-ab.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["summary"], indent=2))
    print("\nevent          H.264     JPEG")
    for k, m in report["summary"]["per_event_median"].items():
        print(f"{k:>12}  {str(m['h264']) + 'ms':>8} {str(m['jpeg']) + 'ms':>8}")


if __name__ == "__main__":
    asyncio.run(main())

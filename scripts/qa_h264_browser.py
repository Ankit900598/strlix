#!/usr/bin/env python3
"""Browser QA for the H.264 viewer: does a real Chromium actually decode it?

    .venv/bin/python scripts/qa_h264_browser.py [--url http://127.0.0.1:8787/]
                                                [--out demo/overnight/qa]

Drives the page like a user: waits for the transport to flip to H.264, taps the
canvas, presses HOME, and reports decoded-frame counts, the HUD readout, and
tap-to-pixels latency measured from *painted canvas pixels* (it hashes the
canvas, so a stuck frame cannot pass).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from playwright.async_api import async_playwright

PROBE = """
() => ({
  transport: window.__qa.transport(),
  frames: window.__qa.frames(),
  fps: window.__qa.fps(),
  kbps: window.__qa.kbps(),
  hud: document.getElementById('streamHud').textContent,
  badge: document.getElementById('streamBadge').textContent.trim(),
  stamp: document.getElementById('shotStamp').textContent,
  canvas: [document.getElementById('liveCanvas').width,
           document.getElementById('liveCanvas').height],
  hidden: document.getElementById('liveCanvas').hidden,
})
"""

# Cheap perceptual hash of the painted canvas: downscale to 16x32 greyscale.
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


async def wait_for_change(page, baseline, timeout_s=6.0):
    """Return ms until the painted canvas actually changes (None on timeout)."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        h = await page.evaluate(CANVAS_HASH)
        if h and h != baseline:
            return round((time.time() - t0) * 1000), h
        await asyncio.sleep(0.03)
    return None, baseline


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8787/")
    ap.add_argument("--out", default="demo/overnight/qa")
    ap.add_argument("--keep", type=float, default=6.0, help="seconds to watch the stream")
    ap.add_argument("--no-webcodecs", action="store_true",
                    help="hide VideoDecoder to exercise the JPEG fallback ladder")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"url": args.url, "started": time.strftime("%Y-%m-%d %H:%M:%S")}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        page = await browser.new_page(viewport={"width": 1280, "height": 1000})
        if args.no_webcodecs:
            await page.add_init_script(
                "delete window.VideoDecoder; delete window.EncodedVideoChunk;")
            report["mode"] = "jpeg-fallback"
        logs: list[str] = []
        page.on("console", lambda m: logs.append(f"{m.type}: {m.text}"))
        page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))

        await page.goto(args.url, wait_until="domcontentloaded")
        # Test hooks into the page's own state (no duplicate bookkeeping).
        await page.evaluate("""() => {
          window.__qa = {
            transport: () => transport,
            frames: () => h264.frames,
            fps: () => Math.round(h264.fps),
            kbps: () => Math.round(h264.kbps),
            supported: () => H264_OK,
            latency: () => h264.latency,
          };
        }""")
        report["webcodecs_supported"] = await page.evaluate("() => window.__qa.supported()")
        if args.no_webcodecs:
            # Fallback run: succeed on the JPEG ladder, not on H.264.
            assert not report["webcodecs_supported"], "VideoDecoder should be hidden"

        # 1. transport upgrade
        t0 = time.time()
        upgraded = False
        while time.time() - t0 < 20:
            st = await page.evaluate(PROBE)
            if st["transport"] == "h264" and st["frames"] > 0:
                upgraded = True
                break
            await asyncio.sleep(0.25)
        report["upgrade_ms"] = round((time.time() - t0) * 1000) if upgraded else None
        report["upgraded_to_h264"] = upgraded
        report["after_upgrade"] = await page.evaluate(PROBE)
        await page.screenshot(path=str(out / "h264-01-live.png"))

        # 2. input → painted pixels, measured on the canvas.
        #    Coordinates are device pixels mapped through the page's own
        #    viewRect, so this tests the real mapping instead of guessing.
        async def click_device(dx: int, dy: int):
            pt = await page.evaluate(
                """([dx, dy]) => {
                  const sr = screenEl.getBoundingClientRect();
                  return [sr.left + viewRect.left + dx * viewRect.scale,
                          sr.top + viewRect.top + dy * viewRect.scale];
                }""", [dx, dy])
            await page.mouse.click(pt[0], pt[1])

        # Land on the launcher first — a tap test that starts from Recents or a
        # half-open app measures the phone's state, not the pipeline.
        await page.click('button[data-key="HOME"]')
        await asyncio.sleep(2.0)
        await page.screenshot(path=str(out / "h264-01b-home.png"))

        base = await page.evaluate(CANVAS_HASH)
        await click_device(162, 987)          # Gmail on the home grid
        ms, base = await wait_for_change(page, base)
        report["tap_to_pixels_ms"] = ms
        report["tap_stamp"] = await page.evaluate("() => shotStamp.textContent")
        await asyncio.sleep(0.8)
        await page.screenshot(path=str(out / "h264-02-after-tap.png"))

        await asyncio.sleep(0.8)
        base = await page.evaluate(CANVAS_HASH)
        await page.click('button[data-key="HOME"]')
        ms_home, base = await wait_for_change(page, base)
        report["home_to_pixels_ms"] = ms_home
        await asyncio.sleep(1.2)
        await page.screenshot(path=str(out / "h264-03-home.png"))

        # 3. swipe (drag) still maps correctly on the video canvas
        box = await page.locator("#touchLayer").bounding_box()
        base = await page.evaluate(CANVAS_HASH)
        await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.78)
        await page.mouse.down()
        await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.30, steps=12)
        await page.mouse.up()
        ms_swipe, base = await wait_for_change(page, base)
        report["swipe_to_pixels_ms"] = ms_swipe
        await asyncio.sleep(0.8)
        await page.screenshot(path=str(out / "h264-04-swipe.png"))

        # 4. steady state
        await asyncio.sleep(args.keep)
        report["steady"] = await page.evaluate(PROBE)
        report["reported_latency_ms"] = await page.evaluate("() => window.__qa.latency()")
        report["swipe_stamp"] = await page.evaluate("() => shotStamp.textContent")

        # 5. background/restore must not strand the viewer
        await page.evaluate("""() => { Object.defineProperty(document, 'visibilityState',
            { value: 'hidden', configurable: true });
            document.dispatchEvent(new Event('visibilitychange')); }""")
        await asyncio.sleep(1.5)
        await page.evaluate("""() => { Object.defineProperty(document, 'visibilityState',
            { value: 'visible', configurable: true });
            document.dispatchEvent(new Event('visibilitychange')); }""")
        await asyncio.sleep(3.5)
        report["after_restore"] = await page.evaluate(PROBE)
        base2 = await page.evaluate(CANVAS_HASH)
        await page.click('button[data-key="APP_SWITCH"]')
        ms_restore, _ = await wait_for_change(page, base2, timeout_s=8)
        report["restore_input_to_pixels_ms"] = ms_restore
        await page.screenshot(path=str(out / "h264-05-after-restore.png"))

        report["console"] = logs[-25:]
        await browser.close()

    (out / "h264-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

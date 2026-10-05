import os
"""Live E2E for the 'normal feel' fix: drives the AFD stream viewer in headless
Chromium with real CDP touch input (mobile 390x844), checks device state over
adb (via ssh to the VM) and measures first-frame + tap-to-frame latency.
Usage: feel_e2e.py <label> [viewer-version-tag]
"""
import asyncio, json, re, subprocess, sys, time, statistics
from playwright.async_api import async_playwright

LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"
TAG = sys.argv[2] if len(sys.argv) > 2 else str(int(time.time()))
STREAM = f"https://strlix-stream-euapehawccbcbuer.z02.azurefd.net/?v={TAG}"
OUT = f"/workspace/strlix-overnight/sprint-1005/{LABEL}/"
subprocess.run(["mkdir", "-p", OUT])
SSH = ["ssh", "-i", __import__("os").environ.get("STRLIX_VM_KEY", "~/.ssh/strlix-vm.pem"), "-o", "StrictHostKeyChecking=accept-new",
       "-o", "ConnectTimeout=15", __import__("os").environ["STRLIX_VM"]]
DW, DH = 1080, 2400
R = {"label": LABEL, "url": STREAM, "steps": {}, "lat": {}, "console_errors": []}


def sh(cmd, timeout=60):
    p = subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=timeout)
    return p.stdout


def adb(cmd, timeout=60):
    return sh("adb -s emulator-5554 shell " + cmd, timeout)


def ui_nodes():
    x = sh("adb shell uiautomator dump /sdcard/u.xml >/dev/null 2>&1; adb shell cat /sdcard/u.xml")
    out = []
    for m in re.finditer(r"<node [^>]*>", x):
        n = m.group(0)
        g = lambda k: (re.search(k + r'="([^"]*)"', n) or [None, ""])[1]
        out.append({"text": g("text"), "desc": g("content-desc"), "id": g("resource-id"), "b": g("bounds"), "pkg": g("package")})
    return out


def dev_state():
    nodes = ui_nodes()
    url = next((n["text"] for n in nodes if n["id"].endswith("url_bar")), None)
    tabs = None
    for n in nodes:
        m = re.search(r"(\d+) (open )?tabs?", n["desc"]) if n["id"].endswith("tab_switcher_button") else None
        if m: tabs = int(m.group(1))
    top = adb("dumpsys activity activities | grep -m1 topResumedActivity").strip()
    rec = adb("dumpsys activity recents | grep 'Recent #'")
    tasks = [l.strip() for l in rec.splitlines() if "type=home" not in l]
    overview = any(n["text"] in ("Clear all", "Select", "Screenshot") or "overview" in n["id"] for n in nodes)
    pkgs = sorted({n["pkg"] for n in nodes})
    return {"url": url, "tabs": tabs, "top": top[-90:], "recent_tasks": len(tasks), "tasks": [t[-60:] for t in tasks],
            "overview": overview, "pkgs": pkgs}


FRAME_PROBE = """
(() => {
  if (window.__fp) return;
  const fp = window.__fp = { changes: [], ptr: [], last: null };
  const c = document.getElementById('liveCanvas');
  const s = document.createElement('canvas'); s.width = 54; s.height = 120;
  const sx = s.getContext('2d', { willReadFrequently: true });
  for (const t of ['pointerdown','pointerup']) document.addEventListener(t, e => fp.ptr.push({t, at: performance.now(), type: e.pointerType}), true);
  function tick() {
    try {
      if (c && c.width) {
        sx.drawImage(c, 0, 0, 54, 120);
        const d = sx.getImageData(0, 0, 54, 120).data;
        if (fp.last) { let sum = 0; for (let i = 0; i < d.length; i += 4) sum += Math.abs(d[i]-fp.last[i]) + Math.abs(d[i+1]-fp.last[i+1]) + Math.abs(d[i+2]-fp.last[i+2]);
          if (sum > 1500) fp.changes.push({ at: performance.now(), sum }); }
        fp.last = d.slice();
      }
    } catch (e) {}
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})();
"""


def link_xy():
    """Centre of the first in-page link in Chrome's web content (uiautomator)."""
    x = sh("adb shell uiautomator dump /sdcard/u.xml >/dev/null 2>&1; adb shell cat /sdcard/u.xml")
    for m in re.finditer(r"<node [^>]*>", x):
        n = m.group(0)
        if 'clickable="true"' not in n or 'package="com.android.chrome"' not in n or 'class="android.view.View"' not in n: continue
        b = re.findall(r"\d+", (re.search(r'bounds="([^"]*)"', n) or [None, ""])[1])
        if len(b) != 4: continue
        x1, y1, x2, y2 = map(int, b)
        if 600 < y1 < 2100 and (x2 - x1) > 60 and (y2 - y1) > 30:
            return (x1 + x2) // 2, (y1 + y2) // 2
    return 539, 1200


class Phone:
    def __init__(self, page, cdp):
        self.page, self.cdp = page, cdp

    async def box(self):
        return await self.page.locator("#liveCanvas").bounding_box()

    async def to_client(self, x, y):
        b = await self.box()
        return b["x"] + x * b["width"] / DW, b["y"] + y * b["height"] / DH

    async def touch(self, typ, cx=None, cy=None, ts=None):
        pts = [] if typ in ("touchEnd", "touchCancel") else [{"x": cx, "y": cy, "id": 1, "radiusX": 4, "radiusY": 4, "force": 1}]
        ev = {"type": typ, "touchPoints": pts}
        if ts is not None and os.environ.get("CDP_TS", "1") == "1":
            ev["timestamp"] = ts   # OS-like event time (what a real phone's touch stack provides)
        await self.cdp.send("Input.dispatchTouchEvent", ev)

    async def tap_client(self, cx, cy, hold=0.06):
        await self.touch("touchStart", cx, cy); await asyncio.sleep(hold); await self.touch("touchEnd")

    async def tap(self, x, y, hold=0.06):
        cx, cy = await self.to_client(x, y); await self.tap_client(cx, cy, hold)

    async def drag_client(self, x1, y1, x2, y2, ms=250, steps=14, hold_end=0.0):
        # Like a real touchscreen: events leave on schedule, we don't wait for
        # the renderer to ack each one (awaiting made sends drift ~35 ms/step).
        t0 = time.time(); dt = ms / 1000 / steps; tasks = []
        tasks.append(asyncio.ensure_future(self.touch("touchStart", x1, y1, ts=t0)))
        for i in range(1, steps + 1):
            await asyncio.sleep(max(0, t0 + i * dt - time.time()))
            tasks.append(asyncio.ensure_future(self.touch("touchMove", x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps, ts=t0 + i * dt)))
        if hold_end: await asyncio.sleep(hold_end)
        tasks.append(asyncio.ensure_future(self.touch("touchEnd", ts=t0 + steps * dt + hold_end)))
        await asyncio.gather(*tasks)

    async def drag(self, x1, y1, x2, y2, **kw):
        a = await self.to_client(x1, y1); b = await self.to_client(x2, y2)
        await self.drag_client(*a, *b, **kw)

    async def rail(self, key):
        btn = self.page.locator(f'.navbar button[data-key="{key}"]')
        if await btn.count() and await btn.is_visible():
            bb = await btn.bounding_box(); await self.tap_client(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
            return True
        return False

    async def mark(self):
        return await self.page.evaluate("({n: __fp.changes.length, p: __fp.ptr.length})")

    async def latency(self, m, wait=2.5):
        await asyncio.sleep(wait)
        d = await self.page.evaluate("""(m) => { const p = __fp.ptr.slice(m.p); const c = __fp.changes.slice(m.n);
            const down = p.find(x => x.t==='pointerdown'); const up = p.find(x => x.t==='pointerup');
            const first = c.find(x => down && x.at > down.at);
            return { down_to_frame: (first && down) ? Math.round(first.at - down.at) : null,
                     up_to_frame: (first && up) ? Math.round(first.at - up.at) : null, changes: c.length, ptype: down && down.type }; }""", m)
        return d

    async def shot(self, name):
        await self.page.screenshot(path=OUT + name + ".png")


async def main():
    t_all = time.time()
    # --- setup on device (not user input): clean Chrome to 2 tabs, launcher home
    adb("am force-stop com.android.chrome"); adb("input keyevent HOME")
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--autoplay-policy=no-user-gesture-required"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                                  user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Mobile Safari/537.36")
        page = await ctx.new_page()
        page.on("console", lambda m: R["console_errors"].append(m.text[:200]) if m.type == "error" else None)
        page.on("pageerror", lambda e: R["console_errors"].append("pageerror " + str(e)[:200]))
        cdp = await ctx.new_cdp_session(page)
        ph = Phone(page, cdp)
        # first frame (3 cold loads)
        ffs = []
        for i in range(3):
            t0 = time.time()
            await page.goto(STREAM + f"&ff={i}", wait_until="domcontentloaded", timeout=60000)
            t_dom = time.time() - t0
            for _ in range(400):
                ok = await page.evaluate("""() => { const c=document.getElementById('liveCanvas'); return !!(c && !c.hidden && c.width>0); }""")
                if ok: break
                await asyncio.sleep(0.05)
            ffs.append({"dom_s": round(t_dom, 2), "first_frame_s": round(time.time() - t0, 2), "ok": ok})
        R["first_frame"] = ffs
        await asyncio.sleep(2.5)
        await page.evaluate(FRAME_PROBE)
        R["viewer_build"] = await page.evaluate("(document.documentElement.outerHTML.match(/viewerBuild[^,]{0,40}/)||[''])[0]")
        R["phone_fs"] = await page.evaluate("document.documentElement.classList.contains('phone-fs')")
        R["canvas_box"] = await ph.box()
        await ph.shot("00-home")
        lat = R["lat"]

        # --- tap-to-frame: tap Chrome icon on home
        m = await ph.mark(); await ph.tap(665, 1968)
        lat["tap_chrome_icon"] = await ph.latency(m, 3.0)
        await asyncio.sleep(1)
        s = dev_state(); R["steps"]["open_chrome"] = {"ok": "chrome" in s["top"], **s}
        await ph.shot("01-chrome-open")

        # --- Back in Chrome after visiting 2 pages
        adb("am start -a android.intent.action.VIEW -d https://www.iana.org/help/example-domains com.android.chrome >/dev/null")
        await asyncio.sleep(5)
        s1 = dev_state()
        LX, LY = link_xy()
        m = await ph.mark(); await ph.tap(LX, LY)  # first in-page link (real tap)
        lat["tap_link"] = await ph.latency(m, 4.0)
        await asyncio.sleep(2)
        s2 = dev_state(); await ph.shot("02-page2")
        # Back via left-edge swipe (what a phone user does)
        cx0, cy0 = await ph.to_client(4, 1300)
        m = await ph.mark(); await ph.drag_client(cx0 + 1, cy0, cx0 + 160, cy0, ms=220)
        lat["edge_back"] = await ph.latency(m, 3.0)
        s3 = dev_state(); await ph.shot("03-after-edge-back")
        R["steps"]["back_edge"] = {"page1": s1["url"], "page2": s2["url"], "after": s3["url"], "top": s3["top"],
                                   "ok": bool(s1["url"] and s2["url"] and s3["url"] and s2["url"] != s1["url"] and s3["url"] == s1["url"])}
        # Forward again, then Back via on-screen Back button
        if s3["url"] and s3["url"] == s1["url"]:
            LX, LY = link_xy(); await ph.tap(LX, LY); await asyncio.sleep(5)
        s4 = dev_state()
        m = await ph.mark(); used = await ph.rail("BACK")
        lat["rail_back"] = await ph.latency(m, 3.0)
        s5 = dev_state(); await ph.shot("04-after-rail-back")
        R["steps"]["back_button"] = {"rail": used, "before": s4["url"], "after": s5["url"], "top": s5["top"],
                                     "ok": bool(s5["url"] and s4["url"] and s5["url"] == s1["url"] and s4["url"] != s1["url"])}

        # --- scroll (real drag) on a long page
        adb("am start -a android.intent.action.VIEW -d \"'https://en.m.wikipedia.org/wiki/Android_(operating_system)'\" com.android.chrome >/dev/null")
        await asyncio.sleep(6)
        a = sh("adb shell screencap -p | md5sum")
        m = await ph.mark(); await ph.drag(540, 1800, 540, 900, ms=300)
        lat["scroll"] = await ph.latency(m, 2.5)
        bsum = sh("adb shell screencap -p | md5sum")
        await ph.shot("05-after-scroll")
        R["steps"]["scroll"] = {"ok": a != bsum and "chrome" in dev_state()["top"], "frame_changes": lat["scroll"]["changes"]}

        # --- close a Chrome tab (tab switcher, swipe card away)
        # setup (not user input): scrolling down hid Chrome's toolbar; bring it back
        adb("input swipe 540 900 540 1600 200"); await asyncio.sleep(1.2)
        s6 = dev_state()
        m = await ph.mark(); await ph.tap(891, 201)  # tab switcher button
        lat["tab_switcher"] = await ph.latency(m, 3.0)
        await ph.shot("06-tab-switcher")
        nodes = ui_nodes()
        cards = [n for n in nodes if n["id"].endswith("tab_title") or n["id"].endswith("card_view") or n["id"].endswith("content_view")]
        R["steps"]["tab_switcher_nodes"] = [(n["id"].split("/")[-1], n["text"][:30], n["b"]) for n in cards][:8]
        closed_via = None
        card = next((n for n in nodes if n["id"].endswith("card_view") or n["id"].endswith("content_view")), None)
        if card:
            x1, y1, x2, y2 = map(int, re.findall(r"\d+", card["b"]))
            cxm, cym = (x1 + x2) // 2, (y1 + y2) // 2
            await ph.drag(cxm, cym, min(DW - 5, cxm + 520), cym, ms=260)  # swipe card sideways
            closed_via = "swipe"
        await asyncio.sleep(2.5)
        nodes2 = ui_nodes()
        s7tabs = None
        n_cards_before = len([n for n in nodes if n["id"].endswith("tab_title")])
        n_cards_after = len([n for n in nodes2 if n["id"].endswith("tab_title")])
        await ph.shot("07-after-close-tab")
        R["steps"]["close_tab"] = {"tabs_before": s6["tabs"], "cards_before": n_cards_before, "cards_after": n_cards_after,
                                   "via": closed_via, "ok": n_cards_after == n_cards_before - 1 and n_cards_before > 0}
        # leave switcher by tapping remaining card (or back)
        await ph.rail("BACK"); await asyncio.sleep(1.5)

        # --- Recents: (a) native swipe-up-and-hold from the bottom of the phone
        def chrome_tasks():
            return adb("dumpsys activity recents | grep -c 'A=10142:com.android.chrome'").strip()
        cxb, cyb = await ph.to_client(540, 2392)
        el = await page.evaluate(f"(() => {{ const e=document.elementFromPoint({cxb},{cyb}); return e ? (e.id||e.className||e.tagName) : null }})()")
        m = await ph.mark(); await ph.drag_client(cxb, cyb, cxb, cyb - 300, ms=350, steps=16, hold_end=0.7)
        lat["recents_gesture"] = await ph.latency(m, 2.5)
        r1 = dev_state(); await ph.shot("08-recents-gesture")
        R["steps"]["recents_gesture"] = {"bottom_element": el, "overview": r1["overview"], "top": r1["top"], "ok": r1["overview"]}
        # informational: swipe the live tile (the app we came from) away
        if os.environ.get("LIVETILE_INFO", "0") == "1":
            b_live = chrome_tasks()
            await ph.drag(540, 1300, 540, 300, ms=250); await asyncio.sleep(4)
            a_live = chrome_tasks(); await ph.shot("08a-after-livetile-dismiss")
            R["steps"]["recents_gesture_livetile_dismiss_info"] = {"chrome_before": b_live, "chrome_after": a_live, "dismissed": b_live == "1" and a_live == "0"}
        # leave Recents via Home button on the rail
        await ph.rail("HOME"); await asyncio.sleep(1.5)
        # (b) Recents button, then swipe the Chrome card away (real drag)
        adb("am start -a android.intent.action.VIEW -d https://example.com com.android.chrome >/dev/null"); await asyncio.sleep(4)
        before_chrome = chrome_tasks()
        m = await ph.mark(); used = await ph.rail("RECENTS_CLEAN")
        lat["recents_button"] = await ph.latency(m, 3.0)
        r2 = dev_state(); await ph.shot("08b-recents-button")
        R["steps"]["recents_button"] = {"rail": used, "overview": r2["overview"], "top": r2["top"], "ok": r2["overview"]}
        m = await ph.mark(); await ph.drag(540, 1300, 540, 300, ms=250)
        lat["recents_dismiss"] = await ph.latency(m, 2.0)
        await asyncio.sleep(3)
        after_chrome = chrome_tasks(); r3 = dev_state(); await ph.shot("09-after-dismiss")
        R["steps"]["recents_dismiss"] = {"chrome_tasks_before": before_chrome, "chrome_tasks_after": after_chrome,
                                         "overview_after": r3["overview"], "ok": before_chrome == "1" and after_chrome == "0"}
        adb("input keyevent HOME")
        R["hud"] = await page.evaluate("(document.getElementById('streamHud')||{}).textContent||''")
        await b.close()
    R["stream_health"] = json.loads(sh("curl -s localhost:8789/health") or "{}").get("h264", {})
    R["stream_health"] = {k: R["stream_health"].get(k) for k in ("source", "size", "fps", "keyframe_requests", "last_keyframe_why", "restarts", "errors", "first_frame_ms")}
    R["elapsed_s"] = round(time.time() - t_all, 1)
    vals = [v["up_to_frame"] for v in R["lat"].values() if v.get("up_to_frame") is not None]
    R["lat_summary"] = {"median_up_to_frame_ms": statistics.median(vals) if vals else None}
    json.dump(R, open(OUT + "result.json", "w"), indent=1)
    print(json.dumps(R, indent=1))

asyncio.run(main())

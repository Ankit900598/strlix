import sys
src = open("" + __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "feel_e2e.py") + "").read()
LBL = sys.argv[1] if len(sys.argv) > 1 else "rb"; N = int(sys.argv[2]) if len(sys.argv) > 2 else 6
sys.argv = ["x", "recents-" + LBL, LBL]
exec(src.split("async def main():")[0])
def chrome_tasks(): return adb("dumpsys activity recents | grep -c 'A=[0-9]*:com.android.chrome'").strip()
async def main():
    res = {"button": [], "gesture": []}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=__import__("os").environ.get("CHROME", "/usr/bin/google-chrome"))
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = await ctx.new_page(); cdp = await ctx.new_cdp_session(page); ph = Phone(page, cdp)
        await page.goto(STREAM, wait_until="domcontentloaded"); await asyncio.sleep(4)
        for i in range(N):
            for mode in ("button", "gesture"):
                adb("am start -n com.android.chrome/com.google.android.apps.chrome.Main >/dev/null"); await asyncio.sleep(3)
                before = chrome_tasks()
                if mode == "button":
                    await ph.rail("RECENTS_CLEAN"); await asyncio.sleep(2.0)
                else:
                    cxb, cyb = await ph.to_client(540, 2392)
                    await ph.drag_client(cxb, cyb, cxb, cyb - 300, ms=350, steps=16, hold_end=0.7); await asyncio.sleep(1.5)
                ov = dev_state()["overview"]
                await ph.drag(540, 1300, 540, 300, ms=250); await asyncio.sleep(2.5)
                after = chrome_tasks(); first = before != "0" and after == "0"
                if not first and ov and after == before and os.environ.get("SETTLE_RETRY", "1") == "1":
                    await asyncio.sleep(1.5)   # settle after a swallowed fling, then retry once
                    await ph.drag(540, 1300, 540, 300, ms=250); await asyncio.sleep(2.5); after = chrome_tasks()
                res[mode].append({"ov": ov, "first": first, "ok": before != "0" and after == "0"})
                if not res[mode][-1]["ok"]: await ph.shot(f"fail-{mode}-{i}")
                adb("input keyevent HOME"); await asyncio.sleep(1)
        await b.close()
    pace = json.loads(sh("curl -s localhost:8789/health") or "{}").get("touch_pacing")
    out = {m: f"{sum(x['ok'] for x in v)}/{len(v)} (first try {sum(x['first'] for x in v)}/{len(v)}, overview {sum(x['ov'] for x in v)}/{len(v)})" for m, v in res.items()}
    out["pacing"] = pace
    os.makedirs(OUT, exist_ok=True); json.dump({"summary": out, "runs": res}, open(OUT + "result.json", "w"), indent=1)
    print(json.dumps(out))
asyncio.run(main())

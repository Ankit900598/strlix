import sys, os
src = open("" + __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "feel_e2e.py") + "").read()
Q = sys.argv[1] if len(sys.argv) > 1 else ""
sys.argv = ["x", "lagprobe", "lag"]
exec(src.split("async def main():")[0])
import statistics as st
HOOK = """(() => { window.__sendLag = []; const S = WebSocket.prototype.send; WebSocket.prototype.send = function(d) {
  try { if (typeof d === 'string' && d.indexOf('"motion"') > 0) { const j = JSON.parse(d); window.__sendLag.push(Math.round(performance.now() - j.t)); } } catch (e) {}
  return S.call(this, d); }; })();"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=os.environ.get("CARGS","").split())
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = await ctx.new_page(); await page.add_init_script(HOOK); cdp = await ctx.new_cdp_session(page); ph = Phone(page, cdp)
        adb("input keyevent HOME")
        await page.goto(STREAM + Q, wait_until="domcontentloaded"); await asyncio.sleep(4)
        for i in range(4):
            await ph.drag(300, 1200, 800, 1200, ms=250); await asyncio.sleep(1.2)
            await ph.drag(800, 1200, 300, 1200, ms=250); await asyncio.sleep(1.2)
        L = await page.evaluate("__sendLag")
        hud = await page.evaluate("(document.getElementById('streamHud')||{}).textContent||''")
        await b.close()
    L.sort(); print(json.dumps({"q": Q, "n": len(L), "median": st.median(L), "p90": L[int(len(L)*.9)], "max": L[-1], "hud": hud}))
    adb("input keyevent HOME")
asyncio.run(main())

import asyncio, json, sys
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else "https://strlix-stream-euapehawccbcbuer.z02.azurefd.net/"
HOOK = """
(() => { window.__t = {}; const O = window.WebSocket;
  window.WebSocket = function(u, p) { const w = p ? new O(u, p) : new O(u);
    if (String(u).includes('/ws/h264')) { __t.ws_new = performance.now();
      w.addEventListener('open', () => __t.ws_open = performance.now());
      w.addEventListener('message', e => { if (typeof e.data === 'string') { if (!__t.hello) __t.hello = performance.now(); } else if (!__t.au) __t.au = performance.now(); }); }
    return w; };
  window.WebSocket.prototype = O.prototype; Object.assign(window.WebSocket, O);
  document.addEventListener('DOMContentLoaded', () => { __t.dcl = performance.now();
    const c = document.getElementById('liveCanvas'); const s = document.createElement('canvas'); s.width = 27; s.height = 60; const x = s.getContext('2d', {willReadFrequently: true});
    (function tick(){ try { if (c && c.width > 10 && !__t.paint) { x.drawImage(c,0,0,27,60); const d = x.getImageData(0,0,27,60).data; let sum=0; for (let i=0;i<d.length;i+=4) sum+=d[i]+d[i+1]+d[i+2]; if (sum>500) __t.paint = performance.now(); } } catch(e){} if (!__t.paint) requestAnimationFrame(tick); })(); });
})();
"""
async def main():
    res = []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=__import__("os").environ.get("CHROME", "/usr/bin/google-chrome"))
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        for k in range(int(sys.argv[2]) if len(sys.argv) > 2 else 3):
            pg = await ctx.new_page(); await pg.add_init_script(HOOK)
            await pg.goto(URL + ("&" if "?" in URL else "?") + "ffd=%d" % k, wait_until="domcontentloaded")
            for _ in range(100):
                await asyncio.sleep(0.1)
                if await pg.evaluate("!!__t.paint"): break
            t = await pg.evaluate("""(() => { const n = performance.getEntriesByType('navigation')[0];
               const r = {ttfb: n.responseStart, html_done: n.responseEnd, size_kb: Math.round(n.transferSize/1024)}; for (const k in __t) r[k] = __t[k]; for (const k in r) r[k] = Math.round(r[k]); return r; })()""")
            res.append(t); await pg.close(); await asyncio.sleep(1)
        await b.close()
    print(json.dumps(res))
asyncio.run(main())

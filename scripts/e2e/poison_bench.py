"""Recents poisoning bench (runs ON the VM against ws://127.0.0.1:8789/ws/h264).
Per trial: open Chrome, APP_SWITCH -> overview, optional deliberately-bad slow drag on the card, gap, then a good fling.
usage: poison_bench.py <poison 0|1> <gap_s> <runs>
"""
import asyncio, json, sys, time, subprocess, websockets, os
URL = os.environ.get("WS", "ws://127.0.0.1:8789/ws/h264")
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True).stdout
def chrome_tasks(): return sh("adb shell dumpsys activity recents | grep -c 'A=[0-9]*:com.android.chrome'").strip()
def line(x1,y1,x2,y2,n): return [(round(x1+(x2-x1)*i/n), round(y1+(y2-y1)*i/n)) for i in range(n+1)]
async def drag(ws, pts, dt):
    t0 = time.time()*1000
    await ws.send(json.dumps({"type":"motion","action":"DOWN","x":pts[0][0],"y":pts[0][1],"t":t0}))
    for i,(x,y) in enumerate(pts[1:],1):
        await asyncio.sleep(dt)
        await ws.send(json.dumps({"type":"motion","action":"MOVE","x":x,"y":y,"t":t0+i*dt*1000}))
    await ws.send(json.dumps({"type":"motion","action":"UP","x":pts[-1][0],"y":pts[-1][1],"t":t0+len(pts)*dt*1000}))
async def main():
    poison = sys.argv[1] == "1"; gap = float(sys.argv[2]); runs = int(sys.argv[3])
    res = []
    async with websockets.connect(URL, max_size=None) as ws:
        async def drain():
            try:
                async for m in ws:
                    if isinstance(m, str) and '"ping"' in m:
                        await ws.send(json.dumps({"type": "pong", "t": json.loads(m).get("t")}))
            except Exception: pass
        asyncio.create_task(drain())
        for r in range(runs):
            sh("adb shell am start -n com.android.chrome/com.google.android.apps.chrome.Main >/dev/null"); await asyncio.sleep(2.0)
            sh("adb shell input keyevent APP_SWITCH"); await asyncio.sleep(1.2)
            before = chrome_tasks()
            if poison:
                await drag(ws, line(540,1300,540,800,14), dt=0.05)   # slow, short: known to fail
                await asyncio.sleep(gap)
                mid = chrome_tasks()
            else:
                mid = before
            t = time.time()
            await drag(ws, line(540,1300,540,250,12), dt=0.012)
            await asyncio.sleep(1.2)
            after = chrome_tasks()
            res.append({"before": before, "mid": mid, "after": after, "ok": before != "0" and after == "0", "poison_dismissed": poison and mid == "0"})
            sh("adb shell input keyevent HOME"); await asyncio.sleep(0.8)
    print(json.dumps({"poison": poison, "gap": gap, "ok": sum(x["ok"] for x in res), "n": len(res), "runs": res}))
asyncio.run(main())

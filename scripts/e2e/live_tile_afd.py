"""Local (on VM) Recents experiments over /ws/h264 motion with real timing.
mode: 'app' = Recents by swipe-up-hold from inside Chrome (live tile); 'home' = from Home via APP_SWITCH.
"""
import asyncio, json, sys, time, subprocess, websockets
import os
URL = os.environ.get("WS", "ws://127.0.0.1:8789/ws/h264")
REMOTE = "127.0.0.1" not in URL
def sh(c):
    if REMOTE: return subprocess.run(["ssh","-i",__import__("os").environ.get("STRLIX_VM_KEY", "~/.ssh/strlix-vm.pem"),__import__("os").environ["STRLIX_VM"],c], capture_output=True, text=True).stdout
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout
def chrome_tasks(): return sh("adb shell dumpsys activity recents | grep -c 'A=[0-9]*:com.android.chrome'").strip()
async def drag(ws, pts, dt=0.016):
    t0 = time.time()*1000
    await ws.send(json.dumps({"type":"motion","action":"DOWN","x":pts[0][0],"y":pts[0][1],"t":t0}))
    for i,(x,y) in enumerate(pts[1:],1):
        await asyncio.sleep(dt)
        await ws.send(json.dumps({"type":"motion","action":"MOVE","x":x,"y":y,"t":t0+i*dt*1000}))
    await ws.send(json.dumps({"type":"motion","action":"UP","x":pts[-1][0],"y":pts[-1][1],"t":t0+len(pts)*dt*1000}))
def line(x1,y1,x2,y2,n): return [(round(x1+(x2-x1)*i/n), round(y1+(y2-y1)*i/n)) for i in range(n+1)]
async def main():
    mode = sys.argv[1]; runs = int(sys.argv[2]) if len(sys.argv)>2 else 3; settle = float(sys.argv[3]) if len(sys.argv)>3 else 1.0
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
            sh("adb shell am start -n com.android.chrome/com.google.android.apps.chrome.Main >/dev/null"); await asyncio.sleep(2.5)
            before = chrome_tasks()
            if mode == "app":
                # swipe up from bottom and hold -> overview
                pts = line(540,2390,540,1500,20) + [(540,1500)]*25
                await drag(ws, pts)
            else:
                sh("adb shell input keyevent HOME"); await asyncio.sleep(1.0)
                sh("adb shell input keyevent APP_SWITCH")
            await asyncio.sleep(settle)
            ov = "RecentsActivity" in sh("adb shell dumpsys activity activities | grep -m1 topResumedActivity") or "nexuslauncher" in sh("adb shell dumpsys activity activities | grep -m1 topResumedActivity")
            # fling the centre card up
            await drag(ws, line(540,1300,540,250,12), dt=0.012)
            await asyncio.sleep(1.2)
            after = chrome_tasks()
            res.append({"before": before, "after": after, "overview": ov, "ok": before != "0" and after == "0"})
            sh("adb shell input keyevent HOME"); await asyncio.sleep(0.8)
    print(json.dumps({"mode": mode, "settle": settle, "ok": sum(x["ok"] for x in res), "n": len(res), "runs": res}))
asyncio.run(main())

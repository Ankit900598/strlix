"""Tap -> first H.264 AU latency over /ws/h264 (motion over the same socket).
Usage: tap_probe.py <ws_url> [runs] [x y]. Before each run: force-stop Chrome,
HOME, idle 2.5 s (so the encoder is silent), then DOWN/UP on the Chrome icon.
Reports DOWN->ack (input path) and DOWN->first AU (input + render + encode + net)."""
import asyncio, json, sys, time, statistics, subprocess, websockets
URL = sys.argv[1]; RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
X, Y = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (665, 1968)
LOCAL = "127.0.0.1" in URL
SSH = ["ssh", "-i", __import__("os").environ.get("STRLIX_VM_KEY", "~/.ssh/strlix-vm.pem"), __import__("os").environ["STRLIX_VM"]]
def adb(c):
    cmd = "adb -s emulator-5554 shell " + c
    subprocess.run(cmd if LOCAL else SSH + [cmd], shell=LOCAL, capture_output=True, timeout=30)
async def main():
    out = {"url": URL, "ack_ms": [], "frame_ms": [], "first_au_s": None}
    t0 = time.time()
    async with websockets.connect(URL, max_size=None, open_timeout=20) as ws:
        q = asyncio.Queue()
        async def rd():
            async for m in ws:
                await q.put((time.time(), m))
        task = asyncio.create_task(rd())
        while True:
            t, m = await q.get()
            if not isinstance(m, str): out["first_au_s"] = round(t - t0, 3); break
        for i in range(RUNS):
            adb("am force-stop com.android.chrome"); adb("input keyevent HOME")
            await asyncio.sleep(2.5)
            while not q.empty(): q.get_nowait()
            td = time.time(); ct = td * 1000
            await ws.send(json.dumps({"type": "motion", "action": "DOWN", "x": X, "y": Y, "t": ct}))
            await asyncio.sleep(0.06)
            await ws.send(json.dumps({"type": "motion", "action": "UP", "x": X, "y": Y, "t": ct + 60}))
            ack = fr = None
            while time.time() - td < 4 and (ack is None or fr is None):
                try: t, m = await asyncio.wait_for(q.get(), 0.5)
                except asyncio.TimeoutError: continue
                if isinstance(m, str):
                    j = json.loads(m)
                    if j.get("type") == "motion_ack" and j.get("action") == "DOWN" and ack is None: ack = (t - td) * 1000
                    if j.get("type") == "ping": await ws.send(json.dumps({"type": "pong", "t": j.get("t")}))
                elif fr is None: fr = (t - td) * 1000
            out["ack_ms"].append(round(ack) if ack else None); out["frame_ms"].append(round(fr) if fr else None)
        task.cancel()
    f = [x for x in out["frame_ms"] if x]; a = [x for x in out["ack_ms"] if x]
    out["frame_median_ms"] = statistics.median(f) if f else None; out["ack_median_ms"] = statistics.median(a) if a else None
    adb("am force-stop com.android.chrome"); adb("input keyevent HOME")
    print(json.dumps(out))
asyncio.run(main())

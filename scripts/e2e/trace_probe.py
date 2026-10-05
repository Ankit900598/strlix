"""Tap latency breakdown. usage: trace_probe.py <ws_url> [runs]
Per run: force-stop Chrome, HOME, idle 2.5 s, DOWN(trace)/UP on the Chrome icon.
Client: RTT (ping/pong), DOWN->ack, DOWN->first AU, DOWN->first big AU (>4 KB, i.e. launch anim).
Server (tap_trace): pace, inject, inject->AU publish, AU->send."""
import asyncio, json, sys, time, statistics, subprocess, os, websockets
URL = sys.argv[1]; RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 6
HOLD = float(os.environ.get("HOLD_MS", "60")) / 1000
X, Y = 665, 1968
LOCAL = "127.0.0.1" in URL
SSH = ["ssh", "-i", os.path.expanduser(os.environ.get("STRLIX_VM_KEY", "~/.ssh/strlix-vm.pem")), os.environ["STRLIX_VM"]]
def adb(c):
    cmd = "adb -s emulator-5554 shell " + c
    subprocess.run(cmd if LOCAL else SSH + [cmd], shell=LOCAL, capture_output=True, timeout=30)
async def main():
    rows = []
    async with websockets.connect(URL, max_size=None, open_timeout=20) as ws:
        q = asyncio.Queue()
        async def rd():
            async for m in ws: await q.put((time.time(), m))
        task = asyncio.create_task(rd())
        while True:
            t, m = await q.get()
            if not isinstance(m, str): break
        for i in range(RUNS):
            adb("am force-stop com.android.chrome"); adb("input keyevent HOME")
            await asyncio.sleep(2.5)
            while not q.empty(): q.get_nowait()
            # RTT
            tp = time.time(); await ws.send(json.dumps({"type": "ping", "t": tp})); rtt = None
            while rtt is None and time.time() - tp < 3:
                t, m = await q.get()
                if isinstance(m, str) and json.loads(m).get("type") == "pong" and json.loads(m).get("t") == tp: rtt = (t - tp) * 1000
            await asyncio.sleep(0.3)
            while not q.empty(): q.get_nowait()
            td = time.time(); ct = td * 1000
            await ws.send(json.dumps({"type": "motion", "action": "DOWN", "x": X, "y": Y - (600 if os.environ.get("MODE") == "drag" else 0), "t": ct, "trace": True}))
            if os.environ.get("MODE") == "drag":
                # home-screen pan: moves start 8 ms after DOWN, every 8 ms, 40 px each (slop crossed on the 1st)
                for k in range(1, 13):
                    await asyncio.sleep(0.008)
                    await ws.send(json.dumps({"type": "motion", "action": "MOVE", "x": X - 40 * k, "y": Y - 600, "t": ct + 8 * k}))
                await ws.send(json.dumps({"type": "motion", "action": "UP", "x": X - 480, "y": Y - 600, "t": ct + 104}))
            else:
                await asyncio.sleep(HOLD)
                await ws.send(json.dumps({"type": "motion", "action": "UP", "x": X, "y": Y, "t": ct + HOLD * 1000}))
            ack = fr = big = None; tr = None
            while time.time() - td < 4 and (ack is None or fr is None or big is None or tr is None):
                try: t, m = await asyncio.wait_for(q.get(), 0.5)
                except asyncio.TimeoutError: continue
                if isinstance(m, str):
                    j = json.loads(m)
                    if j.get("type") == "motion_ack" and j.get("action") == "DOWN" and ack is None: ack = (t - td) * 1000
                    elif j.get("type") == "tap_trace": tr = j
                    elif j.get("type") == "ping": await ws.send(json.dumps({"type": "pong", "t": j.get("t")}))
                else:
                    if fr is None: fr = (t - td) * 1000
                    if big is None and len(m) > 4096: big = (t - td) * 1000
            rows.append({"rtt": round(rtt or 0), "ack": round(ack or 0), "first_au": round(fr or 0), "big_au": round(big or 0), "trace": tr})
            print(json.dumps(rows[-1]), flush=True)
        task.cancel()
    def med(k): v = [r[k] for r in rows if r[k]]; return statistics.median(v) if v else None
    tr = [r["trace"] for r in rows if r["trace"]]
    def tmed(f): v = [f(x) for x in tr]; return round(statistics.median(v), 1) if v else None
    summ = {"rtt": med("rtt"), "ack": med("ack"), "first_au": med("first_au"), "big_au": med("big_au"),
            "srv_pace": tmed(lambda x: x["pace_ms"]), "srv_inject": tmed(lambda x: x["inject_ms"]),
            "srv_inj_to_au": tmed(lambda x: x["inj_to_au_ms"][0]), "srv_au_to_send": tmed(lambda x: x["au_to_send_ms"][0])}
    print("SUMMARY " + json.dumps(summ))
    adb("am force-stop com.android.chrome"); adb("input keyevent HOME")
asyncio.run(main())

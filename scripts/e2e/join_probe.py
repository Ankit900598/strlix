import asyncio, json, sys, time, websockets
async def one(url):
    t0 = time.time(); hello = None
    async with websockets.connect(url, max_size=None, open_timeout=20) as ws:
        topen = time.time() - t0
        while True:
            m = await asyncio.wait_for(ws.recv(), 10)
            if isinstance(m, str):
                if json.loads(m).get("type") == "hello" and hello is None: hello = time.time() - t0
            else:
                return {"open_ms": round(topen*1000), "hello_ms": round((hello or 0)*1000), "first_au_ms": round((time.time()-t0)*1000), "key": bool(m[1] & 1)}
async def main():
    url = sys.argv[1]; gap = float(sys.argv[2]) if len(sys.argv) > 2 else 15
    out = []
    for i in range(int(sys.argv[3]) if len(sys.argv) > 3 else 3):
        out.append(await one(url)); await asyncio.sleep(gap)
    print(json.dumps(out))
asyncio.run(main())

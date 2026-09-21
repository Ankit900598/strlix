# Strlix web-market

Homepage marketplace with **mini-phone → fullscreen bezel**, device filters (Android / RAM / ROM / model), and **test-mode** checkout stub.

## Open locally

```bash
cd /workspace/zevi-cloudphone/web-market
python3 -m http.server 8765 --bind 127.0.0.1
# Prefer :8790 when free; on this box :8790/:8791 are sand-egress-tunnel — use :8765 or http://127.0.0.1:8792/market/
# open http://127.0.0.1:8790/
```

Optional market-api:

```bash
cd /workspace/zevi-cloudphone
.venv/bin/pip install -e services/market-api
.venv/bin/uvicorn market_api.main:app --app-dir services/market-api --port 8792
# then set window.STRLIX_MARKET.marketApi = "http://127.0.0.1:8792" in index.html
```

Live stream: desktop-api `http://127.0.0.1:8789/` or pilot `http://127.0.0.1:8787/`.


## Anonymous first session

Browsing and the mini-phone preview make no auth request. The first test-mode
rent creates a short-lived, PII-free anonymous market session (`POST
/v1/auth/anon`) only when checkout starts. After the phone opens successfully,
the UI offers an optional email claim that keeps the same user/order history
(`POST /v1/auth/claim`). Access tokens stay in memory; only the refresh token
is persisted locally, and no email is collected before the first successful
rental.

Run the local smoke test from the repository root:

```bash
scripts/test-market-anonymous.py
```


## Minimal async task status

After an authenticated/anonymous rental session exists, the phone-first UI can
start and poll a privacy-safe status shell. It accepts only an allow-listed kind
(`phone_task`, `device_wake`, or `replay_export`) and never accepts prompt text,
chat content, device content, or an outside destination. The market-api keeps the
short-lived record in process memory and transitions `queued → running → done`;
it is intentionally not a durable worker yet.

```js
const job = await window.StrlixJobs.create("phone_task");
const done = await window.StrlixJobs.poll(job.job_id, {
  onUpdate: (state) => console.log(state.status),
});
```

The API endpoints are `POST /v1/jobs` and `GET /v1/jobs/{job_id}`. Both require
the existing bearer session and never expose another user's job.

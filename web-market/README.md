# Strlix web-market

Homepage marketplace: **hero phone → immersive bezel**, device catalog secondary, free-month / anon session. AI Ask lives **inside** the phone stream (`static/index.html?embed=1`), not an external chat panel.

## Production (real phones)

Config is **same-origin** — never `127.0.0.1` on the public AFD host:

```js
window.STRLIX_MARKET = {
  marketApi: "",          // → /v1/*
  // Interim HTTPS tunnel (AFD /stream still 404). Or "/stream" after AFD attach.
  streamUrl: "https://graduation-cope-elementary-defence.trycloudflare.com",
  streamFallback: "",
  payMode: "test",
  billingMode: "free_month",
  freeLaunch: true
};
```

**Merge does not update production.** Redeploy market-api **0.6.8** (see [DEPLOY.md](./DEPLOY.md)) or `/market/` keeps the old catalog UI.

## Open locally

```bash
cd web-market
python3 -m http.server 8765 --bind 127.0.0.1
# http://127.0.0.1:8765/?api=http://127.0.0.1:8792&stream=http://127.0.0.1:8789
```

Optional market-api:

```bash
.venv/bin/uvicorn market_api.main:app --app-dir services/market-api --port 8792
```

## Anonymous first session

Browsing and the hero-phone preview make no auth request. The first free-month / checkout path creates a short-lived anonymous market session (`POST /v1/auth/anon`) only when access starts. After the phone opens, an optional email claim keeps the same user (`POST /v1/auth/claim`). Access tokens stay in memory; only the refresh token is persisted locally.

```bash
scripts/test-market-anonymous.py
```

## Minimal async task status

```js
const job = await window.StrlixJobs.create("phone_task");
const done = await window.StrlixJobs.poll(job.job_id, {
  onUpdate: (state) => console.log(state.status),
});
```

API: `POST /v1/jobs`, `GET /v1/jobs/{job_id}` — bearer session required; no chat payloads.

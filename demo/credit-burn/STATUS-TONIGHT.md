> Newer cutover status: see [`STATUS.md`](./STATUS.md) + [`HARDENING-APPLIED.md`](./HARDENING-APPLIED.md) (2026-09-21 ~21:15 IST).

# Credit-burn tonight — shipped (GPU NO-GO)

**When:** 2026-09-21 ~19:45 IST (Asia/Calcutta)  
**Branch:** `main` (local commits only — parent pushes)  
**Azure GPU:** still **NO-GO** (N* quota = 0)

## Shipped in this pass

1. **Live payments path (test-gated)** — `market_api/payments.py`, migration `005_payment_intents.sql`, endpoints create/confirm/webhook + `/v1/payments/status`. Triple gate: `PAY_MODE=live` ∧ `PAYMENTS_LIVE` ∧ `ALLOW_LIVE_CHARGES`. KV runbook: `infra/hardening/PAYMENTS-KEYVAULT.md`.
2. **WebRTC / APM barge polish** — `static/worklets/barge-vad-processor.js` + feature flag in `static/index.html`; fallback to AnalyserNode; NOTES: `demo/ui-vision/NOTES-WEBRTC-APM-BARGE.md`.
3. **Prod hardening IaC** — AFD+WAF bicep/script, Redis create script, PE stubs, Entra notes under `infra/hardening/`.
4. **Real-device &lt;100ms doc** — `demo/latency/REAL-DEVICE-SUB-100MS.md`.
5. Status updates — this file + `demo/ui-vision/IMPLEMENTATION-STATUS.md` Pass Q.

## Not done / blockers

| Item | Blocker |
|------|---------|
| GPU worker create | Quota 0 on all N* families; LP cores=3 |
| AFD / Redis / PE actually provisioned | Scripts are dry-run by default; await portal credit confirm + Day-1 burn budget |
| Live Stripe charges | Intentionally gated OFF; need KV live secrets + Ankit flip |
| Physical &lt;100ms proof | Needs USB device on desk; emulator cannot certify |
| Entra login in product | Portal notes only — anon preview stays |

## Do not

- Push from this agent (parent handles GitHub)
- Delete Azure resources / touch other RGs
- Commit secrets

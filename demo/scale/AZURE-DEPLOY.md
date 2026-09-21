# Azure deploy — Strlix split backends

**Date:** 2026-09-21 IST  
**Account:** `ay186mnc@gmail.com` · sub `a3dc5296-f948-427e-8656-c6bc52afee21`  
**RG only:** `rg-zevi-cloudphone` (RG location eastus2; phone VM is **eastus**)  
**Never touch:** `phonecodex-*` · never sign out

---

## Honest before / after

| Item | Before | After |
|------|--------|-------|
| Research | Incomplete Claude stream; partial arch docs | `RESEARCH-FULL.md` with citations |
| android-api | Box only `:8788` | **Azure Container Apps** public HTTPS |
| desktop-api + session-broker | Box only `:8789` / `:8791` | **systemd on `vm-zevi-cloudphone`** (ADB-local) |
| Pilot monolith `:8787` | Running on box | **Still running** (untouched) |

---

## Public URLs (no secrets)

### A) android-api — chat / voice / a11y BFF

| | |
|--|--|
| **HTTPS** | `https://ca-android-api.salmonrock-c8e120f0.eastus2.azurecontainerapps.io` |
| **Health** | `GET /health` |
| **Chat** | `POST /v1/chat` (alias `POST /chat`) |
| **Region** | eastus2 (next to `oai-zevi-phonepilot` + `speech-zevi-strlix`) |
| **App** | `ca-android-api` in env `cae-zevi-strlix` |
| **Image** | `acrzevistrlix.azurecr.io/android-api:0.1.0` (ACR Basic) |
| **Scale** | min=1 · max=3 · 0.5 vCPU / 1 GiB |

```bash
AND=https://ca-android-api.salmonrock-c8e120f0.eastus2.azurecontainerapps.io
curl -s "$AND/health" | jq .
curl -s -X POST "$AND/v1/chat" -H 'Content-Type: application/json' \
  -d '{"message":"say hi in three words"}' | jq .
```

**Verified 2026-09-21 IST:** `/health` → 200; `/v1/chat` → `ok:true` via deployment `gpt-5.6-sol`.

### B) desktop-api + session-broker — on phone VM

| | |
|--|--|
| **VM** | `vm-zevi-cloudphone` · **20.115.117.71** · eastus · ADB `emulator-5554` |
| **desktop-api** | `http://20.115.117.71:8789` |
| **session-broker** | `127.0.0.1:8791` on VM only (capacity nested in desktop `/health`) |
| **Units** | `strlix-desktop-api.service`, `strlix-session-broker.service` |
| **NSG** | `allow-8789` (pri 1040), `allow-8791` (pri 1050) on `vm-zevi-cloudphone-nsg` |

```bash
DESK=http://20.115.117.71:8789
curl -s "$DESK/health" | jq '{ok,service,adb_state,broker:.broker.ok}'
```

**Verified 2026-09-21 IST:** `/health` → `ok:true`, `adb_state=device`, broker ok.

**Why VM (option 1):** stream/ADB latency; cheapest solid path. android-api stays on Container Apps.

---

## Secrets (never print)

- OpenAI + Speech keys read via `az cognitiveservices account keys list` → Container Apps secrets (`oai-key`, `speech-key`) as `secretref:…`.
- `STRLIX_JWT_SECRET` generated at deploy → ACA secret `jwt-secret`.
- VM services: `~/strlix/.env` (mode 600). No keys in image layers.
- Phase-2: Key Vault references (not created yet — save credits).

---

## Local pilot preserved

| Port | Service | Host |
|-----:|---------|------|
| 8787 | pilot monolith | box |
| 8788 | android-api | box |
| 8789 | desktop-api | box |
| 8791 | session-broker | box |

Azure deploy is **additive**. APK → public android URL is a separate cutover (`APK-CUTOVER.md`).

---

## Cost notes (Startup credits)

| Resource | SKU | Notes |
|----------|-----|-------|
| `acrzevistrlix` | Basic | Image store |
| `law-zevi-strlix` | Pay-as-you-go | Required by CAE |
| `cae-zevi-strlix` | Consumption | Shared env |
| `ca-android-api` | 0.5 vCPU / 1 GiB · min=1 | OpenAI tokens will dominate bill |
| Existing VM | already running | No extra VM for desktop path |
| Key Vault | not created | Deferred |

Overnight idle:

```bash
az containerapp update -g rg-zevi-cloudphone -n ca-android-api --min-replicas 0
```

---

## Rebuild / redeploy

```bash
cd /workspace/zevi-cloudphone
docker build -f services/android-api/Dockerfile -t android-api:local .
az acr login -n acrzevistrlix
docker tag android-api:local acrzevistrlix.azurecr.io/android-api:0.1.1
docker push acrzevistrlix.azurecr.io/android-api:0.1.1
az containerapp update -g rg-zevi-cloudphone -n ca-android-api \
  --image acrzevistrlix.azurecr.io/android-api:0.1.1
```

VM refresh:

```bash
KEY=/home/box/Downloads/vm-zevi-cloudphone-key.pem
HOST=20.115.117.71
tar czf /tmp/strlix-vm.tgz --exclude='__pycache__' --exclude='.venv' \
  services/desktop-api services/session-broker packages/common app static
scp -i "$KEY" /tmp/strlix-vm.tgz azureuser@$HOST:~/
ssh -i "$KEY" azureuser@$HOST \
  'cd ~/strlix && tar xzf ~/strlix-vm.tgz && sudo systemctl restart strlix-session-broker strlix-desktop-api'
```

---

## Resources in `rg-zevi-cloudphone` (this deploy)

- `acrzevistrlix` · `law-zevi-strlix` · `cae-zevi-strlix` · `ca-android-api`
- NSG rules `allow-8789`, `allow-8791`

Pre-existing (used, not recreated): VM, OpenAI, Speech, VNet/NSG/IP.

---

## Related

- `RESEARCH-FULL.md` — cloud phones, farms, WebRTC, chat scale, BFF split  
- `ARCHITECTURE-claude.md` — service map (+ § Azure deployment)  
- `CAPACITY.md` · `STREAM-OWNER.md` · `APK-CUTOVER.md`

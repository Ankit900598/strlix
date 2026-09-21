# Strlix Scale Research (FULL) — Cloud Phones, Device Farms, Streaming, Chat BFF

**Date:** 2026-09-21 IST  
**Scope:** Finish incomplete Claude stream (`claude-stream.jsonl`); expand with web research + concrete Strlix recommendations.  
**RG constraint:** only `rg-zevi-cloudphone` · never touch `phonecodex-*`.

> **Honest status before this doc:** Architecture split existed (`ARCHITECTURE-claude.md`, services on box `:8788/:8789/:8791`), but Claude’s design stream never finished final markdown, and **nothing was Azure-deployed** (services ran on the shared box only). This document + `AZURE-DEPLOY.md` close that gap.

---

## 1. Research questions

1. What cloud-phone / device-farm options exist for a phone-first AI product?
2. How do WebRTC / scrcpy streaming fleets scale (viewer slots ≠ chat QPS)?
3. What chat-API patterns (WhatsApp-scale) apply to Strlix’s in-phone LLM loop?
4. Why separate **mobile BFF** (`android-api`) from **desktop/viewer BFF** (`desktop-api`)?

---

## 2. Cloud phone platforms (product category)

A **cloud phone** is a remote Android environment (container/VM/physical) streamed to a thin client. Categories:

| Category | Examples | Fit for Strlix |
|----------|----------|----------------|
| **Antidetect / multi-account cloud phones** | Multilogin, GeeLark, MoreLogin, DuoPlus, PhoneGrid | Weak — built for SMM fingerprint farms, not AI-in-phone UX |
| **General Android cloud / emulators** | VMOS Cloud, Redfinger, BlueStacks X, LDCloud | Possible short-term device rental; little control over ADB/a11y |
| **Dev/QA device farms (physical)** | [AWS Device Farm](https://aws.amazon.com/device-farm/), BrowserStack, Sauce Labs, LambdaTest, pCloudy | Great for APK QA; expensive as always-on “user phone” pool |
| **Self-host / cloud-native Android** | [Canonical Anbox Cloud](https://canonical.com/anbox-cloud), [Redroid](https://github.com/remote-android/redroid-doc), Genymotion Cloud, Azure VM + AVD (current) | **Best long-term for Strlix ownership** |

Sources:

- Pixelscan — “Best 16 Cloud Phone Android Providers for 2026”: https://pixelscan.net/blog/best-cloud-phone-android-providers/
- Codersera — cloud emulators 2026: https://codersera.com/blog/best-cloud-phone-emulators-in-depth-guide/
- Whoer — Android cloud emulator comparison: https://whoerip.com/blog/android-cloud-emulator-platforms/
- Canonical Anbox Cloud docs: https://canonical.com/anbox-cloud/docs/
- Self-hosted Waydroid vs Redroid vs Anbox guide: https://www.pistack.xyz/posts/2026-06-07-self-hosted-android-emulation-waydroid-redroid-anbox-guide/
- AWS Device Farm: https://aws.amazon.com/device-farm/
- Device farm roundups: https://www.pcloudy.com/blogs/top-device-farms/ · https://www.getpanto.ai/blog/device-farms-for-mobile-testing

### Strlix recommendation (devices)

| Phase | Fleet choice | Why |
|------:|--------------|-----|
| **0–1 (now)** | Keep **Azure VM AVD** (`vm-zevi-cloudphone`, eastus) + ADB | Already paid Startup VM; full ADB + a11y; lowest change |
| **2** | **Redroid** or **Anbox Cloud** on Azure VMSS (ARM preferred for density) | Container density > one qemu/AVD per VM; still own the serial |
| **2 alt** | Genymotion SaaS / Device Farm for **CI only** | Do not rent Device Farm as the production “user phone” |
| **3** | Mixed: Anbox/Redroid pool + optional physical farm for Play Integrity / carrier apps | Broker routes `device_id → edge` |

**Do not** build Strlix on antidetect cloud phones (GeeLark etc.) — wrong product surface and ToS risk.

---

## 3. Device farms vs “user cloud phone”

Device farms (BrowserStack, AWS Device Farm, Sauce) optimize for **ephemeral test sessions**, not persistent personal AI phones with AccessibilityService + chat history.

| Need | Device farm | Owned cloud phone (AVD/Redroid/Anbox) |
|------|-------------|----------------------------------------|
| Install Strlix APK + a11y | Possible | Native |
| Persist user session days | Poor / costly | Designed for it |
| H.264 mirror to desktop | Limited APIs | Full control (scrcpy/WebRTC) |
| Cost at 100–1k concurrent phones | Very high | CapEx/OpEx you control |

**Rec:** Use farms for **regression**; use owned fleet for **product**.

---

## 4. WebRTC / streaming fleets

Current Strlix path: `adb screenrecord` → Annex-B H.264 over WebSocket (`desktop-api`), ~12 viewers/device.

Industry path for scale:

1. **Device encode** (scrcpy-server / MediaCodec) on the phone/container  
2. **Stream-edge** near the device (same region/VNet)  
3. **WebRTC SFU** for browser fan-out (not mesh)  
4. **TURN** for NAT; watch egress cost  

References:

- Scrcpy over WebRTC: https://github.com/hqw700/ScrcpyOverWebRTC  
- ScreenStream (MJPEG / WebRTC / RTSP): https://github.com/dkrivoruchko/ScreenStream  
- WebRTC SFU + simulcast cost curve (2026): https://appscale.blog/en/blog/webrtc-sfu-realtime-infrastructure-scaling-media-routing-cost-2026  
- Fleet video / SFU latency budget: https://www.samvyo.com/blog/how-fleet-video-streaming-actually-works-the-architecture-between-vehicle-and-command-centre  
- Android WebRTC screen share 2026: https://www.forasoft.com/blog/article/android-webrtc-screen-sharing  

### Latency & placement rule

> Put **desktop-api / stream-edge next to the emulator** (same VM or private link). Keep **android-api** (chat) cloud-native and regionally replicated.

This is why Azure deploy splits:

- **android-api → Azure Container Apps** (eastus2, next to OpenAI/Speech)  
- **desktop-api + session-broker → on `vm-zevi-cloudphone`** (eastus, ADB-local)

### Streaming roadmap for Strlix

| Step | Tech | Viewer model |
|------|------|--------------|
| Now | adb screenrecord → WS H.264 | `devices × 12` hard cap |
| Next | scrcpy-server on VM | Lower encode latency; still WS or WebRTC |
| Scale | Regional stream-edge + SFU (LiveKit / mediasoup / Azure Comm.) | Simulcast; broker maps `sid → edge` |
| Never | Screencap on android-api hot path | Pollutes chat scale |

---

## 5. Chat API scale (WhatsApp-shaped patterns → Strlix)

Classic messaging designs separate **ingest**, **fan-out**, **presence**, and **media**:

- API gateway → chat service → **Redis** (sessions / rate limits / presence) → **queue** (Kafka/Service Bus) → delivery workers  
- GeeksforGeeks WhatsApp design: https://www.geeksforgeeks.org/system-design/designing-whatsapp-messenger-system-design/  
- Scalable messaging walkthrough: https://www.prafulls.me/blogs/scalable-messaging-platform  
- Architecture deep dive: https://medium.com/@yadavsatale/whatsapp-system-design-a-complete-architecture-deep-dive-8949f8d4eb2b  
- High-volume WhatsApp REST patterns (queues, retries, webhooks): https://www.wasenderapi.com/blog/how-to-build-a-reliable-whatsapp-rest-api-architecture-for-high-volume-saas  

### Mapping to Strlix (LLM chat, not P2P SMS)

| WhatsApp concept | Strlix analogue |
|------------------|-----------------|
| Message ingest API | `POST /v1/chat` on android-api |
| Presence / session store | Redis (phase-2) keyed by `device_id` / JWT `sub` |
| Async workers | Service Bus for TTS render, tool telemetry, session expiry |
| Media CDN | Blob + CDN for TTS audio (today: local `demo/voice-audio/`) |
| Rate limits | `CHAT_RATE_PER_MIN` → Redis token bucket |
| Horizontal scale | Container Apps min=0/max=N; **no sticky ADB** |

**Critical difference:** Strlix chat is **LLM-bound** (Azure OpenAI QPS / PTU), not store-and-forward SMS. Scaling chat ≠ buying more phones. Scaling **desktop viewers** = buying more devices.

Phase-1 design target (unchanged honesty): **10M DAU / 100k concurrent chat** with Redis + PTU; viewers = `devices × ~12`.

---

## 6. Separate mobile vs desktop BFF (confirmed)

| Concern | android-api (mobile BFF) | desktop-api (desktop BFF) |
|---------|--------------------------|---------------------------|
| Traffic shape | Short HTTPS, high QPS | Sticky WS, high bandwidth |
| Scarce resource | OpenAI tokens / Speech | ADB serial / encode CPU |
| Scale unit | Replica count | Device count |
| Auth aud | `android-api` | `desktop-api` |
| Deploy | Container Apps / App Service | **Co-located with emulator** |
| Failure domain | Chat outage ≠ black screen | Stream outage ≠ mute chat |

Monolith `:8787` conflated these; the split under `services/` is the correct product architecture. See `ARCHITECTURE-claude.md` + `SPLIT-PLAN.md`.

---

## 7. Clear recommendations for Strlix (actionable)

1. **Ship dual backends permanently** — never re-merge chat into the stream process.  
2. **Azure now:** android-api on **Container Apps** (eastus2); desktop-api + session-broker as **docker/systemd on VM** (eastus). Documented in `AZURE-DEPLOY.md`.  
3. **Secrets:** app settings / Key Vault references; never bake keys into APK or image layers.  
4. **Pilot `:8787`:** keep running for demos until APK + public tunnel fully cut over (`APK-CUTOVER.md`).  
5. **Fleet next:** evaluate Redroid density on a second D-series / ARM VM before buying Anbox license; keep Device Farm for CI only.  
6. **Streaming next:** scrcpy-server on VM; then WebRTC SFU only when viewer>12 on multi-device pool.  
7. **Chat next:** Azure Cache for Redis + Front Door; PTU when OpenAI 429s become the ceiling.  
8. **Auth next:** Play Integrity / attestation before `STRLIX_REQUIRE_AUTH=1` in production.  
9. **Cost:** prefer ACA consumption + one existing VM; avoid AKS until >~20 stream-edge nodes.  
10. **Honesty in decks:** “100k concurrent” = chat; “billion phones” = aspiration, not phase-1 capacity.

---

## 8. Gaps closed vs incomplete Claude stream

| Item | Before | After |
|------|--------|-------|
| Claude final architecture markdown | Stream stuck in thinking (`claude-stream.jsonl`) | `ARCHITECTURE-claude.md` + this research |
| Cloud phone / farm survey | Missing | §2–3 with citations |
| WebRTC fleet path | One-liner in arch doc | §4 with sources + deploy placement rule |
| WhatsApp-scale chat patterns | Missing | §5 mapped to Strlix |
| Azure deploy of backends | Box-only | `AZURE-DEPLOY.md` + live URLs |

---

## 9. Related docs

- `ARCHITECTURE-claude.md` — service map, APIs, roadmap  
- `CAPACITY.md` — honest numbers  
- `SPLIT-PLAN.md` — migration steps  
- `STREAM-OWNER.md` — who owns H.264 encode  
- `APK-CUTOVER.md` — APK → `:8788`  
- `AZURE-DEPLOY.md` — public URLs, curl, cost notes  

# Strlix Dual-Backend Scale Architecture — Senior Design Brief

You are a senior distributed-systems + mobile-backend architect. Design TWO separate backends for Strlix (phone-first AI product). Output a complete architecture markdown document. Be concrete and implementable — not hand-wavy.

## Product facts
- **Android Strlix in-phone app** (`com.zevi.agent`): home search pill, chat, voice STT/TTS, AccessibilityService for on-device tap/swipe/type. Calls host for LLM (`POST /chat`). Keys NEVER in APK.
- **Desktop/viewer** (web): phone mirror — H.264/WS or JPEG stream, tap/swipe/key mapped to ONE bound device. Optional host Live voice. NOT the product chat surface.
- Current monolith: `/workspace/zevi-cloudphone/` FastAPI on :8787 mixes chat, voice, ADB stream, tap. One Azure emulator ADB serial. Documented caps: 12 stream viewers, 1 device.
- Azure RG only: `rg-zevi-cloudphone` (eastus2). OpenAI: `oai-zevi-phonepilot` / `gpt-5.6-sol`. Azure Speech + AWS Polly already wired. Never touch phonecodex-*.
- Honest capacity: **one Azure emulator ≠ billion phones**. Must introduce device pool + session broker.

## Scale assumptions (realistic path)
- Marketing: ~billion concurrent aspiration.
- Engineering phase-1 design target: **10M DAU / 100k concurrent** with clear path to more.
- Separate traffic shapes:
  - Android API: chat/LLM, voice STT/TTS hooks, agent tool protocol for Accessibility results — high QPS, short requests, no screencap fan-out.
  - Desktop/viewer API: device stream (H.264/WS), tap/swipe, session binding to ONE physical/cloud device from a pool — stream-heavy, sticky sessions, scarce devices.

## Required sections in your output
1. Executive summary & separation of concerns (why two APIs, what each owns)
2. Capacity honesty: device pool model; what "100k concurrent" means for phones vs chat-only users
3. Service map: android-api, desktop-api, session-broker, stream-edge (scrcpy/WebRTC fleet), auth, queues
4. Repo/folder layout recommendation under zevi-cloudphone/
5. Auth & device sessions (JWT/device tokens; Android vs viewer; binding)
6. APIs (REST + WS) with path sketches and OpenAPI-style request/response shapes
7. Data stores (Redis sessions, Postgres accounts, blob for TTS audio, queue for jobs)
8. Streaming fleet: WebRTC vs scrcpy-server vs current screenrecord; regional Azure; encoder nodes
9. Rate limits, backpressure, multi-tenant isolation
10. Migration from monolith :8787 without breaking the pilot mid-flight
11. Phase roadmap: pilot (1 device) → 10 devices → 100k concurrent design
12. Risks & non-goals (no restoring big outside chat as product)

Write the FULL architecture as markdown. Be opinionated. Prefer Azure eastus2 + existing OpenAI/Speech; AWS Polly ok. No fluff.

Write a complete Strlix dual-backend architecture markdown document (no tooling, no questions). Phone-first AI product.

Facts: Android app com.zevi.agent (chat/voice/Accessibility) vs desktop web viewer (H.264/WS + tap). Current monolith FastAPI :8787 mixes both; 1 Azure emulator. RG rg-zevi-cloudphone eastus2; Azure OpenAI gpt-5.6-sol; Azure Speech + AWS Polly. Never phonecodex-*.

Design for 10M DAU / 100k concurrent phase-1 with path upward. Marketing billion concurrent is aspiration — be honest: chat scales on API; viewers need device pool.

Required sections:
1. Executive summary & separation of concerns
2. Capacity honesty (device pool; 100k chat vs viewers)
3. Service map: android-api, desktop-api, session-broker, stream-edge, auth, queues
4. Repo layout under zevi-cloudphone/
5. Auth & device sessions (JWT audiences)
6. APIs REST+WS OpenAPI-style sketches
7. Data stores (Redis, Postgres, blob, queues)
8. Streaming fleet (screenrecord → scrcpy → WebRTC; regional Azure)
9. Rate limits / backpressure / isolation
10. Migration from :8787 without breaking pilot
11. Phase roadmap 1 → 10 → 100k
12. Risks & non-goals (no big outside chat as product)

Opinionated. Azure-first. Concrete paths/ports: android-api :8788, desktop-api :8789, session-broker :8791. Output ONLY the architecture markdown.

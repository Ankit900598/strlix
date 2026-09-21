# Strlix 3-Platform Deploy Roadmap (Android · Desktop · iOS)

**Date:** 2026-09-21 IST  
**Codebase reality:** FastAPI backends + static/phone-first web (`static/index.html`, new `web-market/`). Android agent APK under `android-agent/`. No Flutter/RN app yet.

---

## Strategy (fit THIS repo)

| Surface | Approach | Why |
|---------|----------|-----|
| **Web / Desktop** | Progressive Web App + optional **Tauri** or **Electron** thin shell | Already have polished web bezel viewer; desktop = bezel window |
| **Android** | Existing `android-agent` (in-phone AI) + **Trusted Web Activity / Chrome Custom Tabs** or Capacitor wrapping `web-market` + viewer | Avoid rewrite; Play distribution |
| **iOS** | **WKWebView** shell (SwiftUI) loading HTTPS market+viewer; later Capacitor | No iOS native viewer yet; App Store needs Apple login + ATS |

Shared: one **web shell** (`web-market` + stream viewer) is source of truth for marketplace + fullscreen phone. Native wrappers add push, IAP (optional), deep links.

---

## Phase 0 — Now (scaffolded)

- [x] `web-market/` static marketplace UI
- [x] `wrappers/android/README.md` — TWA/Capacitor notes
- [x] `wrappers/ios/README.md` — WKWebView stub notes
- [x] `wrappers/desktop/README.md` — Tauri/Electron notes
- [ ] HTTPS stable host (Cloudflare tunnel or ACA custom domain)

## Phase 1 — Staging web

1. Serve `web-market` + proxy `/api` → market-api, `/stream` → desktop-api.
2. Custom domain on ACA or Static Web Apps in `rg-zevi-cloudphone`.
3. CI: GitHub Action build → ACR → ACA (market-api) + SWA deploy.

## Phase 2 — Android

1. Capacitor project in `wrappers/android/capacitor/` pointing at production URL **or** bundled assets.
2. Continue shipping `android-agent` APK for on-device Ask/Live (separate package or module).
3. Play Console: internal testing track; signing via upload key in KV.
4. Deep link `https://strlix.app/open` → fullscreen phone.

## Phase 3 — Desktop

1. Tauri 2 wrapping web-market (smaller than Electron).
2. Window: fixed aspect phone chrome; frameless optional.
3. Auto-update via Tauri updater + GitHub releases.
4. macOS notarization + Windows Authenticode (certs in KV).

## Phase 4 — iOS

1. Xcode SwiftUI `StrlixShell` WKWebView (stub folder documented).
2. Sign in with Apple required if account gate exists.
3. TestFlight → App Store; no private API streaming.
4. IAP only if selling digital goods on iOS (else external Stripe for account credits — follow Apple guidelines carefully).

---

## CI sketch

```yaml
# .github/workflows/strlix-deploy.yml (to add)
# on push main:
#  - pytest services/*
#  - docker build market-api → acrzevistrlix.azurecr.io/market-api
#  - az containerapp update
#  - upload web-market to SWA
```

## Stores checklist

| Store | Account | Artifacts | Blockers |
|-------|---------|-----------|----------|
| Google Play | TBD | AAB (Capacitor) + optional agent APK | Play App Signing |
| App Store | TBD | IPA | D-U-N-S, Apple Dev $99, Sign in with Apple |
| Microsoft Store (optional) | TBD | MSIX from Tauri | Partner Center |
| Direct macOS/Windows | GitHub Releases | Tauri bundles | Notarization |

## Security

- ATS / HTTPS only for iOS.
- No secrets in wrappers; use market-api.
- Certificate pins optional later.

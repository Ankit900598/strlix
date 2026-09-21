# Strlix iOS viewer (WKWebView stub)

This is an intentionally small, developer-openable Xcode skeleton for the phone-first Strlix web market and fullscreen phone viewer. It is **not App Store ready**: there is no signing team, production host, native login, push, IAP, analytics, or store metadata yet.

## Open it

1. Open `wrappers/ios/StrlixShell.xcodeproj` in Xcode 16 or newer.
2. Edit `StrlixShell/Info.plist` and replace `https://YOUR_HOST/market/` in `StrlixWebURL` with the HTTPS deployment of `web-market`/market-api.
3. If the deployment is not same-origin, update the `window.STRLIX_MARKET` endpoints in `web-market/index.html` for the market-api and stream host (the checked-in values are local-dev defaults).
4. Select an iPhone Simulator or device, choose the `StrlixShell` target, and Run.

The first screen is the shared `web-market` surface. Its mini phone opens the same phone-first fullscreen bezel viewer used by desktop/web. The native layer deliberately stays thin so the web viewer remains the source of truth.

## What is included

- SwiftUI `WindowGroup` with a `WKWebView` wrapper.
- HTTPS-only navigation policy; non-HTTPS schemes are rejected.
- Inline media playback and default website storage for the viewer session.
- `Info.plist` with ATS left strict (no arbitrary loads).
- A hand-authored `.xcodeproj` with Debug/Release configurations and iPhone/iPad device families.

## Known stub limitations

- `YOUR_HOST` must be replaced before a useful run; the placeholder is intentionally not a fallback service.
- Configure signing/team and capabilities in Xcode.
- Add Sign in with Apple only when the account gate is enabled; anonymous preview should remain available before login.
- Validate App Store privacy disclosures, cookie/session behavior, deep links, and media playback on real iOS hardware.
- No private streaming API is used; the shell only loads the HTTPS web viewer.

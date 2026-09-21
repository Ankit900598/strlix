# UI research takeaways (Strlix phone-first)

## References
- **ws-scrcpy-web**: full-bleed stream, compact toolbar, stream modal — device is the product; no chat column.
- **BrowserStack Live**: thin top toolbar (zoom, rotate, device info); device fills the session; DevTools are secondary panes.
- **AWS Device Farm remote**: single device in browser; side tools feel “admin console” — counter-example for consumer product.
- **Android Studio Device Streaming**: physical bezel in Running Devices; ADB interaction; screen is hero.
- **Rabbit R1**: AI lives *on the device* (PTT, home cards); companion web (rabbithole) is config, not the chat pilot.

## Patterns we shipped
1. Phone owns the viewport (≥70% visual weight); chrome ≤52px.
2. No competing chat column — Ask is a FAB + slim drawer only.
3. Pixel-like bezel, dark elegant background, status dots + Live + language.
4. Poll `/adb/screenshot` ~1.5s (visibility-aware) for live feel.
5. Keep `/chat` + Live voice for agent/host audio; product story is in-phone AI.

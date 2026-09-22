# Strlix Phone UI Design Brief — World-Class Cloud Android

**Audience:** web-market + session viewer rewrite  
**Date:** 2026-09-22 (IST)  
**Sources studied (public marketing/docs/screenshots only — no login scrape):**  
Appetize.io · BrowserStack App Live / Live · Genymotion SaaS + Device Web Player · Redfinger / RedCloud · Yeshen-class cloud phones (public reviews) · ws-scrcpy / WebADB scrcpy · prior Strlix `demo/ui-redesign-claude.md` + `demo/ux-audit-strlix.md`  
**Product thesis:** The page is a *window onto a real phone*. AI lives **inside** the Android chrome (Ask bar). Outside chrome is thin status + hardware affordances — never a chat cockpit.

---

## 1. What to copy

### Layout (hero = device)

| Product | Pattern to steal |
|---|---|
| **Appetize** | Instant “device is the page.” Centered physical-looking phone; session starts in seconds; toolbar for power actions (screenshot, biometrics, location) sits *around* the device, not beside a chat log. Embed-first mindset: the phone can live alone in an iframe. |
| **BrowserStack App Live** | Device fills the working area; **thin top status** (device / session) + **icon rail** (home, recents, rotate, screenshot) that never competes with pixels. Natural gestures (tap / swipe / long-press / pinch). Tools open as transient drawers, not permanent columns. |
| **Genymotion Web Player** | Real bezel/frame; **floating toolbar under the device** (rotate, screenshot, record, fullscreen). SDK embeddable — player owns the screen rectangle; host page stays quiet. |
| **ws-scrcpy / WebADB** | Full-bleed H.264 / WebRTC stream, collapsed chrome, latency/fps as **11px muted telemetry**, zero conversational UI. Touch + keyboard map 1:1 to the device. |
| **Redfinger / Yeshen-class** | Consumer “this is *my* phone” framing: always-on session, multi-client (web / APK / desktop), **fullscreen phone first**, plan/upgrade UI secondary. Marketing shows a big live screen — not a dashboard. |

**Copy for Strlix:**

1. **Full-bleed / height-driven device** — phone owns ≥70% of viewport pixels. Stage is `1fr` under a ~44–52px top chrome; device is centered; `aspect-ratio` from real `wm size`, never hardcoded `9/19.5`.
2. **Machined bezel** — dark metal frame (`--bezel` ~8–12px desktop / 6px mobile), large outer radius (~36–46px), punch-hole or thin notch, optional side volume/power nubs. Screen is the only saturated surface.
3. **Floating hardware pill** — Back · Home · Recents · (optional Refresh) docked under the bezel, not in a left sidebar. On `(hover:none)` always visible; ≥44px hit targets.
4. **Icon-only tool rail** — rotate, mute, quality, share — as icons. Never labels that steal width from the phone.
5. **Entry flow = mini-phone → expand** (already in web-market): marketplace card is a small bezel; tap expands to `#phoneStage` fullscreen overlay with the same bezel language. No intermediate “cockpit.”
6. **Typography** — Inter / system UI; chrome labels 12–13px; telemetry 11px muted; body inside Ask 14px/1.55. Low-chroma dark page (`#05070d`–`#0a0e17`); phone screen supplies color.
7. **Density** — BrowserStack-tight: one glance of chrome, then pure phone. Prefer fewer permanent affordances over denser panels.
8. **Motion** — hard frame swap (decode off-screen → replace); optimistic 20px ripple on tap; `200–280ms` ease for stage open/close; **no** crossfade between stream frames; **no** spinner over a live screen. Prefer WebRTC/H.264; JPEG poll only as fallback with visible age.
9. **Touch is the demo** — pointer → tap/swipe; wheel → scroll; keyboard while stage focused maps to Android (modifier combos for web chrome only).

### Entry / first-run (from Appetize + Redfinger + our audit)

- Anonymous browse → rent/grant → stream appears **inside** the bezel within a few seconds.
- Skeleton phone (wallpaper + soft pulse) while connecting — never a broken-image icon.
- Status dots: stream · AI — plain language (“Live · Online”), never `127.0.0.1` or model IDs in the hero chrome.
- Optional email claim **after** phone works (web-market already does this) — never before.

---

## 2. What NOT to copy

| Anti-pattern | Where it shows up | Why Strlix rejects it |
|---|---|---|
| **Chat-first side panel** | Early Strlix `static/index.html` 60/40 chat+phone; AWS Device Farm “screen + tabs” admin feel | Ankit rejected outside chat UI. Size = product: chat column makes Strlix look like “ChatGPT with a screenshot.” |
| Permanent right/left **DevTools column** | BrowserStack DevTools (logs, Appium, ADB shell) | Fine for QA tools; wrong for consumer cloud phone. Keep engineer tools behind a hidden menu or not in market UI. |
| Giant external **Ask / Copilot drawer as primary** | Prior redesign’s large Ask drawer temptation | Drawer may exist as escape hatch; must not feel like the product. Prefer Ask **inside** Android. |
| Multi-device grid as default | Device farms / Genymotion parallel | Soft-launch is one personal phone. Grid is ops, not first session. |
| Neon glassmorphism / emoji chrome | Some gaming cloud-phone marketing | Reads cheap next to a real Android wallpaper. |
| Zevi dual branding | Legacy agent APK / old web | Trust killer — Strlix only. |
| Toasts / `alert()` for ADB errors | Amateur remotes | Status dot + dimmed veil + one quiet line. |

**Hard rule (Ankit):** No chat-first side panels. No resizable “collapse chat” that still reserves a column. A collapsed chat panel is still a chat product.

---

## 3. Phone-first rules (non-negotiable)

1. **Full-bleed device** — phone is the hero; page never scrolls on desktop session view (`100dvh` grid).
2. **AI Ask bar INSIDE the phone chrome** — Strlix home widget / in-Android Ask is the primary AI surface. Web must not replace it with an external mega-chat.
3. **No giant external chat** — optional slim Ask sheet only if needed for web-only fallback; default closed; no suggestion chips wall, no avatars, no history sidebar.
4. **Outside chrome ≤ ~52px top + floating pill** — everything else is icon or overlay.
5. **Stream = truth** — AI actions that change the UI must appear on the mirrored screen, not as a second screenshot in a chat bubble.
6. **Mobile browser parity** — same phone-first rules on real phones viewing the market (`dvh`, safe-area, width-driven bezel).

```
┌─────────────────────────────────────────┐
│ S Strlix   ● Live   ● AI     [···]      │  thin chrome
├─────────────────────────────────────────┤
│                                         │
│            ╭──────────────╮             │
│            │ Android home │             │
│            │  [Ask Strlix]│  ← AI here  │
│            │              │             │
│            ╰──────────────╯             │
│              ◁  ○  □                    │  nav pill
└─────────────────────────────────────────┘
```

---

## 4. Concrete CSS / component checklist (web-market)

### Tokens
- [ ] `--bg`, `--stage`, `--chrome`, `--bezel`, `--fg`, `--fg-dim`, `--muted`, `--accent`
- [ ] `--chrome-h: 52px` (≥1024) / `48` / `44` (<768)
- [ ] `--bezel: 10px` → `6px` on small; `--r-bezel: 46px` → `32px`
- [ ] Use `dvh` / `svh`, never bare `vh`
- [ ] `prefers-reduced-motion: reduce` disables expand/ripple animations

### Components
- [ ] `.mini-phone` marketplace entry (existing) — same bezel language as fullscreen
- [ ] `#phoneStage` fullscreen overlay — flex center, dark stage, no page scroll
- [ ] `.device-frame` / `.phone` — padding bezel, punch-hole, side nubs (hide nubs `<768`)
- [ ] `.screen` — stream `<video>` (preferred) or `<canvas>`/`<img>`; `touch-action: none`; `user-select: none`; `draggable="false"`
- [ ] `.nav-pill` — Back / Home / Recents; floating under bezel; safe-area on iOS
- [ ] `.chrome` — logo mark “S” + wordmark; Live/AI dots; overflow menu only
- [ ] `.telemetry` — frame age / bitrate / paused (hidden on narrow)
- [ ] `.ask-hint` — subtle cue that Ask lives **on the phone** (not a web chat CTA)
- [ ] Connecting skeleton (wallpaper + pulse) — never broken-image
- [ ] Dimmed veil + status when stream/ADB down
- [ ] Optional post-wow account claim — compact, never blocks phone (existing pattern)
- [ ] Hit targets ≥44×44 on touch; focus rings on keyboard

### Interaction
- [ ] Pointer → tap / swipe with optimistic ripple
- [ ] Keyboard → Android when stage focused; web shortcuts are modifier-only
- [ ] No poll storm on `document.hidden`
- [ ] Hard-swap frames; no crossfade
- [ ] Aspect ratio from device size API

### Explicit deletes (market / viewer)
- [ ] No `#chat` column, `#log`, suggestion chip walls, avatar rows
- [ ] No permanent DevTools / ADB shell panel in consumer market UI
- [ ] No Zevi wordmarks or “Z” avatars

---

## 5. First session in 10 seconds (real mobile browser)

Target: user on a phone opens the soft-launch URL on mobile Safari / Chrome.

| t | Feel |
|---|---|
| **0–1s** | Market paints. One clear mini-phone / “Open phone” CTA. No signup wall. |
| **1–3s** | Tap → fullscreen bezel expands (`dvh`, safe-area). Skeleton screen + “Starting…” |
| **3–7s** | Stream locks; wallpaper/home visible; status ● Live. User can **tap** something. |
| **7–10s** | Sees **Ask Strlix** on the Android home (inside the bezel). Optional quiet “You’re in — Ask is on the phone.” No external chat takeover. |

**Pass criteria:** In 10 seconds the user believes they are holding a phone, not using a chatbot. Fail if chat UI or engineer jargon appears first.

---

## 6. Why “browser not working” inside cloud Android

Common failures teams hit on Redroid / AOSP / cloud phones (document for support + capabilities page):

| Cause | Symptom | Mitigation direction |
|---|---|---|
| **No Chrome / Play Services** | “Browser” icon missing; Play links fail; WebView apps blank | Bundle Chromium or document AOSP Browser; GMS images where licensed |
| **Broken / outdated System WebView** | In-app links crash or white-screen (esp. Redroid / custom images) | Pin WebView provider; `cmd webviewupdate`; keep WebView APK updated |
| **Network / DNS / captive portal** | Chrome opens then ERR_NAME_NOT_RESOLVED / timeout | Verify container net, DNS, egress; don’t assume host DNS |
| **ADB / session not ready** | Stream up but taps dead; apps won’t launch | Gate “Live” on `boot_completed` + input ready; don’t show interactive UI early |
| **Architecture mismatch** | ARM-only APKs fail on x86_64 Redroid | Prefer ARM64 workers for consumer apps; warn on translate gaps |
| **Missing Google account / Widevine** | YouTube / banking / DRM sites fail | Honest capabilities copy — not every site works on every image |
| **Gesture / focus stolen by host page** | User “can’t type in Chrome” because web keyboard captured | Focus rules: stage focus → device IME path |

Support copy should say: *“If the phone browser is blank, it’s usually WebView/Chrome on the cloud image or network — not your laptop browser.”*

---

## 7. Competitive cheat-sheet (one line each)

- **Appetize** — fastest “phone as embed”; copy speed + centered bezel + toolbar discipline.  
- **BrowserStack** — copy icon rails + gesture fidelity; do **not** copy DevTools-as-default.  
- **Genymotion** — copy floating under-device toolbar + embeddable player.  
- **Redfinger / Yeshen** — copy consumer “my always-on phone” framing + multi-client; skip cluttered marketing chrome in-product.  
- **ws-scrcpy** — copy stream-first minimalism + telemetry density; add Strlix bezel + in-phone AI.

---

## 8. Success metrics for the rewrite

- Phone pixel share ≥70% on ≥1024px session view.  
- Time-to-first-interactive-frame (tap works) ≤7s p50 on soft-launch path.  
- Zero permanent chat columns in DOM.  
- First-run copy contains no IP addresses, model IDs, or “APK/a11y” jargon.  
- Mobile Lighthouse / manual: no horizontal scroll; Ask discoverable inside bezel within 10s.

---

*End of brief. Implement against `web-market/` (market entry) and session viewer; keep Android Ask bar as the AI source of truth.*

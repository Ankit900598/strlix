# Strlix Cloud Phone — Desktop Viewer Redesign Brief

**Surface:** `static/index.html` served at `/` by `app/main.py` (FastAPI, uvicorn `:8787`)
**Thesis:** The web page is a *window onto the phone*, not a cockpit. The AI lives inside Android (home Ask bar / Live mode). Everything outside the bezel is chrome.

---

## Research takeaways

| Pattern | What they do | What Strlix takes |
|---|---|---|
| **BrowserStack Live** | Device fills the viewport; one thin top bar (session, device, quality); every tool is an icon rail that never competes with the screen | Device is the hero; tools are icons, never panels |
| **AWS Device Farm remote access** | Screen left, tabs right — and it *feels* like an admin console, not a product | Counter-example: a permanent side panel makes the phone look like a preview thumbnail |
| **Android Studio Device Streaming** | Physical-looking bezel, hardware buttons as an adjacent floating rail, screen is pixel-crisp and click-to-touch by default | Bezel + floating nav pill + click-to-tap |
| **ws-scrcpy-web** | Full-bleed stream, collapsed toolbar, zero conversational UI, latency/fps as tiny text | Compact toolbar, telemetry as 11px muted text |
| **Current Strlix UI** | 60/40 split: chat log left (`#chat`), phone as a ~380px sidebar card (`#side`, `aspect-ratio: 9/19.5`) | **Invert it.** The sidebar card becomes an ~810px-tall device; the chat column is deleted |

Four conclusions that drive the spec:

1. **Size communicates the product.** Whichever element is biggest is what the user thinks they bought. Today that's a chat log, so Strlix reads as "ChatGPT with a phone screenshot." The phone must own ≥70% of the pixels.
2. **Chrome should be readable in one glance, not one read.** BrowserStack's top bar is status + 3 affordances. Ours: connection dots, Live, language. Nothing else earns permanent space.
3. **Liveness beats fidelity.** Device Farm's slow refresh reads "broken." A 720px-wide JPEG at 1.2 s feels alive; a 1080px PNG at 4 s feels dead. Ship the small frame.
4. **Touch is the demo.** `app/adb_client.py` already implements `tap()`, `swipe()`, `type_text()`, `key()` — none are exposed as routes in `app/main.py` (only `/adb/screenshot` is). Wiring them turns a screenshot into a phone, which is the whole pitch.

---

## Layout spec

Two rows, no columns. `100dvh`, page never scrolls.

```
┌────────────────────────────────────────────────────────────┐
│ ▣ Strlix   ● ADB  ● AI        [◉ Live]  [English (US) ▾]   │ 52px chrome
├────────────────────────────────────────────────────────────┤
│                                                            │
│                    ╭──────────────╮                        │
│                    │              │                        │
│                    │   ANDROID    │   ← height-driven      │
│                    │    SCREEN    │     device, centered   │
│                    │              │                        │
│                    ╰──────────────╯                        │
│                     ◁   ○   □   ⟳        1.2s · 68 KB      │ floating
│                                                     ( ? )  │ Ask FAB
└────────────────────────────────────────────────────────────┘
```

**Grid**

```
body        grid-template-rows: var(--chrome-h) 1fr
.chrome     52px, hairline bottom border
.stage      1fr, place-items:center, min-block-size:0, padding 24px
.phone      block-size:100%; aspect-ratio from /adb/size; max-inline-size:100%
```

**Sizing math.** The device is height-driven so it never crops: on a 900px-tall window the stage is `900 − 52 − ~88 = 760px`, and at 1080/2400 that's a **342 × 760** device — roughly 2× today's sidebar card and larger than the chat log it replaces. `max-inline-size: 100%` covers short-and-wide windows (aspect ratio then drives height instead).

**Floating layers** (absolutely positioned inside `.stage`, never reflow the device):

| Layer | Position | Contents |
|---|---|---|
| Nav pill | centered, 16px above stage bottom | Back · Home · Recents · Refresh |
| Telemetry | bottom-left, 11px muted | frame age, payload size, `paused` when tab hidden |
| Ask FAB | bottom-right, 24px inset, 44px circle | opens the Ask drawer |
| Ask drawer | right slide-over, 360px, `inset-block:0` | slim `/chat` thread |

**Chrome contents, left → right:** logo mark (28px, "S") + wordmark · `● ADB 127.0.0.1:5555` · `● Strlix AI` · *(flex spacer)* · **Live** button · language `<select>`. Nothing else. No tabs, no breadcrumb, no "New chat".

**Responsive**

| Breakpoint | Behaviour |
|---|---|
| `≥1024px` (primary) | As above. Device height-driven, controls float over the stage. |
| `768–1023px` | `--chrome-h: 48px`, stage padding 12px, wordmark hidden (mark only), language select collapses to a region code (`EN`). |
| `<768px` | Stacks: chrome 44px → device sized by **width** (`inline-size:100%; block-size:auto`), bezel thins to 6px, radii shrink, side nubs hidden. Nav pill docks to the bottom edge with `env(safe-area-inset-bottom)`. Ask drawer becomes an 85dvh bottom sheet. Telemetry hidden. |
| `(hover:none)` | Nav pill always visible (no hover reveal); hit targets ≥44px. |

Use `dvh`, not `vh` — mobile Safari's collapsing toolbar otherwise crops the nav pill.

---

## Visual system

Dark, neutral, low-chroma — the phone screen is the only saturated thing on the page.

```css
:root{
  /* surfaces */
  --bg:        #05070d;   /* page */
  --stage:     #080b12;   /* behind device (radial lift) */
  --chrome:    #0a0e17;   /* top bar */
  --panel:     #0f1420;   /* drawer, popovers */
  --raised:    #161d2c;   /* buttons, pills */
  --raised-h:  #1d2637;   /* hover */

  /* ink */
  --fg:        #e9edf8;
  --fg-dim:    #aab6cc;
  --muted:     #75849e;

  /* line */
  --line:      rgba(148,163,184,.13);
  --line-str:  rgba(148,163,184,.22);

  /* accent + state */
  --accent:    #5b8cff;
  --accent-ink:#0a1020;
  --glow:      rgba(91,140,255,.30);
  --live:      #ff4d6d;   /* mic hot — used nowhere else */
  --ok:        #34d399;
  --warn:      #fbbf24;
  --err:       #f87171;

  /* metrics */
  --chrome-h:  52px;
  --bezel:     10px;
  --r-bezel:   46px;
  --r-screen:  36px;
  --r-panel:   16px;
  --r-ctl:     10px;
  --r-pill:    999px;

  /* space — 4pt scale; use these, not ad-hoc px */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px;

  --shadow-ui:  0 6px 24px rgba(0,0,0,.45);
  --shadow-dev: 0 40px 80px -24px rgba(0,0,0,.85);
  --ease:       cubic-bezier(.2,.8,.2,1);
}
```

**Typography.** One family: `ui-sans-serif, -apple-system, "Segoe UI", Inter, system-ui, sans-serif`. Numbers that tick (frame age, KB, session timer) get `font-variant-numeric: tabular-nums` so chrome doesn't jitter.

| Token | Size / weight / tracking | Used for |
|---|---|---|
| Wordmark | 14px / 650 / `-0.01em` | "Strlix" |
| Control | 13px / 550 | buttons, select |
| Status | 12px / 500 | `ADB 127.0.0.1:5555` |
| Telemetry | 11px / 500 / `0.02em` | frame age, size |
| Body (drawer) | 14px / 400 / `1.55` | `/chat` messages |

**Color discipline.** `--accent` appears on exactly two things: focus rings and the speaking Live state. `--live` appears only while the mic is hot. Status dots are the only other color, and they're 7px. Everything else is greyscale — that's what makes the Android screen read as the subject.

**Depth.** No glassmorphism, no gradients on controls. Elevation is one hairline plus one shadow. The device is the only element with a large shadow; that shadow is what separates "phone" from "screenshot".

**Motion.** 120 ms control hover/press, 220 ms `--ease` drawer, 180 ms Live state change. Frames do **not** animate — crossfading screenshots smears motion and reads as lag. All of it collapses to ~0 under `prefers-reduced-motion`.

---

## Components

### 1. `.chrome` — top bar
52px, `background: var(--chrome)`, `border-block-end: 1px solid var(--line)`. 32px-tall controls vertically centered. `role="banner"`.

### 2. `.status-dot` — connection dots
7px circle + 12px label inside a `--raised` pill. Three states drive dot color and `title`:

| State | Dot | Label | Trigger |
|---|---|---|---|
| connected | `--ok`, steady | `ADB 127.0.0.1:5555` | `/health` → `adb_state: "device"` |
| degraded | `--warn`, 2 s pulse | `Reconnecting…` | poll backoff engaged |
| down | `--err`, steady | `Phone offline` | `/health` error or 3 failed frames |

Poll `/health` every 10 s (not per frame). Wrap in `aria-live="polite"`; announce transitions only, never frame counts.

### 3. `.live-btn` — Live voice
The one prominent control. 32px tall, `--r-pill`, 13px label, leading 8px dot.

- **idle** — `--raised` bg, `--fg-dim` text, static dot
- **listening** — `--live` bg, white text, dot pulses 1.4 s
- **thinking** — `--raised` bg, 3-dot shimmer replacing the label
- **speaking** — `--accent` bg, dot becomes a 3-bar mini-equalizer

Click → `POST /voice/live {active:true, source:"browser", language}` → open `WS /ws/live` → request mic. On `{type:"speak"}` play `audio_url` via WebAudio (host TTS; scrcpy stays `--no-audio`). Keep the existing `#liveOverlay` **only** as the in-session view — it's a modal, not a panel, and it closes back to the bare phone.

### 4. `.lang-select` — language
Native `<select>` styled to match (`appearance:none`, custom caret), populated from `GET /voice/languages`. Persist to `localStorage["strlix.lang"]`, default `en-US`. Sent as `language` on `/voice/live`, `/voice/turn`, `/voice/speak`. Under 1024px show the region code only. Never a flag grid.

### 5. `.phone` — bezel + screen
Padding-based bezel with a machined edge (two inset hairlines, one bright, one dark), punch-hole camera, and two side-button nubs on the right rail. Screen is a single `<img class="screen">` on black backing. Aspect ratio comes from `GET /adb/size` into `--phone-aspect`; today's hardcoded `9/19.5` is wrong for a 1080×2400 AVD and shows as letterbox bars.

States via `data-state` on `.phone`: `live` (default) · `stale` (frame >4 s old → 85% brightness) · `offline` (grayscale + "Phone offline — check the ADB tunnel"). Never blank to a spinner; keep the last frame and dim it.

### 6. `.nav-pill` — hardware keys
Floating below the device: `◁ Back` · `○ Home` · `□ Recents` · `⟳ Refresh`. 36px icon buttons in a `--raised` pill, 1px `--line`, `--shadow-ui`. First three `POST /adb/key` (`KEYCODE_BACK` / `HOME` / `APP_SWITCH`); Refresh forces an immediate frame and resets backoff. Inline SVG with `aria-label`s, never emoji.

### 7. `.telemetry`
11px muted, bottom-left: `1.2s · 68 KB · 720p`, and `paused` when `document.hidden`. The ws-scrcpy trick — costs nothing, makes the viewer feel instrumented.

### 8. `.ask-fab` + `.ask-drawer` — optional, explicitly secondary
44px circle, bottom-right, `--raised`, question-mark glyph, `aria-expanded`. Opens a 360px right slide-over (`role="dialog"`, `aria-modal="false"` — the phone stays interactive), `--panel` bg, hairline left border, `translateX(100%) → 0` in 220 ms.

Contents: one-line header (`Ask Strlix` + close), a compact thread (14px, 8px radius, user right-aligned in `--raised`, assistant left-aligned bare text — **no avatars, no bubble tails, no typing dots**), single-line composer posting to `/chat`. Last 20 turns in memory only; no history sidebar, no suggestion chips, no export. If a reply changes the screen, it lands in the next poll — the drawer never renders its own screenshot.

Dismiss on `Esc`, FAB re-click, close button. Restore focus to the FAB. Toggle with `Ctrl/Cmd+K` (never a bare `/` — single keys belong to the phone).

---

## Interaction

**Frame polling (the core loop).** `setTimeout` chain, never `setInterval` — an interval stacks requests when a frame outlasts the period.

```js
const MIN = 1200, MAX = 8000;
let delay = MIN, etag = null, timer = null;

async function pump(){
  const t0 = performance.now();
  try {
    const r = await fetch('/adb/screen.jpg?w=720&q=70',
      { cache:'no-store', headers: etag ? {'If-None-Match': etag} : {} });
    if (r.status === 304) { delay = MIN; }             // screen idle, nothing decoded
    else if (r.ok) {
      etag = r.headers.get('ETag');
      const url  = URL.createObjectURL(await r.blob());
      const next = new Image(); next.src = url;
      await next.decode();                             // decode off-screen → zero flicker
      const old = screenEl.src; screenEl.src = url; URL.revokeObjectURL(old);
      setState('live'); delay = MIN;
    } else throw new Error(r.status);
  } catch { setState('stale'); delay = Math.min(delay * 2, MAX); }
  telemetry(performance.now() - t0);
  timer = setTimeout(pump, Math.max(delay - (performance.now() - t0), 250));
}
document.addEventListener('visibilitychange', () =>
  document.hidden ? clearTimeout(timer) : (delay = MIN, pump()));
```

- **Hidden tab → stop entirely.** A background tab hammering `adb exec-out screencap` is the fastest way to make the emulator feel slow.
- **Backoff on failure:** 1.2 → 2.4 → 4.8 → 8 s, dots go `--warn`, screen goes `stale`. Any success or Refresh snaps back to 1.2 s.
- **After any input**, jump the queue: extra polls at +120 ms and +450 ms so a tap feels immediate, then resume cadence.

**Backend work this requires** (small, and it unblocks the whole feel):

| Route | Why |
|---|---|
| `GET /adb/screen.jpg?w=720&q=70` | Return JPEG **bytes** with an `ETag` (frame hash) and `Cache-Control: no-store`. Today `/adb/screenshot` writes a PNG into `demo/` and returns a URL — at 1.2 s that's ~3,000 files and several GB per hour. Downscale + encode in-process; keep `/adb/screenshot` for the deliberate "capture" action only. |
| `GET /adb/size` | Feeds `--phone-aspect` from `wm_size()` instead of a hardcoded ratio. |
| `POST /adb/tap` `{x,y}` normalized 0–1 | `adb_client.tap()` exists; scale by `wm_size` server-side so the client never guesses device pixels. |
| `POST /adb/swipe`, `/adb/key`, `/adb/text` | `swipe()`, `key()`, `type_text()` all exist, unrouted. |

**Touch mapping.** `pointerdown` records a normalized point; `pointerup` within 8px and 250 ms → tap, otherwise swipe (`duration_ms` = real gesture ms, clamped 50–800). Wheel → vertical swipe, throttled to one per 120 ms. Draw a 20px accent ripple at the press point immediately — optimistic feedback covers the ~200 ms ADB round trip. `touch-action: none` on the screen, `user-select: none` on the bezel, `draggable="false"` on the `<img>` or Chrome offers to drag the screenshot away.

**Keyboard**, only while the stage has focus (`tabindex="0"`, visible ring on the bezel):

| Key | Action |
|---|---|
| printable | buffered 300 ms → `POST /adb/text` (one call per burst, not per keystroke) |
| `Enter` / `Backspace` | `KEYCODE_ENTER` / `KEYCODE_DEL` |
| `Esc` | `KEYCODE_BACK` (drawer/overlay consume `Esc` first) |
| `Ctrl/Cmd+K` | toggle Ask drawer |
| `Ctrl/Cmd+Shift+L` | toggle Live |

**Live session flow.** Live → `/voice/live {active:true}` → `WS /ws/live` → mic capture → `POST /voice/turn {message, language, source:"browser"}` → server runs the pilot, synthesizes, broadcasts `{type:"speak", audio_url}` → browser plays it. Audio must be unlocked by the Live click itself (create/resume `AudioContext` in that handler) or autoplay policy silently drops the first reply. Ping the socket every 20 s; on close retry with jitter (1 s → 15 s) and flip the AI dot to `--warn`. `Leave` → `/voice/live {active:false}`, close socket, stop the mic track so the browser's recording indicator goes out.

**Error surfacing.** Inline and quiet: connection problems live in the status dot + the dimmed-screen veil; a failed `/chat` renders as one red-tinted line inside the drawer. No toasts, no modals, no `alert()`.

---

## HTML outline

```html
<body>
  <header class="chrome" role="banner">
    <div class="brand"><span class="mark">S</span><span class="wordmark">Strlix</span></div>
    <div class="status" aria-live="polite">
      <span class="pill"><i class="dot" id="adbDot"></i><span id="adbLabel">ADB …</span></span>
      <span class="pill"><i class="dot" id="aiDot"></i><span>Strlix AI</span></span>
    </div>
    <div class="spacer"></div>
    <button id="liveBtn" class="live-btn" data-state="idle" aria-pressed="false">
      <i class="dot"></i><span class="live-label">Live</span>
    </button>
    <select id="lang" class="lang-select" aria-label="Voice language"></select>
  </header>

  <main class="stage" id="stage">
    <div class="phone" id="phone" data-state="offline" tabindex="0"
         role="application" aria-label="Android phone screen"
         style="--phone-aspect: 1080/2400">
      <span class="camera" aria-hidden="true"></span>
      <img class="screen" id="screen" alt="Live phone screen" draggable="false" />
      <div class="screen-veil" id="veil"><p>Phone offline — check the ADB tunnel</p></div>
      <span class="ripple" id="ripple" aria-hidden="true"></span>
    </div>

    <nav class="nav-pill" aria-label="Device controls">
      <button data-key="KEYCODE_BACK"       aria-label="Back">   <svg …/></button>
      <button data-key="KEYCODE_HOME"       aria-label="Home">   <svg …/></button>
      <button data-key="KEYCODE_APP_SWITCH" aria-label="Recents"><svg …/></button>
      <button id="refreshBtn"               aria-label="Refresh"><svg …/></button>
    </nav>

    <p class="telemetry" id="telemetry" aria-hidden="true">—</p>

    <button id="askFab" class="ask-fab" aria-expanded="false"
            aria-controls="askDrawer" aria-label="Ask Strlix (⌘K)">?</button>
  </main>

  <aside id="askDrawer" class="ask-drawer" role="dialog"
         aria-label="Ask Strlix" aria-modal="false" hidden>
    <header><h2>Ask Strlix</h2><button id="askClose" aria-label="Close">✕</button></header>
    <div class="ask-thread" id="askThread"></div>
    <form class="ask-composer" id="askForm">
      <input id="askInput" placeholder="Ask about the phone…" autocomplete="off" />
      <button type="submit" aria-label="Send">↑</button>
    </form>
  </aside>

  <!-- in-session modal only; closes back to the bare phone -->
  <div id="liveOverlay" role="dialog" aria-modal="true" hidden> … </div>
</body>
```

Deleted from today's markup: `<section id="chat">`, `#log`, `#welcome`, `.suggestions`, `#composer`, `<aside id="side">`, `.shot-meta`, `.history-shots`, `#shots`.

---

## CSS key rules

```css
*,*::before,*::after{ box-sizing:border-box }
html,body{ block-size:100% }
body{
  margin:0; background:var(--bg); color:var(--fg);
  font:400 14px/1.5 ui-sans-serif,-apple-system,"Segoe UI",Inter,system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;
  display:grid; grid-template-rows:var(--chrome-h) 1fr;
  block-size:100dvh; overflow:hidden;              /* page never scrolls */
}

/* ── chrome ───────────────────────────────────────────── */
.chrome{
  display:flex; align-items:center; gap:var(--s3); padding-inline:var(--s4);
  background:var(--chrome); border-block-end:1px solid var(--line);
}
.spacer{ flex:1 }
.pill{
  display:inline-flex; align-items:center; gap:var(--s2);
  block-size:28px; padding-inline:10px; border-radius:var(--r-pill);
  background:var(--raised); font-size:12px; color:var(--fg-dim);
  font-variant-numeric:tabular-nums;
}
.dot{ inline-size:7px; block-size:7px; border-radius:50%; background:var(--muted) }
.dot.ok{ background:var(--ok); box-shadow:0 0 0 3px color-mix(in srgb,var(--ok) 18%,transparent) }
.dot.warn{ background:var(--warn); animation:breathe 2s var(--ease) infinite }
.dot.err{ background:var(--err) }

.live-btn{
  display:inline-flex; align-items:center; gap:var(--s2);
  block-size:32px; padding-inline:14px; border:1px solid var(--line);
  border-radius:var(--r-pill); background:var(--raised);
  color:var(--fg-dim); font:550 13px/1 inherit; cursor:pointer;
  transition:background .18s var(--ease), color .18s var(--ease);
}
.live-btn:hover{ background:var(--raised-h); color:var(--fg) }
.live-btn[data-state="listening"]{ background:var(--live); border-color:transparent; color:#fff }
.live-btn[data-state="listening"] .dot{ background:#fff; animation:pulse 1.4s var(--ease) infinite }
.live-btn[data-state="speaking"]{ background:var(--accent); border-color:transparent; color:var(--accent-ink) }

.lang-select{
  appearance:none; block-size:32px; padding:0 30px 0 12px;
  border:1px solid var(--line); border-radius:var(--r-ctl);
  background:var(--raised) var(--caret) no-repeat right 10px center;
  color:var(--fg-dim); font:500 13px/1 inherit;
}

/* ── stage ────────────────────────────────────────────── */
.stage{
  position:relative; display:grid; place-items:center;
  min-block-size:0;                                /* lets the device shrink in the grid row */
  padding:var(--s5) var(--s4) 64px;                /* bottom room for the nav pill */
  background:radial-gradient(120% 90% at 50% 0%, #0d1420 0%, var(--stage) 55%, #04060b 100%);
}

/* ── device ───────────────────────────────────────────── */
.phone{
  position:relative;
  block-size:100%;
  aspect-ratio:var(--phone-aspect, 1080/2400);
  max-inline-size:100%;
  padding:var(--bezel);
  border-radius:var(--r-bezel);
  background:linear-gradient(158deg,#2b3242 0%,#151b27 38%,#0b0e15 100%);
  box-shadow:
    0 0 0 1px rgba(255,255,255,.08),               /* machined outer edge */
    inset 0 1px 0 rgba(255,255,255,.10),           /* top highlight       */
    inset 0 -1px 0 rgba(0,0,0,.65),                /* bottom shade        */
    var(--shadow-dev),
    0 0 120px -40px var(--glow);
  contain:paint;
}
.phone:focus-visible{ outline:2px solid var(--accent); outline-offset:6px }

/* right-rail hardware nubs */
.phone::before,.phone::after{
  content:""; position:absolute; inset-inline-start:100%;
  inline-size:3px; background:linear-gradient(90deg,#2b3242,#0d111a);
  border-radius:0 3px 3px 0;
}
.phone::before{ inset-block-start:18%; block-size:6%  }   /* power  */
.phone::after { inset-block-start:28%; block-size:11% }   /* volume */

.camera{
  position:absolute; inset-block-start:calc(var(--bezel) + 12px);
  inset-inline-start:50%; translate:-50% 0;
  inline-size:9px; block-size:9px; border-radius:50%;
  background:#04060a; box-shadow:inset 0 0 0 1px rgba(255,255,255,.10); z-index:2;
}

.screen{
  display:block; inline-size:100%; block-size:100%;
  object-fit:cover; border-radius:var(--r-screen);
  background:#000; user-select:none; touch-action:none;
  transition:filter .2s var(--ease);
}
.phone[data-state="stale"]   .screen{ filter:brightness(.85) }
.phone[data-state="offline"] .screen{ filter:grayscale(1) brightness(.35) }

.screen-veil{
  position:absolute; inset:var(--bezel); display:grid; place-items:center;
  border-radius:var(--r-screen); opacity:0; pointer-events:none;
  color:var(--muted); font-size:13px; text-align:center; padding:var(--s5);
  transition:opacity .2s var(--ease);
}
.phone[data-state="offline"] .screen-veil{ opacity:1 }

.ripple{
  position:absolute; inline-size:20px; block-size:20px; margin:-10px 0 0 -10px;
  border-radius:50%; background:var(--accent); opacity:0; pointer-events:none;
}
.ripple.go{ animation:tap .35s var(--ease) }
@keyframes tap{ from{opacity:.55; scale:.4} to{opacity:0; scale:2.4} }

/* ── floating controls ────────────────────────────────── */
.nav-pill{
  position:absolute; inset-block-end:16px; inset-inline-start:50%; translate:-50% 0;
  display:flex; gap:var(--s1); padding:var(--s1);
  background:color-mix(in srgb,var(--raised) 92%,transparent);
  border:1px solid var(--line); border-radius:var(--r-pill); box-shadow:var(--shadow-ui);
}
.nav-pill button{
  inline-size:36px; block-size:36px; display:grid; place-items:center;
  border:0; border-radius:var(--r-pill); background:transparent;
  color:var(--fg-dim); cursor:pointer; transition:background .12s var(--ease);
}
.nav-pill button:hover{ background:var(--raised-h); color:var(--fg) }
.nav-pill button:active{ scale:.94 }

.telemetry{
  position:absolute; inset-block-end:18px; inset-inline-start:18px; margin:0;
  font:500 11px/1 inherit; letter-spacing:.02em;
  color:var(--muted); font-variant-numeric:tabular-nums;
}

.ask-fab{
  position:absolute; inset-block-end:24px; inset-inline-end:24px;
  inline-size:44px; block-size:44px; border-radius:50%;
  background:var(--raised); border:1px solid var(--line); color:var(--fg-dim);
  box-shadow:var(--shadow-ui); cursor:pointer;
}
.ask-fab:hover{ background:var(--raised-h); color:var(--fg) }

/* ── ask drawer ───────────────────────────────────────── */
.ask-drawer{
  position:fixed; inset-block:0; inset-inline-end:0; inline-size:360px; z-index:40;
  display:grid; grid-template-rows:auto 1fr auto;
  background:var(--panel); border-inline-start:1px solid var(--line);
  translate:100% 0; transition:translate .22s var(--ease);
}
.ask-drawer[hidden]{ display:grid; visibility:hidden }   /* keep it animatable */
.ask-drawer.open{ translate:0 0; visibility:visible }
.ask-thread{ overflow:auto; padding:var(--s4); display:grid; gap:var(--s3); font-size:14px }
.ask-thread .msg{ max-inline-size:90%; border-radius:10px }
.ask-thread .msg.user{ justify-self:end; background:var(--raised); padding:8px 12px }
.ask-thread .msg.bot { justify-self:start; color:var(--fg-dim) }

/* ── focus, motion, responsive ────────────────────────── */
:where(button,select,input,[tabindex]):focus-visible{
  outline:2px solid var(--accent); outline-offset:2px; border-radius:var(--r-ctl);
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{ animation-duration:.01ms !important; transition-duration:.01ms !important }
}

@media (max-width:1023px){
  :root{ --chrome-h:48px }
  .wordmark{ display:none }
  .stage{ padding:var(--s3) var(--s3) 60px }
}
@media (max-width:767px){
  :root{ --chrome-h:44px; --bezel:6px; --r-bezel:32px; --r-screen:26px }
  .stage{ padding:var(--s2) var(--s2) 72px; align-items:start }
  .phone{ block-size:auto; inline-size:100% }
  .phone::before,.phone::after{ display:none }
  .nav-pill{ inset-block-end:calc(8px + env(safe-area-inset-bottom)) }
  .telemetry{ display:none }
  .ask-drawer{
    inset:auto 0 0 0; inline-size:100%; block-size:85dvh;
    border-inline-start:0; border-block-start:1px solid var(--line);
    border-radius:var(--r-panel) var(--r-panel) 0 0;
    translate:0 100%;
  }
  .ask-drawer.open{ translate:0 0 }
}
```

---

## Do not

1. **Do not keep a chat column.** No left pane, no right pane, no resizable splitter, no "collapse chat" toggle. Delete `#chat`, `#log`, `.suggestions`, `#composer`. A collapsed chat panel is still a chat product.
2. **Do not make the Ask drawer look important.** No hero empty state, no suggestion chips, no avatars, no streaming typing dots, no persistent history, no "powered by" line. If it starts to feel good to live in, it has grown past its job.
3. **Do not shrink the phone for chrome.** Nothing new earns a permanent row or column. New tools become icons in the nav pill or they don't ship.
4. **Do not poll with `setInterval`**, and do not poll a hidden tab. Requests stack, the emulator bogs down, and the demo stutters at the worst moment.
5. **Do not write a PNG to `demo/` per frame.** Today's `/adb/screenshot` persists every capture; at 1.2 s that's thousands of files an hour. Stream bytes; persist only on explicit capture.
6. **Do not crossfade or spin between frames.** Decode off-screen, hard-swap. A fade smears scrolling content and reads as lag; a spinner over a live screen reads as broken.
7. **Do not hardcode `aspect-ratio: 9/19.5`.** Read it from `wm_size` or the device sits in letterbox bars that make the bezel look fake.
8. **Do not use `vh`.** Mobile toolbars eat the nav pill. `dvh` everywhere.
9. **Do not add color for decoration.** No gradient hero, no glassmorphism over the screen, no neon borders, no emoji in chrome. The Android screen supplies all the color the page needs.
10. **Do not autoplay TTS without a gesture.** Unlock `AudioContext` inside the Live click handler or the first reply is silently dropped.
11. **Do not bind bare single keys** (`/`, `n`, space) to web UI. Those keystrokes belong to the phone. Modifier combos only.
12. **Do not use toasts or `alert()`** for ADB/network errors. Status dot, dimmed screen, one inline line in the drawer.
13. **Do not reintroduce Zevi branding** in markup, titles, or the logo mark — the UX audit flagged split Zevi/Strlix branding as a trust killer, and `static/index.html` is currently clean. Keep it that way.
14. **Do not ship the viewer without touch.** A phone you can only look at is a screenshot viewer; `tap`/`swipe`/`text`/`key` already exist in `app/adb_client.py` and just need routes.

---

I tried to save this to `demo/ui-redesign-claude.md` (the empty placeholder there) but the write wasn't permitted — approve it and I'll drop the file in, or I can go ahead and implement the redesign in `static/index.html` plus the four `/adb/*` routes it depends on.

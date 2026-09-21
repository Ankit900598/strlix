# Strlix UX Audit — First-time user + senior engineer

**Product:** Strlix (cloud Android phone + in-phone AI)  
**Audit time:** 2026-09-20 ~15:50–15:55 IST (Asia/Calcutta)  
**Surfaces walked:** Home (Ask Strlix bar), MainActivity setup, ChatActivity, mic, a11y settings path, overlay/QSB mask notification, web pilot `localhost:8787`, install scripts, layouts/strings/services  
**Device:** AVD `strlix` Android 14 via ADB `127.0.0.1:5555` (SSH tunnel to `azureuser@20.115.117.71`)  
**Artifacts:** `demo/ux-audit/` (before/after screenshots + UI dumps)  
**Claude Code prompts:** drafted below — **none executed**

---

## Executive verdict

This is a strong *demo skeleton* (home pill + chat + host pilot) that still fails a consumer first-run bar. The single worst bug: **tapping “Ask Strlix or type” opened the engineer setup screen (`MainActivity`) instead of chat**, because DB-placed widgets never received `PendingIntent`s. Dual Zevi/Strlix branding and engineer jargon (“APK”, “gpt-5.6-sol”, “a11y”, raw `127.0.0.1`) leak into every surface. **There is no signup** — correctly documented as a finding (demo-only), but the product never says that up front (until this audit’s copy fix).

Highest-impact quick fixes from this pass are **implemented and reinstalled** on the emulator (see §4).

---

## (1) Full mistake list

Severity: **P0** ship-blocker for pitch · **P1** hurts conversion/trust · **P2** polish · **P3** debt

### P0 — Home “Ask Strlix” bar opens setup, not chat
| | |
|---|---|
| **Where** | Home widget `ZeviSearchWidget` / `widget_search_pill.xml`; tap bounds ~`[57,1541][1023,1688]` |
| **User feels** | Taps the hero CTA. Gets a permission/debug dashboard (“Pilot”, “Grant overlay”, “v0.2 · a11y…”). Thinks the product is broken or only for engineers. |
| **Why it hurts** | The *entire* marketing promise is “ask from the home bar.” First tap is the pitch. |
| **Root cause** | `polish-home.sh` / launcher DB placement shows `initialLayout` without running `AppWidgetProvider.onUpdate`, so RemoteViews have **no** click `PendingIntent`. Nexus Launcher falls back to `MAIN`/`LAUNCHER` → `MainActivity` (confirmed: `Intent { act=MAIN … cmp=.MainActivity bnds=[57,1541][1023,1688] }`). |
| **Evidence** | `demo/ux-audit/06-after-bar-tap.png`, logcat before fix |

### P0 — Emulator ↔ pilot often “unreachable” / chat “offline”
| | |
|---|---|
| **Where** | `PilotClient` probes `127.0.0.1:8787`; Main status; Chat chip `offline` |
| **User feels** | Product looks dead on first open. |
| **Why it hurts** | Demo dies in the first 10 seconds. |
| **Root cause** | `adb reverse tcp:8787` not sticky across reconnects; scripts sometimes skip it; Main showed `Pilot: unreachable — all endpoints unreachable` while host uvicorn was healthy. |
| **Evidence** | `02-main-activity.png`, `03-chat-empty.png` vs host `curl /health` OK |

### P1 — No signup / onboarding account flow (finding)
| | |
|---|---|
| **Where** | Entire product (Android + web) |
| **User feels** | Dropped into a live phone with AI already “on.” Confusing for a real consumer launch; fine for a closed demo *if labeled*. |
| **Why it hurts** | Marketing can’t claim “accounts,” billing, sync, or privacy consent. Reviewers ask “where do I sign up?” |
| **Status** | Documented. Copy now states: *“There is no account signup for this demo.”* |

### P1 — Dual branding: Zevi leftovers vs Strlix
| | |
|---|---|
| **Where** | Package `com.zevi.agent`; classes `Zevi*`; theme `Theme.ZeviAgent`; colors `zevi_*`; drawable `ic_zevi_*`; notification channel `zevi_overlay`; web logo **“Z”**; chat avatars **“Z”**; `show-phone.sh` title `Zevi Phone`; README “Zevi Cloud Phone”; Gradle `rootProject.name = "ZeviAgent"`; log tags `ZeviPilot` |
| **User feels** | “Is this Zevi or Strlix?” Unfinished rebrand = untrustworthy startup. |
| **Why it hurts** | Pitch decks say Strlix; phone/web still say Z/Zevi. Investors notice in 5 seconds. |

### P1 — Setup screen is an engineer console, not a product
| | |
|---|---|
| **Where** | `activity_main.xml` / `MainActivity` (before fix) |
| **User feels** | Wall of: Pilot URL, gpt deployment, Overlay/Accessibility jargon, “keys stay on host APK”, “Start floating bubble”, duplicate “Enable Accessibility” while status says ON. |
| **Why it hurts** | Looks like an internal debug APK leaked to demo day. |

### P1 — Chat welcome dumps model + infra jargon
| | |
|---|---|
| **Where** | `ChatActivity` first bubble (before fix) |
| **User feels** | “gpt-5.6-sol (keys stay on host)… Accessibility ON… a11y” |
| **Why it hurts** | Sounds like a research prototype, not a consumer assistant. |

### P1 — Google QSB still present under the mask
| | |
|---|---|
| **Where** | Hotseat `search_container_hotseat` + `OverlayService` QSB mask; UI dump still lists Google app / Voice search / Lens |
| **User feels** | Visually “only Strlix” (good), but a11y/automation can still hit Google; swipe-up or mask misalignment can flash Google. Persistent notif: “Hiding Google search bar on Home.” |
| **Why it hurts** | Demo claim “replaces Google” is a *cover-up*, not a real replacement — fragile for live demos. |

### P1 — Mic on home bar / chat fails poorly on emulator
| | |
|---|---|
| **Where** | Widget mic → `EXTRA_VOICE`; `ChatActivity` `SpeechRecognizer` |
| **User feels** | Mic looks first-class; emulator has no usable mic → cryptic “Voice error N” (before) or dead end. |
| **Why it hurts** | Promotes voice as equal to text without a graceful empty state. |

### P1 — Web pilot empty phone shows broken / misleading chrome
| | |
|---|---|
| **Where** | `static/index.html` `#liveShot` + `#phoneEmpty` |
| **User feels** | “Phone screenshot” broken-image affordance before any capture; empty “Recent.” |
| **Why it hurts** | First web impression looks broken. |

### P2 — Permission buttons contradict status
| | |
|---|---|
| **Where** | Main: “Overlay: granted” + still “Grant overlay permission”; “Accessibility: ON” + “Enable Accessibility…” |
| **User feels** | Doesn’t know what to tap; fear of breaking something. |

### P2 — Floating bubble + QSB mask + search pill = three entry points
| | |
|---|---|
| **Where** | `OverlayService` bubble mode, QSB mask mode, home widget, app icon → Main |
| **User feels** | “Which one is Strlix?” Bubble was demoted in scripts but still primary CTA before fix. |

### P2 — Accessibility enable path is system-generic
| | |
|---|---|
| **Where** | `Settings.ACTION_ACCESSIBILITY_SETTINGS` (full settings splash gear — `05-a11y-settings.png`) |
| **User feels** | Lost in Android Settings with no Strlix-branded explanation screen. |
| **Why it hurts** | Core power feature needs a one-screen explainer + deep link if possible. |

### P2 — Chat chip row clips “Screenshot & describe”
| | |
|---|---|
| **Where** | `activity_chat.xml` horizontal chips |
| **User feels** | Unfinished layout; discoverability of screenshot action is weak. |

### P2 — App display name “Strlix Copilot” vs product “Strlix”
| | |
|---|---|
| **Where** | `strings.xml` `app_name` (before: Strlix Copilot) |
| **User feels** | Naming drift across launcher, notifs, a11y label. |

### P2 — Persistent overlay notification is scary for consumers
| | |
|---|---|
| **Where** | FGS notif “Hiding Google…” / “Strlix Copilot is floating” + system “displaying over other apps” |
| **User feels** | Spyware vibe during a pitch. |

### P2 — Local action replies say “(a11y)” / “(intent)”
| | |
|---|---|
| **Where** | `LocalActions.a11yNote()` (before) |
| **User feels** | Robot talking to engineers. |

### P2 — Web model pill shows raw deployment id
| | |
|---|---|
| **Where** | `index.html` `#modelLabel` → `gpt-5.6-sol` |
| **User feels** | Internal Azure name, not brand. |

### P2 — Public Cloudflare URL is random nonsense
| | |
|---|---|
| **Where** | `demo/public-url.txt` `dicke-materials-vendors-maritime.trycloudflare.com` |
| **User feels** | Unprofessional share link; rotates on restart. |
| **Why it hurts** | Can’t put on a slide without looking improvised. |

### P3 — Package / class rename debt (`com.zevi.agent`)
Safe to keep for now (breaks widgets, a11y component strings, scripts). Track as post-demo rebrand.

### P3 — README still documents AVD `zevi` while live AVD is `strlix`
Ops confusion for the next engineer.

### P3 — No empty-state illustration in chat (large dark void)
After welcome bubble, 60% of the screen is empty — fine for chat, but no suggested cards below fold.

### P3 — `QUERY_ALL_PACKAGES` + cleartext + debuggable
Expected for demo; must not ship to Play as-is.

---

## (2) Engineered fixes (proposed + done)

| Mistake | Fix | File / component | Expected improvement |
|---|---|---|---|
| Bar opens Main | Always `ZeviSearchWidget.refreshAll()` on Main `onResume`, Chat open, a11y `onServiceConnected`; scripts pass `--ez refresh_widget true` after place | `MainActivity.java`, `ChatActivity.java`, `ZeviAccessibilityService.java`, `polish-home.sh`, `install-and-launch.sh` | Home bar opens **Chat** (verified after install) |
| Pilot offline | Ensure `adb reverse tcp:8787` in polish-home + audit session | `polish-home.sh`, live reverse | “Cloud: connected” / “Online” |
| Engineer Main UI | Consumer copy; primary **Ask Strlix**; hide granted permission rows; hide URL when healthy; declare no signup | `activity_main.xml`, `strings.xml`, `MainActivity.java` | Setup feels like a product, not a debugger |
| Chat jargon | Friendly welcome; status `Online · control on`; `friendlyError()` | `ChatActivity.java`, `strings.xml` | First message is pitch-safe |
| Local “(a11y)” | Plain English results | `LocalActions.java` | Replies feel human |
| Web Z branding | Logo/avatars **S**; “Phone connected”; “Strlix AI”; no-signup welcome; hide empty img | `static/index.html` | Web matches Strlix |
| show-phone title | `Strlix Phone` | `scripts/show-phone.sh` | Scrcpy window matches brand |
| App label | `Strlix`; widget picker `Strlix search bar` | `strings.xml`, `AndroidManifest.xml` | Consistent naming |
| Overlay channel | `strlix_overlay`; softer mask notif text | `OverlayService.java` | Less Zevi in shade |
| README title | Strlix Cloud Phone Pilot | `README.md` | Docs match pitch |
| QSB under mask | **Not fully fixed** (needs launcher QSB disable or Pixel-without-GMS) — Claude prompt below | — | True “replaces Google” |
| Package rename | **Deferred** (breaks a11y component id / widgets) | — | Full rebrand later |
| Custom domain | Cloudflare named tunnel / static hostname | ops | Shareable demo URL |

---

## (3) Claude Code prompts drafted (none executed)

### Prompt A — Hard-disable Google QSB (not just mask)
```
In /workspace/zevi-cloudphone, make the Pixel/Nexus home show ONLY the Strlix search widget with zero Google QSB under it.
Do NOT rely on OverlayService QSB mask as the primary solution.
Investigate: pm disable googlequicksearchbox (already partially done), launcher extras to hide hotseat search, or replacing NexusLauncher config.
Keep Strlix widget PendingIntents working. Document the approach in android-agent/README.md.
Do not touch Azure phonecodex-* or sign out. Do not rename applicationId yet.
```

### Prompt B — First-run onboarding sheet (still no account)
```
Add a one-time Strlix first-run bottom sheet (not a signup) when ChatActivity opens and screen-control is off:
- 3 bullets: Ask from Home / Screen control / Cloud brain on host
- Primary: Turn on screen control (deepest possible a11y settings intent)
- Secondary: Continue without
Persist "seen" in SharedPreferences. Keep copy consumer-grade. No Zevi strings.
```

### Prompt C — Full Strlix applicationId migration plan
```
Produce a safe migration plan (do not apply yet) from com.zevi.agent → com.strlix.agent:
- a11y service component string updates in all scripts
- widget provider favorites SQL
- data wipe expectations on emulator
List every file touch. Estimate risk to live demo.
```

**None of the above prompts were executed in this audit.** Fixes below were applied directly.

---

## (4) What was actually implemented (this session)

Installed APK: `android-agent` `0.2.0-home` rebuilt + `adb install -r` on `127.0.0.1:5555`.

1. **Critical:** `ZeviSearchWidget.refreshAll()` on Main resume / Chat open / a11y connect + script hooks → **home bar tap opens Chat** (`15-bar-tap-after-fix.png`, log: `Displayed …ChatActivity`).
2. **Main UI:** “Your phone, with AI”; no-signup hint; primary **Ask Strlix**; hide overlay/a11y/pin when done; “Cloud: connected” without raw URL; footer `Strlix demo · v0.2`.
3. **Chat:** Short welcome; widget-specific “Opened from your home bar…”; status `Online · control on`; friendlier errors/mic copy; hint `Ask Strlix anything…`.
4. **LocalActions:** Removed `(a11y)` / `(intent)` suffixes; clearer enable-control messages.
5. **Web:** S logo + S avatars; “Phone connected” / “Strlix AI”; no-signup welcome; empty phone copy; hide broken img until capture.
6. **Branding nits:** `show-phone.sh` title; overlay channel `strlix_overlay`; app_name `Strlix`; README title; Pilot log tag `StrlixPilot`.
7. **Scripts:** `adb reverse` + widget refresh in `polish-home.sh` / `install-and-launch.sh`.

**Not done (intentionally):** package rename; removing QSB via launcher surgery; signup; Cloudflare custom domain; Azure/`phonecodex-*` changes.

### Verification snapshots
| File | What |
|---|---|
| `demo/ux-audit/01-home-before.png` | Clean home + Strlix bar (before) |
| `demo/ux-audit/02-main-activity.png` | Engineer Main + Pilot unreachable (before) |
| `demo/ux-audit/03-chat-empty.png` | Jargon welcome + offline (before) |
| `demo/ux-audit/06-after-bar-tap.png` | **Bug:** bar → Main (before) |
| `demo/ux-audit/08-web-pilot.png` | Z logo web (before) |
| `demo/ux-audit/13-main-after-fix.png` | Consumer Main + Ask Strlix (after) |
| `demo/ux-audit/15-bar-tap-after-fix.png` | **Fixed:** bar → Chat (after) |
| `demo/ux-audit/17-web-after-fix.png` | S logo web (after) |

---

## First-time user walkthrough (observed)

1. **No signup** — lands on polished home with Strlix pill.  
2. Tap bar → *(was)* setup hell → *(now)* Chat “Opened from your home bar…”.  
3. Mic → voice path; emulator often fails → text fallback copy.  
4. Open app icon → setup/status (still useful for demo ops; now quieter).  
5. Web `http://127.0.0.1:8787/` → chat + live phone panel; health OK when ADB tunnel up.  
6. Overlay FGS notification remains while QSB mask runs.

---

## Recommended next 48h (startup bar)

1. Kill Google hotseat search for real (Prompt A) — mask is a demo hack.  
2. One-screen a11y explainer (Prompt B).  
3. Stable HTTPS hostname for the pitch URL.  
4. Keep `com.zevi.agent` until after next investor demo; then Prompt C.  
5. Add golden-path script: `reverse + refresh_widget + screencap` as `scripts/demo-ready.sh`.

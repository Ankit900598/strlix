# Verification of per-mistake Claude solutions

**Date:** 2026-09-21 IST
**Rule:** Evidence from RESEARCH.md / reviews / Strlix constraints. No rubber-stamp.

## M01
- **Source:** `claude-solutions/M01.md` (claude-cli)
- **Evidence checked:** Appetize/now.gg/Multilogin instant launch vs VSPhone buy-first (GoLogin review). Instant demo + progressive identity fits Strlix.
- **Verdict:** **ACCEPT**

## M02
- **Source:** `claude-solutions/M02.md` (claude-cli)
- **Evidence checked:** VSPhone balance banners observed. Published $/hr in devices.json + checkout stub fixes opacity.
- **Verdict:** **ACCEPT**

## M03
- **Source:** `claude-solutions/M03.md` (claude-cli)
- **Evidence checked:** VSPhone activation-code maze in help center. Single Stripe/Razorpay test path correct.
- **Verdict:** **ACCEPT**

## M04
- **Source:** `claude-solutions/M04.md` (claude-cli)
- **Evidence checked:** GoLogin review: games not preinstalled. Honest notes on cards.
- **Verdict:** **ACCEPT**

## M05
- **Source:** `claude-solutions/M05.md` (claude-cli)
- **Evidence checked:** Square aspect until swap in review. Fixed phone bezel aspect in UI.
- **Verdict:** **ACCEPT**

## M06
- **Source:** `claude-solutions/M06.md` (claude-cli)
- **Evidence checked:** Fixed 5ms latency in review.
- **Verdict:** **REVISE**
- **Revised solution:** Show latency from frame-arrival deltas / WS RTT; label est.; never hardcode.

## M07
- **Source:** `claude-solutions/M07.md` (claude-cli)
- **Evidence checked:** Session wipe in review. leases table direction OK; live migration deferred.
- **Verdict:** **ACCEPT**

## M08
- **Source:** `claude-solutions/M08.md` (claude-cli)
- **Evidence checked:** EN i18n thin. EN-first UI strings.
- **Verdict:** **ACCEPT**

## M09
- **Source:** `claude-solutions/M09.md` (claude-cli)
- **Evidence checked:** Browser-first Appetize/now.gg. web-market is browser-native.
- **Verdict:** **ACCEPT**

## M10
- **Source:** `claude-solutions/M10.md` (claude-cli)
- **Evidence checked:** Ad video on wait. We show progress/phone not ads.
- **Verdict:** **ACCEPT**

## M11
- **Source:** `claude-solutions/M11.md` (claude-cli)
- **Evidence checked:** Proxy/WebRTC leaks in VSPhone tests. Strlix is not anti-detect SMM.
- **Verdict:** **REVISE**
- **Revised solution:** Honest datacenter label; optional BYO proxy later; no false residential claims.

## M12
- **Source:** `claude-solutions/M12.md` (claude-cli)
- **Evidence checked:** Fingerprint theater common. Honesty labeling; do not fake anti-detect for Strlix AI product.
- **Verdict:** **ACCEPT**

## M13
- **Source:** `claude-solutions/M13.md` (claude-cli)
- **Evidence checked:** RESEARCH.md — Redfinger/VSPhone expose Android/RAM/ROM; GeeLark matrix incomplete; Strlix requirement #2 for filters. web-market already ships Android/RAM/ROM/tier filters + legacy chips.
- **Verdict:** **ACCEPT**
- **Note:** Canonical DeviceSpec + compare drawer are good; APK minSdk assistant is stretch — ship filters/spec chips first.

## M14
- **Source:** `claude-solutions/M14.md` (claude-cli)
- **Evidence checked:** RESEARCH.md — web viewers assume WebCodecs; JPEG fallback uncommon; Android 7+ graceful shell is explicit Strlix requirement. static/index.html already ladders H.264→JPEG.
- **Verdict:** **ACCEPT**
- **Note:** Full T0–T3 matrix is aspirational; market UI already documents JPEG fallback. Keep honest tier badge direction.

## M15
- **Source:** `claude-solutions/M15.md` (claude-cli)
- **Evidence checked:** RESEARCH.md table — “In-phone AI: Almost nobody”; GeeLark AIGC/RPA outside. Shipped ask-hint + no side chat column.
- **Verdict:** **ACCEPT**

## M16
- **Source:** `claude-solutions/M16.md` (claude-cli)
- **Evidence checked:** RESEARCH.md GeeLark Synchronizer one-to-many. Strlix is phone-first AI consumer, not farm control plane.
- **Verdict:** **REVISE**
- **Revised solution:** Defer fleet sync in v1. If multi-device routines ship later, require rehearse→preflight→canary→typed confirm + STOP ALL; never a live mirror toggle. Do not make Fleet the primary IA.

## M17
- **Source:** `claude-solutions/M17.md` (claude-cli)
- **Evidence checked:** RESEARCH.md MoreLogin $0 off / $0.006/min + seats + proxies unbundling. Strlix already publishes $/hr on cards.
- **Verdict:** **ACCEPT**
- **Note:** Phone-Hour single meter; avoid inventing seat SKUs.

## M18
- **Source:** `claude-solutions/M18.md` (claude-cli)
- **Evidence checked:** MISTAKES DuoPlus-class startup fees; RESEARCH peer fee opacity.
- **Verdict:** **ACCEPT**
- **Note:** Use one label “Cold start”; do not invent competitor fee amounts — Strlix stub prices only.

## M19
- **Source:** `claude-solutions/M19.md` (claude-cli)
- **Evidence checked:** GeeLark team permissions; share-without-expiry gap (M43/GAPS).
- **Verdict:** **ACCEPT**
- **Note:** Create-time Private default + expiry — ship when collab exists; v1 can stay Private-only.

## M20
- **Source:** `claude-solutions/M20.md` (claude-cli)
- **Evidence checked:** RESEARCH AdsPower/Nstbrowser fingerprint-as-Android confusion; Strlix is real ARM stream.
- **Verdict:** **ACCEPT**

## M21
- **Source:** `claude-solutions/M21.md` (claude-cli)
- **Evidence checked:** Multilogin 2-in-1 marketing vs Strlix constraints (not anti-detect SMM — see M11/M12 revises).
- **Verdict:** **REVISE**
- **Revised solution:** Strlix is phone-stream first. Do not merge antidetect browser profiles into an “Identity” product. Optional desktop companion = stream client only, shared auth — never fingerprint theater.

## M22
- **Source:** `claude-solutions/M22.md` (claude-cli)
- **Evidence checked:** RESEARCH now.gg Trustpilot ~1.5/5 ads/queues; M10 ad-on-wait.
- **Verdict:** **ACCEPT**

## M23
- **Source:** `claude-solutions/M23.md` (claude-cli)
- **Evidence checked:** RESEARCH BlueStacks X hybrid → App Player install. web-market already browser-native (M09).
- **Verdict:** **ACCEPT**

## M24
- **Source:** `claude-solutions/M24.md` (claude-cli)
- **Evidence checked:** Instant-play curated catalog lock-in vs real cloud phone need for APK.
- **Verdict:** **ACCEPT**
- **Note:** Sideload + trust card; abuse scanning deferred, not fake-safe claims.

## M25
- **Source:** `claude-solutions/M25.md` (claude-cli)
- **Evidence checked:** Device-farm contact-sales pattern in RESEARCH; Strlix cards already show $/hr + test checkout.
- **Verdict:** **ACCEPT**
- **Note:** Ignore Claude’s sample ₹/$ plan numbers — keep devices.json stub cents.

## M26
- **Source:** `claude-solutions/M26.md` (claude-cli)
- **Evidence checked:** Appetize/Genymotion overage; free hard-kill without save (M27 related).
- **Verdict:** **ACCEPT**
- **Note:** Active-minute meter + idle park aligns with M07 snapshot direction.

## M27
- **Source:** `claude-solutions/M27.md` (claude-cli)
- **Evidence checked:** Session hard caps without save — separate stream cap from persisted identity; aligns M07 snapshot direction.
- **Verdict:** **ACCEPT**

## M28
- **Source:** `claude-solutions/M28.md` (claude-cli)
- **Evidence checked:** RESEARCH farms chrome overload; phone-as-document matches Strlix fullscreen bezel already shipped.
- **Verdict:** **ACCEPT**

## M29
- **Source:** `claude-solutions/M29.md` (claude-cli)
- **Evidence checked:** Core Strlix pattern; mini-phone→fullscreen already in web-market.
- **Verdict:** **ACCEPT**

## M30
- **Source:** `claude-solutions/M30.md` (claude-cli)
- **Evidence checked:** BrowserStack switch friction; portable Session object direction OK — migrate deferred.
- **Verdict:** **ACCEPT**

## M31
- **Source:** `claude-solutions/M31.md` (claude-cli)
- **Evidence checked:** Sauce Connect / local tunnel as gate; phone-first then network upgrade fits instant-try.
- **Verdict:** **ACCEPT**

## M32
- **Source:** `claude-solutions/M32.md` (claude-cli)
- **Evidence checked:** Real vs virtual confusion; Strlix catalog is virtual cloud — label honestly, no fake metal.
- **Verdict:** **ACCEPT**

## M33
- **Source:** `claude-solutions/M33.md` (claude-cli)
- **Evidence checked:** a11y gap; web-market already has skip link/focus-visible — expand to stream canvas roles.
- **Verdict:** **ACCEPT**

## M34
- **Source:** `claude-solutions/M34.md` (claude-cli)
- **Evidence checked:** Contrast/status encoding; keep WCAG-minded chips (already legacy/warn colors).
- **Verdict:** **ACCEPT**

## M35
- **Source:** `claude-solutions/M35.md` (claude-cli)
- **Evidence checked:** Degraded stream messaging; pairs with M14 tier badge + JPEG ladder.
- **Verdict:** **ACCEPT**

## M36
- **Source:** `claude-solutions/M36.md` (claude-cli)
- **Evidence checked:** Touch prediction overlay; careful not to fake latency — local ghost only.
- **Verdict:** **ACCEPT**

## M37
- **Source:** `claude-solutions/M37.md` (claude-cli)
- **Evidence checked:** WASD/keyboard discovery; in-product map over help-only docs.
- **Verdict:** **ACCEPT**

## M38
- **Source:** `claude-solutions/M38.md` (claude-cli)
- **Evidence checked:** Root/Magisk: do not promote root for conversion. If offered, risk sheet + SafetyNet/Play Integrity warn; default non-root.
- **Verdict:** **REVISE**
- **Revised solution:** Default non-root. Root only behind explicit risk sheet naming Play Integrity / banking breakage; never one-click Magisk in help.

## M39
- **Source:** `claude-solutions/M39.md` (claude-cli)
- **Evidence checked:** Multi-unpaid-orders; single checkout intent + idempotency matches market-api stub direction.
- **Verdict:** **ACCEPT**

## M40
- **Source:** `claude-solutions/M40.md` (claude-cli)
- **Evidence checked:** Region without RTT; pairs with shipped M06 RTT chip — probe before region pick.
- **Verdict:** **ACCEPT**

## M41
- **Source:** `claude-solutions/M41.md` (claude-cli)
- **Evidence checked:** App–OS compatibility gap; derived minSdk signals + filter apply fits M13 spec chips.
- **Verdict:** **ACCEPT**

## M42
- **Source:** `claude-solutions/M42.md` (claude-cli)
- **Evidence checked:** Farm density anti-pattern; three-tier viewport matches phone-first / focus mode.
- **Verdict:** **ACCEPT**

## M43
- **Source:** `claude-solutions/M43.md` (claude-cli)
- **Evidence checked:** Share-without-expiry gap (GAPS#18); in-phone share + expiry/watermark.
- **Verdict:** **ACCEPT**

## M44
- **Source:** `claude-solutions/M44.md` (claude-cli)
- **Evidence checked:** SMS add-on surprise; inbox-from-minute-zero honesty — cost disclosure required, no fake free SMS claims.
- **Verdict:** **ACCEPT**

## M45
- **Source:** `claude-solutions/M45.md` (claude-cli)
- **Evidence checked:** API/UI parity; schema-driven filters align with DeviceSpec (M13).
- **Verdict:** **ACCEPT**

## M46
- **Source:** `claude-solutions/M46.md` (claude-cli)
- **Evidence checked:** Data retention / factory reset affordance inside phone Privacy pill.
- **Verdict:** **ACCEPT**

## M47
- **Source:** `claude-solutions/M47.md` (claude-cli)
- **Evidence checked:** Codec/resolution control inside phone for weak networks — pairs M14/M35.
- **Verdict:** **ACCEPT**

## M48
- **Source:** `claude-solutions/M48.md` (claude-cli)
- **Evidence checked:** No upsell overlays on stream rect; stream sovereignty matches M15 immersion.
- **Verdict:** **ACCEPT**

## M49
- **Source:** `claude-solutions/M49.md` (claude-cli)
- **Evidence checked:** First-run tour inside phone frame — not external chat.
- **Verdict:** **ACCEPT**

## M50
- **Source:** `claude-solutions/M50.md` (claude-cli)
- **Evidence checked:** Status/outage honesty inside phone; GAPS#14.
- **Verdict:** **ACCEPT**

## M51
- **Source:** `claude-solutions/M51.md` (claude-cli)
- **Evidence checked:** Tax/FX clarity; show line items in checkout stub — keep stub cents, no invented FX rates.
- **Verdict:** **ACCEPT**

## M52
- **Source:** `claude-solutions/M52.md` (claude-cli)
- **Evidence checked:** Razorpay/UPI local methods already stubbed in market-api; region method rail OK in test mode.
- **Verdict:** **ACCEPT**

## M53
- **Source:** `claude-solutions/M53.md` (claude-cli)
- **Evidence checked:** Native select/focus for pickers+pay; web-market already uses real <select>.
- **Verdict:** **ACCEPT**

## M54
- **Source:** `claude-solutions/M54.md` (claude-cli)
- **Evidence checked:** Audio as visible controllable channel; do not claim perfect A/V sync without measurement.
- **Verdict:** **ACCEPT**

## M55
- **Source:** `claude-solutions/M55.md` (claude-cli)
- **Evidence checked:** Core Strlix differentiator — AI as in-phone agent app, zero outside chat (RESEARCH table).
- **Verdict:** **ACCEPT**

## Summary
- ACCEPT: 50
- REVISE: 5
- REJECT: 0
- Verified IDs: 55 / 55
- Pending: 0
- REVISE list: M06, M11, M16, M21, M38
- Claude solutions on disk: 55/55 (all SOURCE: claude-cli; M55 regenerated after trailing-newline skip in `_mistake_ids.txt`)
- UI patches shipped: M06 RTT est. chip; M11 datacenter network labels; Android 7 JPEG note; published $/hr pricing
- Serve: web-market **:8765** and **http://127.0.0.1:8792/market/** (:8790/:8791 = sand-egress-tunnel on this box)
- Updated: 2026-09-21 IST

# Phone full-bleed fix — 2026-09-23 (~09:05 IST)

Standing APPROVED. Soft-launch is **phone-first**. AWS GPU left **stopped**.

## Symptom (Ankit)

> UI is not good full screen not coming for phone also

On a real phone browser the cloud Android frame was a **small centered bezel** with chrome/letterboxing — not edge-to-edge.

## Root cause

| Surface | Bug |
|---------|-----|
| **Stream** `static/index.html` | Full-bleed CSS only applied under `html.embed`. Opening `/?v=…` on a phone kept `.device { height: min(100dvh - 172px, 840px); max-width: 420px }` → floated mini-phone + topbar/footer. |
| **Market** `web-market/css/market.css` | Immersive rules at `max-width: 920px` were correct, but a later `@media (max-width: 560px)` reset `.device-frame` to the small bezel. |
| **Letterbox paint** | `layoutView()` used **contain** (`Math.min`) so even a full-bleed stage could show black bars. |

## Fix

1. **Auto `phone-fs`** on coarse/narrow viewports (and always with `?embed=1`).
2. **`html.phone-fs` / `html.embed`** share full-bleed CSS: `100dvh`/`100svh`, no bezel radius/padding, hide topbar/footer/nav-rail.
3. **`layoutView` cover** when immersive (`Math.max`) so the stream crops instead of letterboxing; touch mapping still uses `viewRect`.
4. Market CSS: immersive query also matches `(pointer: coarse) and (hover: none)`; **560px rule scoped to `#phoneStage:not(.open)`**; iframe forced full-bleed.
5. Faster chrome auto-hide (~1.4s). `viewerBuild` / `viewerRev`: **`20260923-fs1`**.

**Not touched:** `f32-planar` audio path, `/ws/h264` motion (fast1), viewerBuild chain shape, AWS GPU.

## Deploy

| Target | Result |
|--------|--------|
| VM static `/home/azureuser/strlix/static/index.html` | **168516** B; `viewerBuild: '20260923-fs1'` + `phone-fs` |
| Stream AFD `?v=20260923-fs1` | Serves phone-fs HTML |
| Market image | `acrzevistrlix.azurecr.io/market-api:0.7.3-fs1c` |
| CA revision | **`ca-market-api--0000029`**; health **`0.7.3+fs1`** |
| AWS GPU `i-0531c567f620877c3` | **stopped** |

## Proof (Playwright mobile 390×844)

| Shot | Result |
|------|--------|
| BEFORE stream direct | device **359×672**, topbar visible, letterboxed bezel |
| AFTER stream direct | device **390×844**, `phoneFs: true`, topbar hidden |
| AFTER market open | stage **390×844**, iframe **390×844** |

Artifacts: `/workspace/strlix-overnight/phone-fs-proof/` (also `demo/launch/phone-fs-proof/`).

## URLs for Ankit (hard-refresh)

- Stream: https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/?v=20260923-fs1
- Market: https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/?cb=20260923-fs1  
  → tap **Open phone**

On Chrome mobile: stream should be edge-to-edge (no floated bezel). Market open stage fills the viewport; thin chrome fades after ~1.4s.

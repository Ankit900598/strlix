# Strlix UI Research Notes — sources & transferable principles
**Date:** 2026-09-21 IST (Asia/Calcutta)  
**Used by:** `BILLION-USER-UI.md` · Claude draft: `CLAUDE-UI.md`

## Phone OS

| Source | Steal | Avoid |
|---|---|---|
| **Pixel / iOS simplicity** | Ruthless first-run subtraction; one hero action; system-native permission honesty | Settings sprawl; dual entry points |
| **Dynamic Island** (Apple) | Transient state living *in* the silhouette — Needs-you pill drops from top, carries meaning, then collapses | Decorative motion without information |
| **AssistiveTouch** | Edge-snapping, opacity-fades, optional forever | Making overlay mandatory |
| **Gemini visual design** ([design.google](https://design.google/library/gemini-ai-visual-design)) | Circles/rounded containers as comfort; gradients only for *energy of thinking*; motion that personifies process | Clippy-era static mascot; competing chrome saturation |
| **Gemini 2026 UX 2.0 / Generative UI** | Response can be an interface, not a wall of text — for Strlix: the *phone screen doing the task* is the generative UI | Treating chat log as the product |

## AI companions

| Source | Steal | Avoid |
|---|---|---|
| **ChatGPT / Claude apps** | Voice-mode orb quality; streaming feel; composer as hero | Sidebars of threads, model pickers, regenerate, "New chat" |
| **Perplexity** | Answer-first; sources tucked | Becoming a research tool with citation chrome |
| **Character.ai** | Presence > affordance; relationship/return loop; silence can be engagement | Parasocial dark patterns; lonely-loop optimization; bolted-on streaks |
| **Time-to-magic** (category lesson) | Measure open → first delightful outcome in seconds, not minutes | Long interest-picker onboarding that delays the magic (TikTok 2025–26 regression warning) |

## Hardware AI failures (must internalize)

From [Digital Applied 2026 failures](https://www.digitalapplied.com/blog/ai-product-failures-2026-sora-humane-rabbit-lessons) + UX fail writeups:

1. **Novelty ≠ PMF** — demo hype ≠ retention. Humane <$10k units after $230M; Rabbit mass returns after 100k CES sales.
2. **Don't replace the phone** — Humane asked users to abandon the winning device. Strlix *is* a phone (cloud) and *lives inside* Android.
3. **Hide latency or die** — Rabbit 5–10s dead air. Voice-only leaves nothing to look at. Strlix: 16ms ack + moving screen.
4. **Ship what you demo** — Rabbit demo→delivery gap destroyed trust.
5. **Survivors share:** sustainable economics, integrate into existing workflows (don't replace them), consistency > peak demo.

## Device mirrors

| Source | Steal | Avoid |
|---|---|---|
| **scrcpy** | Input latency discipline; click-to-touch; minimal chrome | Entire visual language of a hacking tool |
| **BrowserStack Live** | Device as hero | Toolbars, device grids, QA framing — that is *not* consumer |
| **Apple Continuity** | Silent clipboard, drag-drop, zero-config | — |
| **Samsung DeX** | — | Identity crisis: phone pretending to be a desktop. Strlix is always a phone window. |

## Consumer love patterns

| Source | Transferable principle |
|---|---|
| **TikTok first session** | First action below decision threshold; wow before account. Warning: heavy interest pickers *increase* drop-off. |
| **Reels / Shorts** | First 3 seconds decide stay/leave — Strlix: first 3s = S mark + phone booting, not a carousel. |
| **Superhuman** | Sub-100ms everything; keyboard-first desktop; obsessive polish |
| **Linear** | One accent on dark; `⌘K`; motion that means something |
| **Stripe docs** | Error copy names the *exact* thing; three-part errors: what / meaning / one button |

## Trust / permissions

- Accessibility is treated by security teams as a **privileged control**, not a convenience toggle — framing must be assistive + visible + revocable.
- Overlay attacks are a known banking-trojan vector — never gate core product on overlay; frame it as optional AssistiveTouch-style bubble.
- Android 2026 trust pattern: ask **least** privilege, at **point of need**, show **blast radius** in human words.
- Strlix trust triad (from vision): earn → visible while *active* (not merely enabled) → one-tap revoke forever.

## Voice / barge-in

Industry consensus 2026: full-duplex + VAD; the 100–200ms window between interrupt and silence is where voice agents win or feel like playback. Spec in main doc: duck 80ms / hard cancel p95 ≤120ms.

## Existing Strlix grounding (repo)

- Accent Android: `#6C8CFF` (`zevi_accent`); desktop brief `#5B8CFF` — unify on indigo family, prefer `#5B8CFF` for chrome + keep `#6C8CFF` acceptable sibling.
- Surfaces: `#0B1020` / `#151B2E` / `#1E2640` (android colors.xml).
- Constraints honored: AI inside phone; desktop = bezel viewer; android-api ≠ desktop-api; rejected big web chat.
- Prior audits: `demo/ux-audit-strlix.md`, `demo/ui-redesign-claude.md`, `demo/live-voice.md`.

# Live E2E probes (real input, through AFD)

These drive the live stream viewer in headless Chrome with real CDP touch (390×844 mobile), check the phone over adb (ssh to the VM), and print numbers.
Environment: `STRLIX_VM_KEY` (ssh key path), `STRLIX_VM` (user@host, required; default key `~/.ssh/strlix-vm.pem`); results are written under `/workspace/strlix-overnight/sprint-1005/<label>/`.

| Script | Measures |
|---|---|
| `feel_e2e.py <label> <tag>` | Full feel regression: open Chrome, link, edge Back, rail Back, scroll, tab switcher, Recents gesture/button/dismiss, tap→frame, first frame |
| `recents_bench.py <label> <N>` | N × (Recents button + card swipe) and N × (swipe-up-hold from an app + card swipe) |
| `tap_probe.py <ws_url> [N]` | Raw WS: DOWN→ack and DOWN→first H.264 AU (no browser) |
| `join_probe.py <ws_url>` | WS open / hello / first AU for a new viewer |
| `ff_diag.py <url>` | First-frame breakdown: TTFB, HTML, WS created/open, hello, first AU, first paint |
| `lag_probe.py` | Viewer handler lag (OS touch time → WS send) |
| `live_tile_afd.py home|app N` (env `WS=`) | Clean WS client Recents dismiss over AFD |

Harness lessons (5 Oct): don't await each `Input.dispatchTouchEvent` (each waits ~35 ms for the renderer ack, so sends drift). Pass `timestamp`. Shell-quote URLs with `()` in `adb shell am start`. example.com no longer has a link.

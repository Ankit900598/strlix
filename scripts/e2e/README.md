# Live E2E regression (real input, through AFD)

## Run everything with one command

```bash
# one-time: Python 3.10+ with playwright + websockets, and Google Chrome
python3 -m venv ~/.strlix-e2e && ~/.strlix-e2e/bin/pip install playwright websockets
export STRLIX_VM=azureuser@<vm-ip>            # required
export STRLIX_VM_KEY=~/.ssh/strlix-vm.pem     # ssh key for the VM (default shown)
PYTHON=~/.strlix-e2e/bin/python scripts/e2e/run_all.sh          # full, about 15 min
PYTHON=~/.strlix-e2e/bin/python scripts/e2e/run_all.sh quick    # skip the Recents benches, about 7 min
```

Needs the stack resumed: VM running, AFD endpoints enabled (allow up to ~25 min after enabling).
Optional: `STRLIX_STREAM_URL`, `STRLIX_EDGE_URL`, `CHROME` (Chrome binary), `STRLIX_E2E_OUT` (default `/tmp/strlix-e2e`).

Output: `$STRLIX_E2E_OUT/<run-id>/summary.md` (table of PASS/FAIL/INFO), `summary.json`, the raw logs and failure screenshots. Exit code 0 means every hard check passed.

What it checks:
1. HTTP 200 on the edge market page `/market/`, edge `/health`, edge `/android/health` and stream `/health`; the phone is on adb and booted.
2. Latency through AFD (raw WS, no browser): tap and home-screen drag, with RTT, DOWN→ack, DOWN→first frame and the server-side breakdown (pace, inject, inject→frame, frame→send). INFO only.
3. Feel regression in headless Chrome with real touch: open Chrome, tap link, edge Back, rail Back, scroll, close tab, Recents gesture/button/dismiss, first frame (cold → warm).
4. `full` only: Recents dismiss bench (3 × button, 3 × swipe-up from an app) and the "after a bad drag" bench on the VM (6 trials, pass at ≥5/6).

A single Recents miss can be launcher flakiness. Rerun before treating it as a regression.

## Individual probes

These drive the live stream viewer in headless Chrome with real CDP touch (390×844 mobile), check the phone over adb (ssh to the VM), and print numbers.
Environment: `STRLIX_VM_KEY` (ssh key path), `STRLIX_VM` (user@host, required; default key `~/.ssh/strlix-vm.pem`); results are written under `$STRLIX_E2E_OUT/<label>/`.

| Script | Measures |
|---|---|
| `feel_e2e.py <label> <tag>` | Full feel regression: open Chrome, link, edge Back, rail Back, scroll, tab switcher, Recents gesture/button/dismiss, tap→frame, first frame |
| `recents_bench.py <label> <N>` | N × (Recents button + card swipe) and N × (swipe-up-hold from an app + card swipe) |
| `tap_probe.py <ws_url> [N]` | Raw WS: DOWN→ack and DOWN→first H.264 AU (no browser) |
| `join_probe.py <ws_url>` | WS open / hello / first AU for a new viewer |
| `ff_diag.py <url>` | First-frame breakdown: TTFB, HTML, WS created/open, hello, first AU, first paint |
| `lag_probe.py` | Viewer handler lag (OS touch time → WS send) |
| `trace_probe.py <wss_url> [N]` (env `MODE=drag`, `HOLD_MS`) | Tap/drag latency breakdown with the server `tap_trace` |
| `poison_bench.py <poison 0/1> <gap_s> <N>` (on the VM) | Recents fling after a deliberately bad slow drag |
| `live_tile_afd.py home|app N` (env `WS=`) | Clean WS client Recents dismiss over AFD |

Harness lessons (5 Oct): don't await each `Input.dispatchTouchEvent` (each waits ~35 ms for the renderer ack, so sends drift). Pass `timestamp`. Shell-quote URLs with `()` in `adb shell am start`. example.com no longer has a link.

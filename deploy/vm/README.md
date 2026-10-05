# VM phone stack (vm-strlix-india): units, knobs and how to verify

Everything here is installed on the VM by copying it to the paths named at the top of each file
and then running `sudo systemctl daemon-reload`. The code itself lives in `~/strlix` (rsync or scp from this repo).

## Units
| Unit | What it does |
|---|---|
| `strlix-emulator.service` (+ `strlix-emulator-zz-restart.conf`) | AVD `strlix_ps`, swiftshader, `Restart=always` |
| `strlix-adb.service` | adb server in its own unit. Before, it was forked inside desktop-api's cgroup, so a desktop-api restart took the phone `offline` |
| `strlix-phone-ready.service` | PartOf/BindsTo the emulator. Waits for `sys.boot_completed`, applies `scripts/normal-feel-profile.sh`, wakes/unlocks, goes Home |
| `strlix-desktop-api.service` + drop-ins | Stream/input API on :8789. Drop-ins sort by name; later ones win: `zz-normal1` (stream profile), `zz-adb` (ordering), `zz-agent1` (Ask bridge → android-api), `zz-perf1` (warm encoder) |
| `strlix-watchdog.timer` → `scripts/phone-watchdog.sh` | Every 60 s. `adb reconnect offline`; restarts the emulator after 300 s without a booted device; restarts desktop-api after 120 s of failing `/health`; re-applies net-tune if a DHCP renew dropped it. Time-based, so manual re-runs can't trigger restarts |
| `strlix-net-tune.service` → `scripts/net-tune.sh` | `initcwnd/initrwnd 32` on the default route (the first key frame + gzipped viewer fit in one flight) |
| `/etc/sysctl.d/99-strlix-net.conf` | `tcp_slow_start_after_idle=0`, BBR, fq |

## Knobs (desktop-api env)
| Env | Default | Meaning |
|---|---|---|
| `H264_KEEP_WARM_S` | 0 (VM: 1800) | Keep scrcpy + GOP replay warm from boot and for N s after the last viewer, so a join is ~10 ms instead of a 0.5–0.7 s cold start |
| `MOTION_PLAYOUT_MS` | 40 | Base touch jitter buffer. MOVE/UP are replayed at the client's timing (`t` = PointerEvent.timeStamp) |
| `MOTION_PACE_ADAPT` | 0 (off) | Opt-in adaptive buffer (A/B 6/10 vs 6/10, so off by default): grows with observed lateness, re-anchors late events, shifts the whole gesture (DOWN too) by the adaptive part. Clean link = no DOWN delay |
| `MOTION_PACE_MAX_MS` | 250 | Cap for the adaptive buffer |
| `ANDROID_API_URL` | – | Where `POST /chat` (viewer Ask) sends turns; the tools then run on the phone over ADB |
| `AGENT_MAX_ROUNDS`, `AGENT_CHAT_PER_MIN` | 3, 12 | Ask bridge limits |

## Verify (numbers seen on 5 Oct 2026, from a US box through AFD)
- `curl -s localhost:8789/health | jq '.h264 | {running,gop_valid,warm_left_s}'`: running, gop_valid true.
- `curl -s localhost:8789/health | jq .touch_pacing`: `buffer_ms` (≈40 on a clean link) and the `last` gesture trace `[action, client_ms, inject_ms]`.
- First paint of the stream page: about 1.2–1.3 s warm (was 3.0 s). WS hello → first AU 17 ms.
- `systemctl list-timers strlix-watchdog.timer`; `journalctl -u strlix-watchdog -u strlix-phone-ready`.

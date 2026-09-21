# Overnight sprint — MISTAKES / bugs found

1. **`_preview_lock` serialized every viewer**  
   Each MJPEG client and `/adb/preview` ran its own screencap behind one lock → ~1fps and 1.6–2.5s preview under load. Felt like “clicks do nothing” because the screen didn’t update.

2. **Live path wrote PNGs to `demo/` historically**  
   Pilot/chat screenshot spam filled disk and competed with IO. Live path must be memory-only.

3. **Coordinate mapping used `img.naturalWidth`**  
   For MJPEG/`<img>` before first decode, `naturalWidth` is 0 → `clientToDevice` returned `null` → silent no-op taps. Fixed by mapping from **device aspect + letterboxed viewRect**, with overlay `#touchLayer`.

4. **No post-tap refresh on MJPEG path**  
   Tap succeeded on device but UI stayed on old frame for a full interval. Fixed with `nudge` / `nudge_soon` after tap/swipe/key.

5. **HOME/BACK not wired as `/adb/key` in older UI**  
   Users couldn’t leave apps from the chrome. Added nav keys + `/adb/key`.

6. **Settings is not on the home grid**  
   QA expectation “click Settings” fails on home; must open app drawer (swipe up) first. Documented; verified via drawer.

7. **Aggressive capture abort on every nudge**  
   Triple `nudge_soon` could cancel in-flight screencap too often (`aborted_captures` rose; occasional 1.4s capture spikes). Tuned `ABORT_COOLDOWN` 0.5→0.8s and delayed follow-up nudges.

8. **Claude Code rewrote APIs mid-flight**  
   Empty `claude-run.log` (stdout buffering) but files landed. Had to reconcile `AdbClient` method names with `pilot.py` (`type_text`, `screenshot`, `key`, …) and restart uvicorn after Claude’s process exited.

9. **Playwright `page.evaluate` arity**  
   Passing multiple positional args to `evaluate` throws; must pass one array/object. Wasted time on false “click broken” failures.

10. **Chrome hotseat tap flaky if not fully on home**  
    After Gmail, HOME must settle before Chrome coords are valid; otherwise tap lands on wrong surface.

11. **`/api/stream/stats` 404**  
    Old probe path; real endpoint is `/adb/stream/stats`.

12. **Background uvicorn SIGKILL (137) in sandbox**  
    `nohup` child sometimes reaped; process still survived from Claude’s earlier start. Prefer explicit PID check via `ss -tlnp`.

13. **Frame producer exits and does not respawn while viewers remain**  
    Idle-stop correctly ends the task at 0 subscribers, but any crash/exit with `subscribers > 0` left MJPEG/WS clients stalled until a *new* subscribe. Fixed: `_stopping` flag, `finally` auto-restart when viewers remain, `_ensure_task()` from `nudge`/`next_frame`.

14. **Optimistic client nudge missing on some paths**  
    Server nudged after tap completed (~100ms later). Client now calls `nudgeStream()` immediately on `sendInput` so the next frame starts ASAP.

13. **`screenrecord` rarely emits IDRs after start** — late joiners need SPS/PPS + IDR. Fixed with GOP replay buffer + rate-limited producer **segment restart** on join when GOP unusable.

14. **Idle flush mid-NAL corrupted AUs** — flushing Annex-B on a short idle timer split NALs. Raised/guarded flush so only complete NALs emit (`misflushes` → 0 in stats).

15. **Hello before SPS** — WS hello advertised geometry before SPS arrived; decoder configured wrong. Wait for SPS/PPS (or send hello after first keyframe).

16. **scrcpy-web deferred** — scrcpy 4.1 works for file record headless, but needs XDG/SDL for interactive mirror; overnight chose `screenrecord` stdout for zero device push.

17. **Duplicate uvicorn PIDs** — orphan processes after restarts; always bind-check `ss -tlnp :8787` and kill non-listeners.

18. **Cloudflare blip during uvicorn recycle** — quick tunnel stayed up; origin 502'd briefly. Public URL unchanged: `dicke-materials-vendors-maritime.trycloudflare.com`.

## Session 2 — H.264 path

13. **Idle-flushing Annex-B mid-write corrupted frames**  
    Annex-B has no length prefix, so a quiet pipe was read as "NAL finished".
    Over an SSH-tunnelled ADB a large NAL genuinely stalls mid-write, so the
    parser published half a slice: `ffmpeg` reported *Invalid level prefix /
    error while decoding MB*, and every following P-frame inherited it. Fixed
    with two-tick stability, a flush window calibrated from measured mid-NAL
    stalls, mis-flush detection (orphaned tail bytes) and an IDR resync.
    **A browser hides this bug** — it just renders a smear. `ffmpeg -f null -`
    on the captured stream is what actually catches it.

14. **Measuring intra-NAL gaps without checking the seam**  
    Counting the gap before *every* chunk as "mid-NAL" fed idle time between
    frames into the calibration, so the flush window ran away to its 250 ms
    ceiling and dragged latency with it. Only count a gap when the arriving
    chunk does not begin a new NAL (start code at or across the seam).

15. **`00 00 00 01` looks like garbage to a 3-byte start-code search**  
    `find(b"\x00\x00\x01")` lands on the *tail* of a 4-byte start code, so the
    leading zero counted as skipped bytes and tripped the mis-flush detector on
    a perfectly healthy stream. Leading zeros are legal padding — only nonzero
    leading bytes mean truncation.

16. **Closing a WebSocket before `accept()` is invisible to the browser**  
    The over-capacity path did `ws.close(1013)` pre-accept, which the browser
    sees as HTTP 403 / code 1006 — indistinguishable from "server down", so the
    client retried instead of falling back. Accept, send the reason, *then*
    close 1013.

17. **`hello` sent before the encoder's SPS existed**  
    Advertised a placeholder codec (`avc1.42E01E`) and height 0, so the decoder
    was configured for the wrong stream. Wait for the segment's SPS
    (`wait_ready`) before greeting the client.

18. **Unhashable dataclass in a `set`**  
    `@dataclass` without `eq=False` kills `__hash__`; subscribers live in a set.

19. **Sequential A/B benchmarking on an emulator is worthless**  
    App-launch time on swiftshader varies by seconds — larger than the effect.
    First runs "showed" H.264 both 4x faster and 2x slower. Only the paired
    setup (two browsers, one device event, watched simultaneously) gives a
    number worth quoting.

20. **`pkill -f "port 8788"` matched the shell running it**  
    The pattern appears in the invoking command line too, so the sandbox killed
    its own session (exit 144). Kill by PID from `ss -tlnp` instead.

21. **QA that starts from an unknown screen measures the phone, not the code**  
    A "tap Gmail" test run while the device sat on Recents reported *no pixels
    changed* and looked like a broken pipeline. Drive HOME and let it settle
    before every measurement.

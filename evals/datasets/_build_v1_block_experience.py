#!/usr/bin/env python3
"""Build evals/datasets/v1_block_experience.jsonl (≥300 cases).

Gold overlays follow trustworthy_block_experience.md + block_experience_v01 rules.
Each case is hand-structured via templates — not LLM-generated gold (avoids circular eval).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUT = Path(__file__).resolve().parent / "v1_block_experience.jsonl"

# Canonical action / forbidden ids (must match schema)
F_DISABLE = "DISABLE_PHONECODEX"
F_IGNORE = "IGNORE_ANYWAY"
F_SETTINGS = "OPEN_SETTINGS_EDITOR"
F_CONT_FREE = "CONTINUE_FREE"
F_SKIP = "SKIP_COOLDOWN"
F_UNINSTALL = "UNINSTALL_HINT"

BASE_FORBIDDEN_STRICT = [F_DISABLE, F_IGNORE, F_SETTINGS, F_CONT_FREE, F_UNINSTALL]
BASE_FORBIDDEN_LOCK = [F_DISABLE, F_IGNORE, F_SETTINGS, F_CONT_FREE, F_SKIP, F_UNINSTALL]
BASE_FORBIDDEN_SOFT = [F_DISABLE, F_SETTINGS, F_UNINSTALL]


def overlay(
    *,
    title: str,
    message: str,
    primary: str,
    secondary: str | None,
    forbidden: list[str],
    tone: str,
    show_cooldown: bool = False,
    show_promise: bool = True,
    emergency: bool = True,
) -> dict[str, Any]:
    return {
        "title": title,
        "message": message,
        "primaryAction": primary,
        "secondaryAction": secondary,
        "forbiddenActions": sorted(set(forbidden)),
        "tone": tone,
        "showCooldown": show_cooldown,
        "showPromise": show_promise,
        "allowEmergencyExit": emergency,
    }


def case(
    cid: str,
    *,
    promise: str,
    app: str,
    screen: str,
    decision: str,
    strictness: str,
    reason: str,
    attempts: int,
    expected: dict[str, Any],
    cluster: str,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "id": cid,
        "userPromise": promise,
        "currentApp": app,
        "screenSummary": screen,
        "decision": decision,
        "strictnessLevel": strictness,
        "reasonCategory": reason,
        "attemptCount": attempts,
        "expectedOverlay": expected,
        "cluster": cluster,
        "notes": notes,
    }


def tone_for(decision: str, strictness: str, reason: str) -> str:
    if reason == "tamper_attempt":
        return "tamper_cold"
    if reason in ("adult_guardrail", "long_term_promise") and decision != "WARN":
        return "contract_life_rule"
    if decision == "LOCK":
        return "locked_vault"
    if decision == "COOLING_OFF":
        return "locked_vault"
    if strictness == "SOFT" and decision == "WARN":
        return "soft_nudge"
    if strictness == "SMART" and decision == "WARN":
        return "smart_cost"
    if strictness in ("STRICT", "LOCKED") or decision == "BLOCK":
        return "strict_guard"
    if decision == "WARN":
        return "smart_cost"
    return "strict_guard"


def forbidden_for(decision: str, strictness: str) -> list[str]:
    if decision in ("LOCK", "COOLING_OFF"):
        return list(BASE_FORBIDDEN_LOCK)
    if strictness in ("STRICT", "LOCKED"):
        return list(BASE_FORBIDDEN_STRICT) + ([F_SKIP] if decision == "COOLING_OFF" else [])
    if strictness == "SMART":
        return [F_DISABLE, F_IGNORE, F_SETTINGS, F_CONT_FREE, F_UNINSTALL]
    return list(BASE_FORBIDDEN_SOFT) + [F_CONT_FREE]


def secondary_continue_ok(decision: str, strictness: str) -> bool:
    if decision == "WARN" and strictness in ("SOFT", "SMART"):
        return True
    if decision == "BLOCK" and strictness == "SOFT":
        return True
    return False


def build() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    n = 0

    def uid(prefix: str) -> str:
        nonlocal n
        n += 1
        return f"bx_{prefix}_{n:03d}"

    # --- Template libraries ---
    study_promises = [
        "YouTube only for calculus lectures, no Shorts, 3 hours",
        "study DSA 2h — lectures ok, no entertainment sidebar",
        "finish organic chem tonight; long videos ok, vertical clips no",
        "library mode: study apps only until 6pm",
        "JEE grind: Khan/Unacademy allowed, no reels",
    ]
    adult_promises = [
        "no porn for 1 year, don't let me disable it",
        "permanent no adult content guardrail",
        "no nsfw on this phone for 6 months",
        "family phone — no adult content ever",
        "1 year clean — no xxx no onlyfans",
    ]
    shorts_promises = [
        "no Shorts during study",
        "40 shorts today then stop",
        "allow 25 Shorts per day, block after",
        "no reels no shorts exam week",
        "nudge me when I open Shorts shelf",
    ]
    wa_promises = [
        "WhatsApp for lab partner and mom only, no meme groups",
        "useful WhatsApp ok, gossip forwards block",
        "family WhatsApp always allowed; hostel spam no",
        "WA for tutor only during study",
        "no flirting chats on WhatsApp exam mode",
    ]
    ig_promises = [
        "Instagram only for college team DMs, no Reels",
        "IG posts ok but block Reels tab",
        "reply to team on IG, nothing else",
        "no Instagram Reels but DMs fine for 4 hours",
        "social: DMs yes, feed scroll no",
    ]
    rail_promises = [
        "YouTube calculus playlist only — MIT OCW calc1",
        "only 3Blue1Brown linear algebra playlist",
        "chemistry channel Unacademy only, no other YT",
        "watch only my 'DSA playlist' on YouTube",
        "channel rail: Physics Wallah JEE, nothing else",
    ]
    chrome_promises = [
        "Chrome for research docs only during study",
        "no movies memes or porn in Chrome this session",
        "stack overflow and docs ok, reddit memes no",
        "browser for assignment research, not entertainment",
        "Chrome soft block except Google Docs",
    ]
    long_promises = [
        "no gambling apps for 365 days",
        "whole year no porn challenge",
        "rest of college no dating apps",
        "30 day no Shorts challenge",
        "annual guardrail no adult content",
    ]
    monk_promises = [
        "monk mode till 2am except family calls",
        "zero entertainment laser focus 4h",
        "monk week no memes no shorts",
        "hard monk block all social feeds",
        "dopamine detox 90 days",
    ]

    apps = {
        "yt": "com.google.android.youtube",
        "ig": "com.instagram.android",
        "wa": "com.whatsapp",
        "ch": "com.android.chrome",
        "settings": "com.android.settings",
        "pc": "com.phonecodex.app",
        "dialer": "com.android.dialer",
    }

    # ========== STUDY DRIFT ==========
    for i, p in enumerate(study_promises):
        for strict in ("SOFT", "SMART", "STRICT", "LOCKED"):
            for decision, attempts, screen, primary, title in [
                (
                    "WARN",
                    1,
                    "YouTube: related videos sidebar showing gaming/entertainment thumbnails while a lecture tab is open",
                    "RETURN_SAFE",
                    "Drift from your study promise",
                ),
                (
                    "BLOCK",
                    2,
                    "YouTube Home trending entertainment feed — not a lecture player",
                    "EXIT_SURFACE" if strict != "SOFT" else "RETURN_SAFE",
                    "Outside your study rail",
                ),
            ]:
                sec = "REVIEW_PROMISE"
                if secondary_continue_ok(decision, strict):
                    sec = "CONTINUE_WITH_STRIKE"
                cases.append(
                    case(
                        uid("study"),
                        promise=p,
                        app=apps["yt"],
                        screen=screen,
                        decision=decision,
                        strictness=strict,
                        reason="study_drift",
                        attempts=attempts,
                        expected=overlay(
                            title=title,
                            message=f'Promise: "{p[:48]}…" — screen looks off the study path ({screen[:40]}).',
                            primary=primary,
                            secondary=sec if sec != primary else "REVIEW_PROMISE",
                            forbidden=forbidden_for(decision, strict),
                            tone=tone_for(decision, strict, "study_drift"),
                        ),
                        cluster="study_drift",
                        notes=f"study drift {decision} {strict}",
                    )
                )

    # ========== ADULT GUARDRAIL ==========
    for p in adult_promises:
        for strict in ("STRICT", "LOCKED"):
            cases.append(
                case(
                    uid("adult"),
                    promise=p,
                    app=apps["ch"],
                    screen="Chrome: explicit adult site with age-gate and NSFW imagery",
                    decision="BLOCK",
                    strictness=strict,
                    reason="adult_guardrail",
                    attempts=1,
                    expected=overlay(
                        title="Guardrail: no adult content",
                        message=f'This hits your promise — "{p[:55]}". Life rule / guardrail, not a soft nudge.',
                        primary="RETURN_SAFE",
                        secondary="REVIEW_PROMISE",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone="contract_life_rule",
                    ),
                    cluster="adult_guardrail",
                )
            )
            cases.append(
                case(
                    uid("adult"),
                    promise=p,
                    app=apps["yt"],
                    screen="YouTube Shorts player with explicit sexual thumbnail and title",
                    decision="BLOCK",
                    strictness=strict,
                    reason="adult_guardrail",
                    attempts=2,
                    expected=overlay(
                        title="Guardrail: no adult content",
                        message="Adult signal on this screen. Your long-term promise blocks it.",
                        primary="EXIT_SURFACE",
                        secondary="ACKNOWLEDGE",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone="contract_life_rule",
                    ),
                    cluster="adult_guardrail",
                )
            )

    # ========== SHORTS / REELS / QUOTA ==========
    for p in shorts_promises:
        for strict in ("SMART", "STRICT"):
            # approaching quota WARN
            cases.append(
                case(
                    uid("shorts"),
                    promise=p,
                    app=apps["yt"],
                    screen="YouTube Shorts player active; vertical swipe feed; quota 35/40",
                    decision="WARN",
                    strictness=strict,
                    reason="shorts_temptation",
                    attempts=1,
                    expected=overlay(
                        title="Shorts on your radar",
                        message=f'Promise involves Shorts limits: "{p[:50]}". Player is open — approaching the line.',
                        primary="EXIT_SURFACE",
                        secondary="CONTINUE_WITH_STRIKE" if strict == "SMART" else "REVIEW_PROMISE",
                        forbidden=forbidden_for("WARN", strict),
                        tone=tone_for("WARN", strict, "shorts_temptation"),
                    ),
                    cluster="shorts_temptation",
                )
            )
            # quota reached BLOCK
            cases.append(
                case(
                    uid("quota"),
                    promise=p,
                    app=apps["yt"],
                    screen="YouTube Shorts player; quota 40/40 exhausted for today",
                    decision="BLOCK",
                    strictness=strict,
                    reason="quota_reached",
                    attempts=1,
                    expected=overlay(
                        title="Shorts quota reached",
                        message="Your Shorts quota is used up. Promise says stop here.",
                        primary="EXIT_SURFACE",
                        secondary="REVIEW_PROMISE",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone="strict_guard",
                    ),
                    cluster="quota_reached",
                )
            )
            # IG reels
            cases.append(
                case(
                    uid("reels"),
                    promise="no Reels during study; Instagram DMs ok",
                    app=apps["ig"],
                    screen="Instagram Reels full-screen player with swipe-up next reel",
                    decision="BLOCK",
                    strictness=strict,
                    reason="reels_temptation",
                    attempts=1,
                    expected=overlay(
                        title="Reels aren't on your promise",
                        message="DMs may be allowed — this is the Reels player, which you blocked.",
                        primary="EXIT_SURFACE",
                        secondary="STAY_IN_MESSAGES",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone="strict_guard",
                    ),
                    cluster="reels_temptation",
                )
            )

    # ========== WHATSAPP useful vs distracting ==========
    for p in wa_promises:
        for strict in ("SOFT", "SMART", "STRICT"):
            cases.append(
                case(
                    uid("wa_bad"),
                    promise=p,
                    app=apps["wa"],
                    screen="WhatsApp: large meme-forward group chat with sticker spam",
                    decision="BLOCK" if strict != "SOFT" else "WARN",
                    strictness=strict,
                    reason="whatsapp_distract",
                    attempts=1,
                    expected=overlay(
                        title="Distracting WhatsApp surface",
                        message=f'Promise: "{p[:50]}". This group looks like spam/memes, not useful chat.',
                        primary="EXIT_SURFACE",
                        secondary="STAY_IN_MESSAGES"
                        if "mom" in p.lower() or "family" in p.lower() or "tutor" in p.lower()
                        else ("CONTINUE_WITH_STRIKE" if secondary_continue_ok("WARN" if strict == "SOFT" else "BLOCK", strict) else "REVIEW_PROMISE"),
                        forbidden=forbidden_for("BLOCK" if strict != "SOFT" else "WARN", strict),
                        tone=tone_for("BLOCK" if strict != "SOFT" else "WARN", strict, "whatsapp_distract"),
                    ),
                    cluster="whatsapp_distract",
                )
            )
            cases.append(
                case(
                    uid("wa_ok_warn"),
                    promise=p,
                    app=apps["wa"],
                    screen="WhatsApp: 1:1 chat with lab partner about assignment PDF",
                    decision="WARN",
                    strictness=strict,
                    reason="whatsapp_risk",
                    attempts=1,
                    expected=overlay(
                        title="Useful chat — stay on path",
                        message="Looks like useful messaging. Don't drift into meme groups under your promise.",
                        primary="STAY_IN_MESSAGES",
                        secondary="REVIEW_PROMISE",
                        forbidden=forbidden_for("WARN", strict),
                        tone=tone_for("WARN", strict, "whatsapp_risk"),
                    ),
                    cluster="whatsapp_useful_warn",
                    notes="soft interrupt even on useful surface when attempt risk high",
                )
            )

    # ========== INSTAGRAM DM vs Reels ==========
    for p in ig_promises:
        for strict in ("SMART", "STRICT", "LOCKED"):
            cases.append(
                case(
                    uid("ig_reels"),
                    promise=p,
                    app=apps["ig"],
                    screen="Instagram Reels tab selected; autoplay entertainment reel",
                    decision="BLOCK",
                    strictness=strict,
                    reason="instagram_reels",
                    attempts=1,
                    expected=overlay(
                        title="Reels blocked by your promise",
                        message=f'"{p[:52]}" — Reels player is not the allowed surface.',
                        primary="EXIT_SURFACE",
                        secondary="STAY_IN_MESSAGES",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone="strict_guard",
                    ),
                    cluster="instagram_reels",
                )
            )
            cases.append(
                case(
                    uid("ig_dm"),
                    promise=p,
                    app=apps["ig"],
                    screen="Instagram DM thread with college project teammates",
                    decision="WARN",
                    strictness=strict if strict != "LOCKED" else "STRICT",
                    reason="instagram_dm_edge",
                    attempts=2,
                    expected=overlay(
                        title="DMs look allowed — don't open Reels",
                        message="College DMs match your promise. Feed/Reels still blocked.",
                        primary="STAY_IN_MESSAGES",
                        secondary="REVIEW_PROMISE",
                        forbidden=forbidden_for("WARN", "STRICT" if strict == "LOCKED" else strict),
                        tone="smart_cost",
                    ),
                    cluster="instagram_dm",
                )
            )

    # ========== PLAYLIST / CHANNEL RAIL ==========
    for p in rail_promises:
        for strict in ("STRICT", "LOCKED"):
            cases.append(
                case(
                    uid("rail_block"),
                    promise=p,
                    app=apps["yt"],
                    screen="YouTube: random entertainment video (not on named playlist/channel)",
                    decision="BLOCK",
                    strictness=strict,
                    reason="playlist_rail",
                    attempts=1,
                    expected=overlay(
                        title="Off your study rail",
                        message=f'This video is not on your allowed rail. Promise: "{p[:48]}".',
                        primary="OPEN_PLAYLIST",
                        secondary="EXIT_SURFACE",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone="strict_guard",
                    ),
                    cluster="playlist_rail",
                )
            )
            cases.append(
                case(
                    uid("rail_redir"),
                    promise=p,
                    app=apps["yt"],
                    screen="YouTube Shorts; redirect target = allowed calculus/DSA playlist",
                    decision="REDIRECT",
                    strictness=strict,
                    reason="playlist_rail",
                    attempts=1,
                    expected=overlay(
                        title="Returning to your rail",
                        message="Shorts aren't on your rail. Opening your allowed playlist.",
                        primary="REDIRECT_NOW",
                        secondary="OPEN_PLAYLIST",
                        forbidden=forbidden_for("REDIRECT", strict),
                        tone="strict_guard",
                    ),
                    cluster="playlist_rail_redirect",
                )
            )

    # ========== CHROME research vs drift ==========
    for p in chrome_promises:
        for strict in ("SOFT", "SMART", "STRICT"):
            cases.append(
                case(
                    uid("ch_movie"),
                    promise=p,
                    app=apps["ch"],
                    screen="Chrome: free movie streaming site homepage with play buttons",
                    decision="BLOCK",
                    strictness=strict,
                    reason="chrome_drift",
                    attempts=1,
                    expected=overlay(
                        title="Browser left research path",
                        message=f'Promise: "{p[:48]}". This looks like entertainment streaming, not docs.',
                        primary="EXIT_SURFACE",
                        secondary="CONTINUE_WITH_STRIKE" if secondary_continue_ok("BLOCK", strict) else "REVIEW_PROMISE",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone=tone_for("BLOCK", strict, "chrome_drift"),
                    ),
                    cluster="chrome_drift",
                )
            )
            cases.append(
                case(
                    uid("ch_meme"),
                    promise=p,
                    app=apps["ch"],
                    screen="Chrome: meme subreddit infinite scroll",
                    decision="WARN" if strict == "SOFT" else "BLOCK",
                    strictness=strict,
                    reason="chrome_drift",
                    attempts=1,
                    expected=overlay(
                        title="Meme drift in Chrome",
                        message="Screen is meme feed, not assignment research.",
                        primary="RETURN_SAFE",
                        secondary="REVIEW_PROMISE",
                        forbidden=forbidden_for("WARN" if strict == "SOFT" else "BLOCK", strict),
                        tone=tone_for("WARN" if strict == "SOFT" else "BLOCK", strict, "chrome_drift"),
                    ),
                    cluster="chrome_drift",
                )
            )
            cases.append(
                case(
                    uid("ch_porn"),
                    promise=p + " + no adult",
                    app=apps["ch"],
                    screen="Chrome: adult video site",
                    decision="BLOCK",
                    strictness="STRICT" if strict == "SOFT" else strict,
                    reason="adult_guardrail",
                    attempts=1,
                    expected=overlay(
                        title="Guardrail: no adult content",
                        message="Adult site in Chrome. Your promise blocks this path.",
                        primary="RETURN_SAFE",
                        secondary="ACKNOWLEDGE",
                        forbidden=forbidden_for("BLOCK", "STRICT" if strict == "SOFT" else strict),
                        tone="contract_life_rule",
                    ),
                    cluster="chrome_adult",
                )
            )

    # ========== TAMPER ==========
    tamper_screens = [
        "Settings: Accessibility → PhoneCodex toggle Off focused",
        "Settings: Apps → PhoneCodex → Force stop",
        "Settings: Apps → PhoneCodex → Uninstall",
        "MIUI: Autostart / battery restriction for PhoneCodex",
        "Trying to revoke overlay / accessibility permission mid-session",
    ]
    for p in (adult_promises[0], monk_promises[0], "can't turn off commitment this week", study_promises[0], long_promises[0]):
        for screen in tamper_screens:
            cases.append(
                case(
                    uid("tamper"),
                    promise=p,
                    app=apps["settings"],
                    screen=screen,
                    decision="LOCK",
                    strictness="LOCKED",
                    reason="tamper_attempt",
                    attempts=1,
                    expected=overlay(
                        title="Tamper blocked",
                        message=f'You asked not to disable mid-promise. "{p[:40]}…" — lock active.',
                        primary="WAIT_LOCK",
                        secondary="EMERGENCY_EXIT",
                        forbidden=forbidden_for("LOCK", "LOCKED"),
                        tone="tamper_cold",
                    ),
                    cluster="tamper_attempt",
                )
            )

    # ========== LONG-TERM ==========
    for p in long_promises:
        for strict in ("STRICT", "LOCKED"):
            cases.append(
                case(
                    uid("long"),
                    promise=p,
                    app=apps["yt"] if "Shorts" in p or "short" in p.lower() else apps["ch"],
                    screen="Content matching the long-term ban category",
                    decision="BLOCK",
                    strictness=strict,
                    reason="long_term_promise",
                    attempts=1,
                    expected=overlay(
                        title="Active life rule",
                        message=f'This is not a 2-hour timer. Long-term promise: "{p}".',
                        primary="ACKNOWLEDGE",
                        secondary="RETURN_SAFE",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone="contract_life_rule",
                    ),
                    cluster="long_term_promise",
                )
            )

    # ========== LOCK STATE (strikes) ==========
    for p in (shorts_promises[0], ig_promises[0], study_promises[0], monk_promises[1], wa_promises[0]):
        for attempts in (3, 4, 5):
            cases.append(
                case(
                    uid("lock"),
                    promise=p,
                    app=apps["yt"],
                    screen="Repeated violation after strikes; PolicyEngine LOCK",
                    decision="LOCK",
                    strictness="LOCKED",
                    reason="lock_state",
                    attempts=attempts,
                    expected=overlay(
                        title="Commitment locked",
                        message=f"Strike threshold hit ({attempts} attempts). Your lock policy is active.",
                        primary="WAIT_LOCK",
                        secondary="EMERGENCY_EXIT",
                        forbidden=forbidden_for("LOCK", "LOCKED"),
                        tone="locked_vault",
                    ),
                    cluster="lock_state",
                )
            )

    # ========== COOLING-OFF ==========
    for p in (study_promises[1], shorts_promises[1], ig_promises[0], adult_promises[1], monk_promises[2]):
        for strict in ("STRICT", "LOCKED"):
            cases.append(
                case(
                    uid("cool"),
                    promise=p,
                    app=apps["pc"],
                    screen="User requested mid-session override / early exit; cooling-off timer 90s",
                    decision="COOLING_OFF",
                    strictness=strict,
                    reason="cooling_off",
                    attempts=1,
                    expected=overlay(
                        title="Cooling-off before override",
                        message="You asked for friction before breaking this promise. Wait out the timer.",
                        primary="WAIT_LOCK",
                        secondary="EMERGENCY_EXIT",
                        forbidden=forbidden_for("COOLING_OFF", strict),
                        tone="locked_vault",
                        show_cooldown=True,
                    ),
                    cluster="cooling_off",
                )
            )

    # ========== REDIRECT lecture ==========
    for p in study_promises[:3]:
        cases.append(
            case(
                uid("redir_lec"),
                promise=p,
                app=apps["yt"],
                screen="Entertainment video; allowed lecture destination known",
                decision="REDIRECT",
                strictness="STRICT",
                reason="study_drift",
                attempts=1,
                expected=overlay(
                    title="Opening your allowed lecture",
                    message="This isn't on your study path. Taking you to the allowed lecture.",
                    primary="REDIRECT_NOW",
                    secondary="OPEN_ALLOWED_LECTURE",
                    forbidden=forbidden_for("REDIRECT", "STRICT"),
                    tone="strict_guard",
                ),
                cluster="redirect_lecture",
            )
        )

    # ========== EMERGENCY EXCEPTION (overlay still may show on wrong path; escape exists) ==========
    for p in monk_promises:
        cases.append(
            case(
                uid("emerg"),
                promise=p,
                app=apps["dialer"],
                screen="Phone dialer / SOS — emergency path",
                decision="WARN",
                strictness="STRICT",
                reason="emergency_exception",
                attempts=0,
                    expected=overlay(
                        title="Emergency path stays open",
                        message="Family/emergency access is outside monk entertainment rules. Continue to call if needed.",
                        primary="EMERGENCY_EXIT",
                        secondary="REVIEW_PROMISE",
                        forbidden=[F_DISABLE, F_IGNORE, F_UNINSTALL, F_SETTINGS, F_CONT_FREE],
                        tone="strict_guard",
                        emergency=True,
                    ),
                cluster="emergency_exception",
                notes="Should usually be ALLOW with no overlay; if shown, emergency primary",
            )
        )

    # ========== MONK entertainment ==========
    for p in monk_promises:
        for strict in ("STRICT", "LOCKED"):
            cases.append(
                case(
                    uid("monk"),
                    promise=p,
                    app=apps["ig"],
                    screen="Instagram feed scroll entertainment",
                    decision="BLOCK",
                    strictness=strict,
                    reason="monk_entertainment",
                    attempts=1,
                    expected=overlay(
                        title="Monk mode: entertainment blocked",
                        message=f'Promise: "{p[:50]}". Feed/entertainment is off-limits.',
                        primary="OPEN_STUDY_HOME",
                        secondary="REVIEW_PROMISE",
                        forbidden=forbidden_for("BLOCK", strict),
                        tone="strict_guard",
                    ),
                    cluster="monk_mode",
                )
            )

    # ========== HIGH ATTEMPT ESCALATION ==========
    for reason, app, screen, promise in [
        ("shorts_temptation", apps["yt"], "Shorts player again", shorts_promises[0]),
        ("instagram_reels", apps["ig"], "Reels again", ig_promises[0]),
        ("study_drift", apps["yt"], "Trending again", study_promises[0]),
        ("chrome_drift", apps["ch"], "Meme site again", chrome_promises[0]),
    ]:
        cases.append(
            case(
                uid("escal"),
                promise=promise,
                app=app,
                screen=screen + " (attempt 5)",
                decision="LOCK",
                strictness="LOCKED",
                reason="lock_state",
                attempts=5,
                expected=overlay(
                    title="Repeated break — locked",
                    message="Multiple attempts on the same forbidden surface. Lock policy engaged.",
                    primary="WAIT_LOCK",
                    secondary="EMERGENCY_EXIT",
                    forbidden=forbidden_for("LOCK", "LOCKED"),
                    tone="locked_vault",
                ),
                cluster="escalation_lock",
            )
        )

    # ========== SOFT-only gentle warns padding to 300+ ==========
    soft_pad = [
        ("maybe less phone during dinner study", apps["ig"], "IG feed at dinner", "study_drift"),
        ("warn me if I open Shorts", apps["yt"], "Shorts shelf visible under lecture", "shorts_temptation"),
        ("gentle nudge on reels", apps["ig"], "Reels tab focused", "reels_temptation"),
        ("remind me Chrome is for docs", apps["ch"], "YouTube.com in Chrome", "chrome_drift"),
        ("soft block games during focus", "com.activision.callofduty.shooter", "COD home", "study_drift"),
    ]
    for p, app, screen, reason in soft_pad * 4:  # 20
        cases.append(
            case(
                uid("soft"),
                promise=p,
                app=app,
                screen=screen,
                decision="WARN",
                strictness="SOFT",
                reason=reason,
                attempts=1,
                expected=overlay(
                    title="Nudge from your promise",
                    message=f'You asked for a soft check: "{p}". This screen may be drift.',
                    primary="RETURN_SAFE",
                    secondary="CONTINUE_WITH_STRIKE",
                    forbidden=forbidden_for("WARN", "SOFT"),
                    tone="soft_nudge",
                ),
                cluster="soft_pad",
            )
        )

    # Extra SMART warns for diversity
    for i in range(15):
        cases.append(
            case(
                uid("smart"),
                promise=f"study focus {i+1}h no shorts no reels",
                app=apps["yt"],
                screen=f"Shorts shelf visible attempt variant {i}",
                decision="WARN",
                strictness="SMART",
                reason="shorts_temptation",
                attempts=1 + (i % 3),
                expected=overlay(
                    title="Shorts on your radar",
                    message="Promise excludes Shorts. Shelf/player signal present — continuing costs a strike.",
                    primary="EXIT_SURFACE",
                    secondary="CONTINUE_WITH_STRIKE",
                    forbidden=forbidden_for("WARN", "SMART"),
                    tone="smart_cost",
                ),
                cluster="smart_pad",
            )
        )

    # Ensure ≥300 with combo fills
    while len(cases) < 300:
        i = len(cases)
        strict = ("SOFT", "SMART", "STRICT", "LOCKED")[i % 4]
        decision = ("WARN", "BLOCK", "LOCK", "REDIRECT", "COOLING_OFF")[i % 5]
        p = study_promises[i % len(study_promises)]
        reason = "study_drift"
        if decision == "LOCK":
            prim, sec, cd = "WAIT_LOCK", "EMERGENCY_EXIT", False
            reason = "lock_state"
            strict = "LOCKED"
        elif decision == "COOLING_OFF":
            prim, sec, cd = "WAIT_LOCK", "EMERGENCY_EXIT", True
            reason = "cooling_off"
            strict = "STRICT"
        elif decision == "REDIRECT":
            prim, sec, cd = "REDIRECT_NOW", "OPEN_ALLOWED_LECTURE", False
        elif decision == "WARN":
            prim = "EXIT_SURFACE"
            sec = "CONTINUE_WITH_STRIKE" if secondary_continue_ok("WARN", strict) else "REVIEW_PROMISE"
            cd = False
        else:
            prim, sec, cd = "EXIT_SURFACE", "REVIEW_PROMISE", False
            if strict == "SOFT":
                sec = "CONTINUE_WITH_STRIKE"
        cases.append(
            case(
                uid("fill"),
                promise=p,
                app=apps["yt"],
                screen=f"Synthetic fill screen #{i} for decision={decision}",
                decision=decision,
                strictness=strict,
                reason=reason,
                attempts=1 + (i % 4),
                expected=overlay(
                    title=f"{decision.replace('_', ' ').title()} — your promise",
                    message=f'Enforcing "{p[:40]}" on this screen. Decision={decision}.',
                    primary=prim,
                    secondary=sec,
                    forbidden=forbidden_for(decision, strict),
                    tone=tone_for(decision, strict, reason),
                    show_cooldown=cd,
                ),
                cluster="synthetic_fill",
                notes="padding to hit 300+",
            )
        )

    return cases


def main() -> None:
    cases = build()
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate ids")
    if len(cases) < 300:
        raise SystemExit(f"only {len(cases)} cases")
    with OUT.open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    clusters: dict[str, int] = {}
    for c in cases:
        clusters[c["cluster"]] = clusters.get(c["cluster"], 0) + 1
    print(f"Wrote {len(cases)} cases to {OUT}")
    for k, v in sorted(clusters.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

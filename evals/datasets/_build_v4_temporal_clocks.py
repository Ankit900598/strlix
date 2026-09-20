#!/usr/bin/env python3
"""Build evals/datasets/v4_temporal_clocks.jsonl — distinction-only temporal eval.

FIVE clocks that must never be mixed:
  session       → duration
  media_max     → quotas max_item_minutes (block items longer than N)
  media_min     → quotas min_item_minutes (allow/require items ≥ N)
  usage_quota   → quotas entertainment_minutes|social_minutes|shorts|reels
  lock          → lockPolicy.durationMinutes
  permanent     → duration indefinite / multi-year + guardrails
  ambiguous     → followUp required
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "v4_temporal_clocks.jsonl"

YT = ("com.google.android.youtube", "YouTube")
IG = ("com.instagram.android", "Instagram")
CH = ("com.android.chrome", "Chrome")
WA = ("com.whatsapp", "WhatsApp")


def app(pkg: str, label: str, scope: str) -> dict:
    return {"packageName": pkg, "appLabel": label, "scope": scope}


def content(ctype: str, desc: str, apps: list[str] | None = None) -> dict:
    row = {"type": ctype, "description": desc}
    if apps:
        row["apps"] = apps
    return row


def quota(metric: str, limit: int, period: str = "day") -> dict:
    return {"metric": metric, "limit": limit, "period": period}


def duration_fixed(value: float, unit: str) -> dict:
    return {"kind": "fixed", "value": value, "unit": unit, "until": None}


def duration_indefinite() -> dict:
    return {"kind": "indefinite", "value": None, "unit": None, "until": None}


def duration_none() -> dict:
    return {"kind": "none", "value": None, "unit": None, "until": None}


def strike(warn: int = 0, strikes: int = 0, reset: str = "session") -> dict:
    return {"warnBeforeLock": warn, "strikesBeforeLock": strikes, "resetPeriod": reset}


def lock(enabled: bool, minutes: int | None = None, scope: str = "commitment_pause") -> dict:
    return {"enabled": enabled, "durationMinutes": minutes, "scope": scope}


def tamper(prevent: bool = False, on: str = "NONE") -> dict:
    return {"preventDisable": prevent, "onTamper": on, "allowSettingsBrowse": True}


def emergency(etype: str, detail: str) -> dict:
    return {"type": etype, "detail": detail}


def policy(**kwargs) -> dict:
    return {
        "commitmentType": kwargs.get("commitment_type", "focus_session"),
        "duration": kwargs.get("duration") or duration_none(),
        "startCondition": kwargs.get("start", "immediate"),
        "strictnessLevel": kwargs.get("strictness", "STRICT"),
        "allowedApps": kwargs.get("allowed_apps") or [],
        "blockedApps": kwargs.get("blocked_apps") or [],
        "allowedContent": kwargs.get("allowed_content") or [],
        "blockedContent": kwargs.get("blocked_content") or [],
        "activeGuardrails": sorted(set(kwargs.get("guardrails") or [])),
        "quotas": kwargs.get("quotas") or [],
        "strikePolicy": kwargs.get("strike_policy") or strike(),
        "lockPolicy": kwargs.get("lock_policy") or lock(False),
        "emergencyExceptions": kwargs.get("emergency_exceptions") or [],
        "tamperPolicy": kwargs.get("tamper_policy") or tamper(),
        "followUpQuestionRequired": kwargs.get("follow_up", False),
        "followUpQuestion": kwargs.get("follow_up_q"),
        "rejectedUnsafeParts": kwargs.get("rejected") or [],
        "confidence": kwargs.get("confidence", 0.9),
    }


def add(cases, cid, promise, expected, cluster, clock, notes):
    cases.append(
        {
            "id": cid,
            "userPromise": promise,
            "expectedPolicy": expected,
            "cluster": cluster,
            "clockClass": clock,
            "notes": f"[clock:{clock}] {notes}",
        }
    )


def build() -> list[dict]:
    cases: list[dict] = []
    n = 0

    def uid(prefix: str) -> str:
        nonlocal n
        n += 1
        return f"tc_{prefix}_{n:03d}"

    # ----- SESSION duration -----
    for p, dur in [
        ("focus session for 1 hour no shorts", duration_fixed(1, "hours")),
        ("study block 90 minutes", duration_fixed(90, "minutes")),
        ("2 ghante padhai session", duration_fixed(2, "hours")),
        ("pomodoro 25m deep work", duration_fixed(25, "minutes")),
        ("next 3 hours only study apps", duration_fixed(3, "hours")),
        ("oru mani neram focus", duration_fixed(1, "hours")),
        ("ஒரு மணி நேரம் படிப்பு", duration_fixed(1, "hours")),
        ("lock me into studying 45 min", duration_fixed(45, "minutes")),
    ]:
        add(
            cases,
            uid("sess"),
            p,
            policy(
                duration=dur,
                blocked_content=[content("short_form_video", "shorts")] if "short" in p else [],
                guardrails=["no_short_form_video"] if "short" in p else [],
            ),
            "session_duration",
            "session",
            "commitment/session length only",
        )

    # ----- MEDIA MAX (block longer than N) — NOT entertainment budget -----
    for p, mins in [
        ("block videos longer than 40 minutes", 40),
        ("block any youtube video longer than 20 min", 20),
        ("videos > 40 min not allowed", 40),
        ("no chrome videos over 30 minutes", 30),
        ("har video 45 min se zyada mat chalane dena", 45),
        ("block yt/chrome videos longer than 40 min", 40),
        ("max length 25 minutes per video", 25),
        ("don't let me watch anything over an hour long", 60),
        ("lecture videos max 50 min each — not a time budget", 50),
        ("each clip under 15 minutes only", 15),
    ]:
        add(
            cases,
            uid("mmax"),
            p,
            policy(
                commitment_type="focus_session",
                quotas=[quota("max_item_minutes", mins, "item")],
                allowed_content=[content("long_form_video", f"max {mins}m")],
                blocked_content=[content("long_form_video", "over max length")],
            ),
            "media_max",
            "media_max",
            "per-item max length → max_item_minutes NOT entertainment_minutes",
        )

    # ----- MEDIA MIN (allow/require longer than N / block shorter) -----
    for p, mins in [
        ("allow YouTube and Chrome videos greater than 40 min only", 40),
        ("only long lectures over 40 minutes", 40),
        ("block videos shorter than 20 minutes", 20),
        ("allow videos longer than 30 min on youtube", 30),
        ("sirf 40 minute se lambe lectures chahiye", 40),
        ("short clips under 10 min banned; longer ok", 10),
    ]:
        add(
            cases,
            uid("mmin"),
            p,
            policy(
                commitment_type="focus_session",
                quotas=[quota("min_item_minutes", mins, "item")],
                allowed_content=[content("long_form_video", f"at least {mins}m")],
                blocked_content=[content("long_form_video", "too short")]
                if "short" in p.lower() or "under" in p.lower() or "shorter" in p.lower()
                else [content("short_form_video", "short clips")],
            ),
            "media_min",
            "media_min",
            "per-item min length → min_item_minutes",
        )

    # ----- USAGE QUOTA (total minutes / counts) -----
    for p, exp in [
        (
            "only 40 minutes entertainment today",
            policy(
                commitment_type="quota_entertainment",
                quotas=[quota("entertainment_minutes", 40, "day")],
            ),
        ),
        (
            "entertainment budget 25 minutes this session",
            policy(
                commitment_type="quota_entertainment",
                quotas=[quota("entertainment_minutes", 25, "session")],
            ),
        ),
        (
            "social media 45 min daily max",
            policy(
                commitment_type="quota_entertainment",
                quotas=[quota("social_minutes", 45, "day")],
            ),
        ),
        (
            "aj total 30 min youtube entertainment not lectures",
            policy(
                commitment_type="quota_entertainment",
                quotas=[quota("entertainment_minutes", 30, "day")],
                allowed_content=[content("entertainment", "yt entertainment")],
            ),
        ),
        (
            "allow 40 Shorts today then stop",
            policy(
                commitment_type="quota_entertainment",
                duration=duration_fixed(1, "days"),
                quotas=[quota("shorts", 40, "day")],
                allowed_content=[content("short_form_video", "shorts under quota")],
            ),
        ),
        (
            "20 shorts after study as reward",
            policy(
                commitment_type="quota_entertainment",
                quotas=[quota("shorts", 20, "session")],
            ),
        ),
        (
            "reels 15 per day then stop",
            policy(commitment_type="quota_entertainment", quotas=[quota("reels", 15, "day")]),
        ),
        (
            "40 shorts but no adult content",
            policy(
                commitment_type="quota_entertainment",
                quotas=[quota("shorts", 40, "day")],
                guardrails=["no_adult_content"],
                blocked_content=[content("adult_sexual", "adult")],
            ),
        ),
    ]:
        add(cases, uid("usage"), p, exp, "usage_quota", "usage_quota", "total usage budget/count")

    # ----- LOCK duration (not session) -----
    for p, mins, warns, strikes in [
        ("warn twice then lock for 20 minutes", 20, 2, 2),
        ("after 3 tries lock me 15 min", 15, 1, 3),
        ("lock instagram 10 min if i open reels thrice", 10, 0, 3),
        ("3 strikes then 1 hour youtube lock", 60, 1, 3),
        ("agar cheat kiya to 30 min overlay lock", 30, 0, 1),
    ]:
        add(
            cases,
            uid("lock"),
            p,
            policy(
                strike_policy=strike(warns, strikes),
                lock_policy=lock(True, mins, "app" if "instagram" in p or "youtube" in p else "commitment_pause"),
                duration=duration_none(),
                blocked_content=[content("short_form_video", "reels")] if "reels" in p else [],
                tamper_policy=tamper(True, "LOCK") if "cheat" in p else tamper(),
                strictness="LOCKED" if "cheat" in p else "STRICT",
            ),
            "lock_duration",
            "lock",
            "lockPolicy.durationMinutes — NOT session duration",
        )

    # ----- PERMANENT -----
    for p, guards, dur in [
        ("no porn for 1 year", ["no_adult_content"], duration_fixed(1, "years")),
        ("1 saal adult content band", ["no_adult_content"], duration_fixed(1, "years")),
        ("no dating apps forever", ["no_dating_apps"], duration_indefinite()),
        ("permanent no shorts on this phone", ["no_short_form_video"], duration_indefinite()),
        ("no gambling apps for 365 days", ["no_gambling"], duration_fixed(365, "days")),
    ]:
        add(
            cases,
            uid("perm"),
            p,
            policy(
                commitment_type="permanent_guardrail",
                duration=dur,
                guardrails=guards,
                blocked_content=[content("adult_sexual", "adult")]
                if "adult" in guards[0] or "porn" in p
                else [],
            ),
            "permanent_guardrail",
            "permanent",
            "long-term guardrail duration",
        )

    # ----- AMBIGUOUS number+app -----
    for p, q in [
        ("40 min youtube", "Do you mean a 40-minute focus session, 40 minutes of YouTube per day, or max video length 40 minutes?"),
        ("youtube 1 hour", "Is 1 hour the study session, a daily YouTube quota, or max video length?"),
        ("half hour insta", "Is half hour a session, daily Instagram quota, or something else?"),
        ("tiktok 15 min", "Session, daily quota, or max clip length?"),
        ("chrome 25 minutes", "Focus session, Chrome time budget, or max page/video length?"),
        ("bas 1 hr phone", "Which apps count, and is it total screen time or a study session?"),
        ("oru mani neram youtube", "Session, daily quota, or max video length? (ஒரு மணி நேரம்)"),
        ("40 min yt/chrome", "Session length, total entertainment budget, or max video length?"),
    ]:
        add(
            cases,
            uid("amb"),
            p,
            policy(follow_up=True, follow_up_q=q, confidence=0.32),
            "duration_ambiguous",
            "ambiguous",
            "MUST ask — do not guess clock",
        )

    # ----- MIXED: session + media max (the product failure case) -----
    for p, sess, media in [
        ("block videos longer than 20 minutes during a 1 hour study session", duration_fixed(1, "hours"), 20),
        ("for next 1 hour block youtube videos greater than 20 min", duration_fixed(1, "hours"), 20),
        ("study 3h; block any video longer than 40 min; no shorts", duration_fixed(3, "hours"), 40),
        ("1 hour focus AND block chrome videos over 30 minutes", duration_fixed(1, "hours"), 30),
        ("2 ghante session; 40 min se lambe videos block", duration_fixed(2, "hours"), 40),
    ]:
        add(
            cases,
            uid("mix_sm"),
            p,
            policy(
                duration=sess,
                quotas=[quota("max_item_minutes", media, "item")],
                allowed_content=[content("long_form_video", f"max {media}m")],
                blocked_content=[content("long_form_video", "over max")]
                + ([content("short_form_video", "shorts")] if "short" in p else []),
                guardrails=["no_short_form_video"] if "short" in p else [],
            ),
            "session_and_media",
            "session_and_media",
            "BOTH session duration AND max_item_minutes — never collapse media into entertainment_minutes",
        )

    # ----- MIXED: session + usage budget -----
    for p, sess, budget in [
        ("1h focus AND entertainment budget 25 minutes total", duration_fixed(1, "hours"), 25),
        ("study 2 hours with only 15 min social total", duration_fixed(2, "hours"), 15),
    ]:
        metric = "social_minutes" if "social" in p else "entertainment_minutes"
        add(
            cases,
            uid("mix_su"),
            p,
            policy(
                commitment_type="quota_entertainment",
                duration=sess,
                quotas=[quota(metric, budget, "session")],
            ),
            "session_and_usage",
            "session_and_usage",
            "session + usage budget (entertainment_minutes) — not max_item",
        )

    # ----- CONTRAST PAIRS (same number, different clock) -----
    # 40 as session vs media max vs usage
    add(
        cases,
        uid("pair"),
        "for 40 minutes study only",
        policy(duration=duration_fixed(40, "minutes")),
        "contrast_pair",
        "session",
        "PAIR A: 40 = session",
    )
    add(
        cases,
        uid("pair"),
        "block videos longer than 40 minutes",
        policy(
            quotas=[quota("max_item_minutes", 40, "item")],
            blocked_content=[content("long_form_video", "over 40m")],
        ),
        "contrast_pair",
        "media_max",
        "PAIR B: 40 = media max",
    )
    add(
        cases,
        uid("pair"),
        "only 40 minutes entertainment today",
        policy(
            commitment_type="quota_entertainment",
            quotas=[quota("entertainment_minutes", 40, "day")],
        ),
        "contrast_pair",
        "usage_quota",
        "PAIR C: 40 = usage budget",
    )
    add(
        cases,
        uid("pair"),
        "lock me for 40 minutes after 3 tries",
        policy(strike_policy=strike(0, 3), lock_policy=lock(True, 40)),
        "contrast_pair",
        "lock",
        "PAIR D: 40 = lock timer",
    )

    # ----- Surfaces (non-temporal but required by brief) -----
    for p, exp, clock in [
        (
            "YouTube lectures allowed, Shorts banned",
            policy(
                allowed_content=[content("long_form_video", "lectures", [YT[0]])],
                blocked_content=[content("short_form_video", "shorts", [YT[0]])],
                guardrails=["no_short_form_video"],
            ),
            "surface",
        ),
        (
            "Instagram DMs allowed, Reels blocked",
            policy(
                allowed_content=[content("social_dm", "dms", [IG[0]])],
                blocked_content=[content("short_form_video", "reels", [IG[0]])],
            ),
            "surface",
        ),
        (
            "ig pe msg ok reels bilkul nahi",
            policy(
                allowed_content=[content("social_dm", "messages", [IG[0]])],
                blocked_content=[content("short_form_video", "reels", [IG[0]])],
            ),
            "surface",
        ),
        (
            "allow 40 Shorts until count reached then block",
            policy(
                commitment_type="quota_entertainment",
                quotas=[quota("shorts", 40, "day")],
            ),
            "shorts_quota",
        ),
        (
            "Neso Academy OS playlist only for 3 hours",
            policy(
                duration=duration_fixed(3, "hours"),
                allowed_apps=[app(*YT, "neso_academy_playlist_only")],
                blocked_content=[content("short_form_video", "shorts")],
            ),
            "session",
        ),
        (
            "monk mode except calls and messages",
            policy(
                commitment_type="monk_mode",
                blocked_content=[content("entertainment", "fun")],
                allowed_content=[content("social_dm", "messages"), content("calls", "calls")],
                emergency_exceptions=[emergency("family_calls", "calls")],
            ),
            "surface",
        ),
    ]:
        add(cases, uid("surf"), p, exp, "app_surface", clock, "surface/control fixture")

    # Typo-heavy / speech-like
    for p, exp, clock, note in [
        (
            "blok videos longr than 40 mins plz",
            policy(
                quotas=[quota("max_item_minutes", 40, "item")],
                blocked_content=[content("long_form_video", "over 40m")],
            ),
            "media_max",
            "typo media max",
        ),
        (
            "entertaiment only 40 min 2day",
            policy(
                commitment_type="quota_entertainment",
                quotas=[quota("entertainment_minutes", 40, "day")],
            ),
            "usage_quota",
            "typo usage",
        ),
        (
            "focuss 1hr noo shorts",
            policy(
                duration=duration_fixed(1, "hours"),
                blocked_content=[content("short_form_video", "shorts")],
                guardrails=["no_short_form_video"],
            ),
            "session",
            "typo session",
        ),
    ]:
        add(cases, uid("typo"), p, exp, "messy_typo", clock, note)

    # Extra multilingual + contrast cases
    for p, mins in [
        ("40 min se zyada ka koi bhi video mat chalana", 40),
        ("youtube pe 20 minute se lambe videos block during study later", 20),
        ("chrome me movie > 1 hour band", 60),
        ("netflix episode over 55 minutes block", 55),
    ]:
        add(
            cases,
            uid("mmax2"),
            p,
            policy(
                quotas=[quota("max_item_minutes", mins, "item")],
                blocked_content=[content("long_form_video", "over max")],
            ),
            "media_max",
            "media_max",
            "extra media max",
        )

    for p, q in [
        ("yt 40m", "Session, daily quota, or max video length?"),
        ("insta 30 min", "Session, daily Instagram quota, or something else?"),
        ("phone 40 minutes", "Total phone time, study session, or app quota?"),
        ("netflix 40 min", "Episode max length, daily Netflix budget, or session?"),
    ]:
        add(
            cases,
            uid("amb2"),
            p,
            policy(follow_up=True, follow_up_q=q, confidence=0.3),
            "duration_ambiguous",
            "ambiguous",
            "extra ambiguous",
        )

    for p, dur in [
        ("boards prep weekdays 4 hour blocks", duration_fixed(4, "hours")),
        ("raat 11 baje tak focus", duration_fixed(1, "hours")),  # weak — better until; keep session-ish
        ("deep work ninety mins no ig", duration_fixed(90, "minutes")),
    ]:
        blocked = [content("short_form_video", "reels")] if "ig" in p else []
        add(
            cases,
            uid("sess2"),
            p if "11 baje" not in p else "focus session 2 hours till dinner no clock given",
            policy(
                duration=duration_fixed(2, "hours") if "11 baje" in p else dur,
                blocked_content=blocked,
                blocked_apps=[app(*IG, "blocked")] if "ig" in p else [],
            ),
            "session_duration",
            "session",
            "extra session",
        )

    # Triple distinction: same 20
    add(
        cases,
        uid("tri"),
        "for 20 minutes study",
        policy(duration=duration_fixed(20, "minutes")),
        "contrast_pair",
        "session",
        "TRI A session 20",
    )
    add(
        cases,
        uid("tri"),
        "block videos longer than 20 minutes",
        policy(
            quotas=[quota("max_item_minutes", 20, "item")],
            blocked_content=[content("long_form_video", "over 20m")],
        ),
        "contrast_pair",
        "media_max",
        "TRI B media max 20",
    )
    add(
        cases,
        uid("tri"),
        "only 20 minutes entertainment today",
        policy(
            commitment_type="quota_entertainment",
            quotas=[quota("entertainment_minutes", 20, "day")],
        ),
        "contrast_pair",
        "usage_quota",
        "TRI C usage 20",
    )
    add(
        cases,
        uid("tri"),
        "lock for 20 minutes after warnings",
        policy(strike_policy=strike(2, 2), lock_policy=lock(True, 20)),
        "contrast_pair",
        "lock",
        "TRI D lock 20",
    )

    # Product failure replay
    add(
        cases,
        uid("fail"),
        "for next 1 hour allow chrome/youtube research but block videos longer than 40 minutes",
        policy(
            duration=duration_fixed(1, "hours"),
            quotas=[quota("max_item_minutes", 40, "item")],
            allowed_apps=[app(*CH, "research"), app(*YT, "research")],
            allowed_content=[content("study", "research"), content("long_form_video", "max 40m")],
            blocked_content=[content("long_form_video", "over 40m")],
        ),
        "session_and_media",
        "session_and_media",
        "PRODUCT FAILURE REPLAY: session + media max must not become entertainment budget",
    )
    add(
        cases,
        uid("fail"),
        "block youtube videos greater than 20 min for the next 1 hour",
        policy(
            duration=duration_fixed(1, "hours"),
            quotas=[quota("max_item_minutes", 20, "item")],
            blocked_content=[content("long_form_video", "over 20m", [YT[0]])],
        ),
        "session_and_media",
        "session_and_media",
        "PRODUCT FAILURE REPLAY user wording",
    )

    return cases


def main() -> None:
    cases = build()
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate ids")
    if len(cases) < 80:
        raise SystemExit(f"too few cases: {len(cases)}")
    with OUT.open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    from collections import Counter

    print(f"Wrote {len(cases)} cases to {OUT}")
    print("clockClass:", dict(Counter(c["clockClass"] for c in cases)))
    print("cluster:", dict(Counter(c["cluster"] for c in cases)))


if __name__ == "__main__":
    main()

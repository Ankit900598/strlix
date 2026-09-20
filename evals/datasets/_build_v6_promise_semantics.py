#!/usr/bin/env python3
"""Build v6 Promise Semantics gold set (Semantics v1).

Output: evals/datasets/v6_promise_semantics.jsonl (>=100 human-curated cases)
No synthetic_fill junk — every case encodes a real interpretation distinction.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "v6_promise_semantics.jsonl"

YT = ("com.google.android.youtube", "YouTube")
IG = ("com.instagram.android", "Instagram")
FB = ("com.facebook.katana", "Facebook")
TT = ("com.zhiliaoapp.musically", "TikTok")
CH = ("com.android.chrome", "Chrome")
NP = ("org.schabi.newpipe", "NewPipe")
PS = ("com.android.vending", "Play Store")
WA = ("com.whatsapp", "WhatsApp")

SEM_QUOTA = (
    "[semantics:v1][scope:all_short_form][quota:allow_first_n][time:calendar_day]"
)
SEM_YT_ONLY = "[semantics:v1][scope:youtube_shorts_only][quota:allow_first_n]"
SEM_ALL = "[semantics:v1][scope:all_short_form]"


def app(pkg: str, label: str, scope: str) -> dict:
    return {"packageName": pkg, "appLabel": label, "scope": scope}


def content(ctype: str, desc: str, apps: list[str] | None = None, **extra: object) -> dict:
    row: dict = {"type": ctype, "description": desc}
    if apps:
        row["apps"] = apps
    row.update(extra)
    return row


def quota(metric: str, limit: int, period: str = "day") -> dict:
    return {"metric": metric, "limit": limit, "period": period}


def duration_fixed(value: float, unit: str) -> dict:
    return {"kind": "fixed", "value": value, "unit": unit, "until": None}


def duration_indefinite() -> dict:
    return {"kind": "indefinite", "value": None, "unit": None, "until": None}


def duration_none() -> dict:
    return {"kind": "none", "value": None, "unit": None, "until": None}


def duration_until(until: str) -> dict:
    return {"kind": "until_clock", "value": None, "unit": None, "until": until}


def strike(warn: int = 0, strikes: int = 0, reset: str = "session") -> dict:
    return {"warnBeforeLock": warn, "strikesBeforeLock": strikes, "resetPeriod": reset}


def lock(enabled: bool, minutes: int | None = None, scope: str = "commitment_pause") -> dict:
    return {"enabled": enabled, "durationMinutes": minutes, "scope": scope}


def tamper(prevent: bool = False, on: str = "NONE", browse: bool = True) -> dict:
    return {"preventDisable": prevent, "onTamper": on, "allowSettingsBrowse": browse}


def dims(
    *,
    language: str = "en",
    typo_level: str = "none",
    promise_type: str,
    app_surface: str = "none",
    time_role: str = "none",
    safety_risk: str = "none",
    expected_followup: bool = False,
    expected_guardrails: list[str] | None = None,
) -> dict:
    return {
        "language": language,
        "typo_level": typo_level,
        "promise_type": promise_type,
        "app_surface": app_surface,
        "time_role": time_role,
        "safety_risk": safety_risk,
        "expected_followup": expected_followup,
        "expected_guardrails": expected_guardrails or [],
    }


def provenance(now: str, note: str = "") -> dict:
    return {
        "sourceModel": "hand",
        "sourceModelFamily": "human_curated",
        "promptVersion": "semantics_v1_gold",
        "generatedAt": now,
        "reviewStatus": "accepted",
        "reviewedBy": "ai_lab",
        "reviewedAt": now,
        "parentSeedId": None,
        "generationBatch": "v6_promise_semantics",
        "notes": note or "Promise Semantics v1 curated gold",
    }


def policy(
    *,
    commitment_type: str = "focus_session",
    duration: dict | None = None,
    strictness: str = "STRICT",
    allowed_apps: list | None = None,
    blocked_apps: list | None = None,
    allowed_content: list | None = None,
    blocked_content: list | None = None,
    guardrails: list | None = None,
    quotas: list | None = None,
    strike_policy: dict | None = None,
    lock_policy: dict | None = None,
    emergency: list | None = None,
    tamper_policy: dict | None = None,
    follow_up: bool = False,
    follow_up_q: str | None = None,
    rejected: list | None = None,
    confidence: float = 0.9,
    confirm: str | None = None,
    interp: list[str] | None = None,
) -> dict:
    row = {
        "commitmentType": commitment_type,
        "duration": duration if duration is not None else duration_fixed(1, "hours"),
        "startCondition": "immediate",
        "strictnessLevel": strictness,
        "allowedApps": allowed_apps or [],
        "blockedApps": blocked_apps or [],
        "allowedContent": allowed_content or [],
        "blockedContent": blocked_content or [],
        "activeGuardrails": guardrails or [],
        "quotas": quotas or [],
        "strikePolicy": strike_policy or strike(),
        "lockPolicy": lock_policy or lock(False),
        "emergencyExceptions": emergency or [],
        "tamperPolicy": tamper_policy or tamper(False),
        "followUpQuestionRequired": follow_up,
        "followUpQuestion": follow_up_q,
        "rejectedUnsafeParts": rejected or [],
        "confidence": confidence,
    }
    if confirm is not None:
        row["userFacingConfirmation"] = confirm
    if interp is not None:
        row["interpretationNotes"] = interp
    return row


def case(
    cid: str,
    promise: str,
    pol: dict,
    *,
    cluster: str,
    clock: str,
    dimensions: dict,
    notes: str,
    now: str,
) -> dict:
    return {
        "id": cid,
        "userPromise": promise,
        "expectedPolicy": pol,
        "cluster": cluster,
        "clockClass": clock,
        "notes": notes,
        "dimensions": dimensions,
        "provenance": provenance(now),
    }


def _shorts_quota_policy(
    n: int,
    *,
    duration: dict | None = None,
    adult: bool = True,
    long_edu: bool = True,
    yt_only: bool = False,
    confirm: str | None = None,
    extra_interp: list[str] | None = None,
) -> dict:
    blocked = []
    guardrails = []
    yt_apps = [YT[0]] if yt_only else None
    if adult:
        blocked.append(
            content("adult_sexual", "adult sexual shorts", apps=yt_apps)
        )
        guardrails.append("no_adult_content")
    allowed = []
    if long_edu:
        allowed.append(
            content("long_form_video", "educational youtube", apps=[YT[0]])
        )
    # Scope marker for YouTube-only quotas (metric stays category "shorts")
    if yt_only:
        allowed.append(
            content("short_form_video", "youtube shorts quota window", apps=[YT[0]])
        )
    interp = []
    if yt_only:
        interp.append("Scoped shorts quota to YouTube Shorts only as user named YouTube.")
    else:
        interp.append("Interpreted shorts as all short-form video surfaces.")
    if extra_interp:
        interp.extend(extra_interp)
    if confirm is None:
        scope = "YouTube Shorts" if yt_only else "short-form video"
        confirm = (
            f"First {n} {scope} today; "
            + ("adult always blocked; " if adult else "")
            + ("long educational YouTube allowed." if long_edu else "then block short-form.")
        )
    return policy(
        commitment_type="quota_entertainment",
        duration=duration if duration is not None else duration_none(),
        quotas=[quota("shorts", n, "day")],
        guardrails=guardrails,
        blocked_content=blocked,
        allowed_content=allowed,
        confirm=confirm,
        interp=interp,
    )


def build() -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []

    # ------------------------------------------------------------------ #
    # 1. short_form_daily_quota (LIVE + variants)
    # ------------------------------------------------------------------ #
    live = (
        "I want to watch at most 10 shorts today, but never adult/sexual shorts. "
        "After 10 shorts, block shorts for the rest of the day. "
        "Long educational YouTube should still be allowed."
    )
    rows.append(
        case(
            "v6_quota_live_001",
            live,
            _shorts_quota_policy(
                10,
                confirm=(
                    "First 10 short-form today; adult always blocked; "
                    "long educational YouTube allowed."
                ),
            ),
            cluster="short_form_daily_quota",
            clock="usage_quota",
            dimensions=dims(
                promise_type="quota_entertainment",
                app_surface="multi",
                time_role="usage_quota",
                safety_risk="adult",
                expected_guardrails=["no_adult_content"],
            ),
            notes=f"{SEM_QUOTA} LIVE failure family; NOT 60min session; NOT hard-ban alone",
            now=now,
        )
    )
    rows.append(
        case(
            "v6_quota_live_001b",
            live,
            _shorts_quota_policy(10, duration=duration_fixed(1, "days")),
            cluster="short_form_daily_quota",
            clock="usage_quota",
            dimensions=dims(
                promise_type="quota_entertainment",
                app_surface="multi",
                time_role="usage_quota",
                safety_risk="adult",
                expected_guardrails=["no_adult_content"],
            ),
            notes=f"{SEM_QUOTA} alt gold: duration fixed 1 day also OK (not 60min)",
            now=now,
        )
    )

    quota_variants = [
        (
            "v6_quota_en_002",
            "at most 10 shorts today, never adult, after 10 block, long educational YouTube allowed",
            10,
            "en",
            "none",
        ),
        (
            "v6_quota_en_003",
            "max 15 shorts for today then stop; no nsfw; lectures on YT still ok",
            15,
            "en",
            "none",
        ),
        (
            "v6_quota_en_004",
            "I can do 5 short videos today only. Block porn always. Long study videos fine.",
            5,
            "en",
            "none",
        ),
        (
            "v6_quota_en_005",
            "20 shorts max today. Adult content never. After quota block shorts rest of day.",
            20,
            "en",
            "none",
        ),
        (
            "v6_quota_hi_006",
            "aaj sirf 10 shorts, adult nahi, uske baad shorts band, lambi padhai YT chalegi",
            10,
            "hinglish",
            "none",
        ),
        (
            "v6_quota_hi_007",
            "aaj maximum 8 shorts dekh sakta hun, adult content kabhi nahi, lecture videos allow",
            8,
            "hinglish",
            "none",
        ),
        (
            "v6_quota_hi_008",
            "sirf 12 short videos aaj ke liye, baaki din block; porn mat dikhao; education YT ok",
            12,
            "hi",
            "light",
        ),
        (
            "v6_quota_typo_009",
            "at mst 10 shortss todya never adult aftre 10 blokk long educatinal yt alowed",
            10,
            "en",
            "heavy",
        ),
        (
            "v6_quota_typo_010",
            "maxx 7 shorts 2day, noo porn, longg study youtube stil okk",
            7,
            "en",
            "heavy",
        ),
        (
            "v6_quota_ta_011",
            "indru 10 shorts mattum, adult venda, apuram block, nalla study youtube ok",
            10,
            "ta",
            "none",
        ),
        (
            "v6_quota_ta_012",
            "iniku maximum 6 short videos, adult content illa, long educational YT allow",
            6,
            "ta",
            "light",
        ),
        (
            "v6_quota_en_013",
            "Allow the first 10 shorts today then hard-stop short-form; keep adult blocked always; long educational YouTube OK",
            10,
            "en",
            "none",
        ),
        (
            "v6_quota_en_014",
            "Daily cap: 10 short videos. Never adult/sexual. Long educational YouTube remains allowed after the cap.",
            10,
            "en",
            "none",
        ),
        (
            "v6_quota_hi_015",
            "aaj 10 se zyada shorts mat dena, adult bilkul nahi, padhai wali lambi video chalne do",
            10,
            "hinglish",
            "none",
        ),
    ]
    for cid, promise, n, lang, typo in quota_variants:
        rows.append(
            case(
                cid,
                promise,
                _shorts_quota_policy(n),
                cluster="short_form_daily_quota",
                clock="usage_quota",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="quota_entertainment",
                    app_surface="multi",
                    time_role="usage_quota",
                    safety_risk="adult",
                    expected_guardrails=["no_adult_content"],
                ),
                notes=f"{SEM_QUOTA} n={n}; quota not session; no hard ban alone",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 2. youtube_shorts_only vs all_short_form scope
    # ------------------------------------------------------------------ #
    scope_cases = [
        (
            "v6_scope_yt_001",
            "YouTube Shorts only: at most 10 today, then block YouTube Shorts",
            10,
            True,
            "en",
            "none",
            f"{SEM_YT_ONLY} named YouTube → do not expand to IG/TikTok",
        ),
        (
            "v6_scope_yt_002",
            "only youtube shorts quota 15 for today, other apps free",
            15,
            True,
            "en",
            "none",
            f"{SEM_YT_ONLY} explicit youtube-only",
        ),
        (
            "v6_scope_yt_003",
            "sirf YouTube Shorts — aaj 8 max, baaki apps chill",
            8,
            True,
            "hinglish",
            "none",
            f"{SEM_YT_ONLY} hinglish youtube-only",
        ),
        (
            "v6_scope_all_004",
            "no more than 10 shorts today across any app",
            10,
            False,
            "en",
            "none",
            f"{SEM_QUOTA} across any app → all_short_form",
        ),
        (
            "v6_scope_all_005",
            "shorts meaning reels tiktok everything — 10 max today",
            10,
            False,
            "en",
            "none",
            f"{SEM_QUOTA} explicit all surfaces",
        ),
        (
            "v6_scope_all_006",
            "bare word shorts: 12 today then stop",
            12,
            False,
            "en",
            "none",
            f"{SEM_QUOTA} bare shorts defaults to all_short_form",
        ),
        (
            "v6_scope_all_007",
            "aaj 10 shorts limit — reels aur tiktok bhi count",
            10,
            False,
            "hinglish",
            "none",
            f"{SEM_QUOTA} hinglish all surfaces",
        ),
        (
            "v6_scope_yt_008",
            "YT shorts only 5 today; instagram reels allowed unlimited",
            5,
            True,
            "en",
            "none",
            f"{SEM_YT_ONLY} contrast: IG free",
        ),
        (
            "v6_scope_all_009",
            "shortss todya 10 max anywhre on phone",
            10,
            False,
            "en",
            "heavy",
            f"{SEM_QUOTA} typo bare shorts → all",
        ),
        (
            "v6_scope_yt_010",
            "indru YouTube Shorts mattum 10, Instagram free",
            10,
            True,
            "ta",
            "none",
            f"{SEM_YT_ONLY} tamil romanized youtube-only",
        ),
    ]
    for cid, promise, n, yt_only, lang, typo, notes in scope_cases:
        rows.append(
            case(
                cid,
                promise,
                _shorts_quota_policy(n, yt_only=yt_only, adult=False, long_edu=False),
                cluster="youtube_shorts_only_vs_all_short_form",
                clock="usage_quota",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="quota_entertainment",
                    app_surface="youtube" if yt_only else "multi",
                    time_role="usage_quota",
                ),
                notes=notes,
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 3. instagram_dm_vs_reels
    # ------------------------------------------------------------------ #
    ig_cases = [
        (
            "v6_ig_001",
            "Allow Instagram messages, but block Reels during work for 2 hours",
            2,
            "hours",
            "en",
            "none",
        ),
        (
            "v6_ig_002",
            "IG DMs ok, Reels and Explore off for 90 minutes",
            90,
            "minutes",
            "en",
            "none",
        ),
        (
            "v6_ig_003",
            "instagram pe chat chalega, reels band — 2 ghante",
            2,
            "hours",
            "hinglish",
            "none",
        ),
        (
            "v6_ig_004",
            "work focus: keep Instagram DM, kill Reels for 3h",
            3,
            "hours",
            "en",
            "none",
        ),
        (
            "v6_ig_005",
            "ig dmss okk reelss blokk 1 hr",
            1,
            "hours",
            "en",
            "heavy",
        ),
        (
            "v6_ig_006",
            "Instagram messages allowed, stories and reels blocked for 45 min",
            45,
            "minutes",
            "en",
            "none",
        ),
        (
            "v6_ig_007",
            "sirf college team DMs on IG, reels mat kholna 2 hours",
            2,
            "hours",
            "hinglish",
            "none",
        ),
        (
            "v6_ig_008",
            "instagram chat allow, reels venda — 2 hours study",
            2,
            "hours",
            "ta",
            "none",
        ),
    ]
    for cid, promise, val, unit, lang, typo in ig_cases:
        blocked = [content("short_form_video", "reels", apps=[IG[0]])]
        if "stories" in promise.lower() or "Explore" in promise:
            blocked.append(content("social_feed", "stories explore", apps=[IG[0]]))
        scope = "messages"
        if "college" in promise.lower():
            scope = "dm_college_team_only"
        rows.append(
            case(
                cid,
                promise,
                policy(
                    duration=duration_fixed(val, unit),
                    allowed_apps=[app(*IG, scope)],
                    blocked_content=blocked,
                    guardrails=["no_short_form_video"],
                    confirm="Instagram DMs allowed; Reels blocked for this session.",
                    interp=["Surface split: social_dm allowed, short_form Reels blocked."],
                ),
                cluster="instagram_dm_vs_reels",
                clock="session",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="focus_session",
                    app_surface="instagram",
                    time_role="session",
                    expected_guardrails=["no_short_form_video"],
                ),
                notes="[semantics:v1][surface:ig_dm_vs_reels] not whole-app ban",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 4. facebook_reels
    # ------------------------------------------------------------------ #
    fb_cases = [
        (
            "v6_fb_001",
            "Block Facebook Reels for 2 hours but keep Messenger/chat usable",
            2,
            "hours",
            "en",
            "none",
        ),
        (
            "v6_fb_002",
            "FB reels band, normal facebook browsing ok for 90 min",
            90,
            "minutes",
            "hinglish",
            "none",
        ),
        (
            "v6_fb_003",
            "no facebook reels during study — 3h focus",
            3,
            "hours",
            "en",
            "none",
        ),
        (
            "v6_fb_004",
            "facebook reelss offf 1hr chat stil ok",
            1,
            "hours",
            "en",
            "heavy",
        ),
        (
            "v6_fb_005",
            "aaj 2 ghante facebook reels mat dikhana",
            2,
            "hours",
            "hi",
            "none",
        ),
        (
            "v6_fb_006",
            "Facebook Spotlight/Reels block 60 minutes, posts ok",
            60,
            "minutes",
            "en",
            "none",
        ),
    ]
    for cid, promise, val, unit, lang, typo in fb_cases:
        rows.append(
            case(
                cid,
                promise,
                policy(
                    duration=duration_fixed(val, unit),
                    blocked_content=[
                        content("short_form_video", "facebook reels", apps=[FB[0]])
                    ],
                    guardrails=["no_short_form_video"],
                    confirm="Facebook Reels blocked; rest of Facebook not fully banned.",
                    interp=["Scoped to Facebook short-form/Reels surface."],
                ),
                cluster="facebook_reels",
                clock="session",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="focus_session",
                    app_surface="other",
                    time_role="session",
                    expected_guardrails=["no_short_form_video"],
                ),
                notes="[semantics:v1][surface:facebook_reels]",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 5. tiktok_quota
    # ------------------------------------------------------------------ #
    tt_cases = [
        ("v6_tt_001", "at most 10 TikToks today then stop", 10, "en", "none"),
        ("v6_tt_002", "15 tiktok videos max for today", 15, "en", "none"),
        ("v6_tt_003", "aaj 8 tiktok only, phir band", 8, "hinglish", "none"),
        ("v6_tt_004", "tiktokk 12 todya then blokk", 12, "en", "heavy"),
        ("v6_tt_005", "indru tiktok 5 mattum", 5, "ta", "none"),
        ("v6_tt_006", "Daily TikTok cap 20 then hard stop for the day", 20, "en", "none"),
        ("v6_tt_007", "sirf 6 tiktok aaj, adult nahi", 6, "hinglish", "none"),
    ]
    for cid, promise, n, lang, typo in tt_cases:
        adult = "adult" in promise.lower()
        rows.append(
            case(
                cid,
                promise,
                policy(
                    commitment_type="quota_entertainment",
                    duration=duration_none(),
                    quotas=[quota("shorts", n, "day")],
                    blocked_content=(
                        [content("adult_sexual", "adult tiktok")] if adult else []
                    ),
                    guardrails=["no_adult_content"] if adult else [],
                    blocked_apps=[],
                    confirm=f"First {n} TikTok/short-form plays today, then block.",
                    interp=[
                        "TikTok count mapped to shorts quota metric (category).",
                        "Interpreted as short-form video plays on TikTok.",
                    ],
                ),
                cluster="tiktok_quota",
                clock="usage_quota",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="quota_entertainment",
                    app_surface="tiktok",
                    time_role="usage_quota",
                    safety_risk="adult" if adult else "none",
                    expected_guardrails=["no_adult_content"] if adult else [],
                ),
                notes=f"[semantics:v1][quota:allow_first_n][app:tiktok] metric=shorts n={n}",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 6. newpipe_clone / chrome_embed
    # ------------------------------------------------------------------ #
    clone_cases = [
        (
            "v6_clone_001",
            "Block Shorts on NewPipe and YouTube for 2 hours; long lectures ok",
            "newpipe_clone",
            2,
            "hours",
            "en",
            "none",
        ),
        (
            "v6_clone_002",
            "newpipe me bhi shorts band, 90 min padhai",
            "newpipe_clone",
            90,
            "minutes",
            "hinglish",
            "none",
        ),
        (
            "v6_clone_003",
            "treat NewPipe like YouTube — no short-form for 3h",
            "newpipe_clone",
            3,
            "hours",
            "en",
            "none",
        ),
        (
            "v6_chrome_004",
            "In Chrome, allow Wikipedia but block YouTube embeds and Shorts pages for 2h",
            "chrome_embed",
            2,
            "hours",
            "en",
            "none",
        ),
        (
            "v6_chrome_005",
            "chrome me sirf docs search, yt embeds mat kholna 90 min",
            "chrome_embed",
            90,
            "minutes",
            "hinglish",
            "none",
        ),
        (
            "v6_chrome_006",
            "block youtube short embeds in browser for 1 hour, keep google docs",
            "chrome_embed",
            1,
            "hours",
            "en",
            "none",
        ),
        (
            "v6_clone_007",
            "vanced/newpipe shorts count too — block shorts 2h study",
            "newpipe_clone",
            2,
            "hours",
            "en",
            "light",
        ),
        (
            "v6_chrome_008",
            "chromee noo yt short embds 2hr wiki okk",
            "chrome_embed",
            2,
            "hours",
            "en",
            "heavy",
        ),
    ]
    for cid, promise, sub, val, unit, lang, typo in clone_cases:
        if sub == "newpipe_clone":
            pol = policy(
                duration=duration_fixed(val, unit),
                allowed_content=[
                    content("long_form_video", "lectures", apps=[YT[0], NP[0]])
                ],
                blocked_content=[
                    content(
                        "short_form_video",
                        "shorts on youtube and newpipe",
                        apps=[YT[0], NP[0]],
                    )
                ],
                guardrails=["no_short_form_video"],
                confirm="Short-form blocked on YouTube and NewPipe; long lectures allowed.",
                interp=[
                    "Clone apps (NewPipe) count as video platforms for short/long rules."
                ],
            )
            surface = "youtube"
            notes = "[semantics:v1][clone:newpipe] category short-form + packages"
        else:
            pol = policy(
                duration=duration_fixed(val, unit),
                allowed_apps=[app(*CH, "study_search")],
                blocked_content=[
                    content("entertainment", "youtube embeds", apps=[CH[0]]),
                    content("short_form_video", "shorts pages", apps=[CH[0]]),
                ],
                guardrails=["no_short_form_video"],
                confirm="Chrome study/search allowed; YouTube embeds and Shorts pages blocked.",
                interp=["Browser embeds count toward short/long video rules."],
            )
            surface = "chrome"
            notes = "[semantics:v1][clone:chrome_embed]"
        rows.append(
            case(
                cid,
                promise,
                pol,
                cluster="newpipe_clone_chrome_embed",
                clock="session",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="focus_session",
                    app_surface=surface,
                    time_role="session",
                    expected_guardrails=["no_short_form_video"],
                ),
                notes=notes,
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 7. neso_playlist_session
    # ------------------------------------------------------------------ #
    neso_cases = [
        (
            "v6_neso_001",
            "Only Neso Academy OS playlist for 3 hours. No Shorts. Lock me if I drift.",
            "en",
            "none",
            True,
        ),
        (
            "v6_neso_002",
            "3h neso academy operating systems playlist only, shorts band, lock on drift",
            "en",
            "none",
            True,
        ),
        (
            "v6_neso_003",
            "sirf Neso OS playlist 3 ghante, shorts nahi, drift pe lock",
            "hinglish",
            "none",
            True,
        ),
        (
            "v6_neso_004",
            "neso academy OS playlist 3 hours no shorts please lock if i leave",
            "en",
            "light",
            True,
        ),
        (
            "v6_neso_005",
            "3 hours only that Neso OS course playlist — block shorts — lock me",
            "en",
            "none",
            True,
        ),
        (
            "v6_neso_006",
            "neso OS playlist mattum 3 hours, shorts venda, drift na lock",
            "ta",
            "none",
            True,
        ),
    ]
    for cid, promise, lang, typo, need_fu in neso_cases:
        rows.append(
            case(
                cid,
                promise,
                policy(
                    duration=duration_fixed(3, "hours"),
                    allowed_content=[
                        content("study", "neso academy OS playlist", apps=[YT[0]])
                    ],
                    blocked_content=[
                        content("short_form_video", "shorts", apps=[YT[0]])
                    ],
                    guardrails=["no_short_form_video"],
                    lock_policy=lock(True, None, "commitment_pause"),
                    follow_up=need_fu,
                    follow_up_q=(
                        "Confirm the exact Neso Academy OS playlist/channel URL or id?"
                        if need_fu
                        else None
                    ),
                    confidence=0.55 if need_fu else 0.85,
                    confirm="3h Neso OS playlist focus; Shorts blocked; lock on drift.",
                    interp=[
                        "Compiled best-effort playlist session; ask to confirm playlist identity."
                    ],
                ),
                cluster="neso_playlist_session",
                clock="session",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="focus_session",
                    app_surface="youtube",
                    time_role="session",
                    expected_followup=need_fu,
                    expected_guardrails=["no_short_form_video"],
                ),
                notes="[semantics:v1][neso] 3h + no shorts + lock + followup playlist id",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 8. permanent_year_adult_dating_install
    # ------------------------------------------------------------------ #
    perm_cases = [
        (
            "v6_perm_001",
            "No porn for 1 year, and block dating app installs too",
            ["no_adult_content", "no_dating_apps"],
            "combo",
            "en",
            "none",
        ),
        (
            "v6_perm_002",
            "1 year: never adult content, no tinder/bumble installs",
            ["no_adult_content", "no_dating_apps"],
            "combo",
            "en",
            "none",
        ),
        (
            "v6_perm_003",
            "ek saal porn nahi, dating apps install mat hone dena",
            ["no_adult_content", "no_dating_apps"],
            "combo",
            "hinglish",
            "none",
        ),
        (
            "v6_perm_004",
            "permanent: block adult sites and dating installs for a year",
            ["no_adult_content", "no_dating_apps"],
            "combo",
            "en",
            "none",
        ),
        (
            "v6_perm_005",
            "noo porn 1 yr + blokk dating instalss",
            ["no_adult_content", "no_dating_apps"],
            "combo",
            "en",
            "heavy",
        ),
        (
            "v6_perm_006",
            "orutha varusham adult content venda, dating app install block",
            ["no_adult_content", "no_dating_apps"],
            "combo",
            "ta",
            "none",
        ),
        (
            "v6_perm_007",
            "No adult content for 1 year; keep rest of phone normal",
            ["no_adult_content"],
            "adult_only",
            "en",
            "none",
        ),
    ]
    for cid, promise, guards, kind, lang, typo in perm_cases:
        blocked_apps = []
        if "no_dating_apps" in guards:
            blocked_apps = [
                app("com.tinder", "Tinder", "install"),
                app("com.bumble.app", "Bumble", "install"),
            ]
        ctype = "install_gate" if "no_dating_apps" in guards else "permanent_guardrail"
        # Combined adult+dating year rule: permanent_guardrail with install blocks
        if kind == "combo":
            ctype = "permanent_guardrail"
        rows.append(
            case(
                cid,
                promise,
                policy(
                    commitment_type=ctype,
                    duration=duration_fixed(1, "years"),
                    guardrails=guards,
                    blocked_content=[content("adult_sexual", "porn/adult")]
                    if "no_adult_content" in guards
                    else [],
                    blocked_apps=blocked_apps,
                    confirm="1-year adult block"
                    + (" plus dating install gate." if blocked_apps else "."),
                    interp=["Long-term permanent guardrail span (1 year)."],
                ),
                cluster="permanent_year_adult_dating_install",
                clock="permanent",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="permanent_guardrail"
                    if ctype == "permanent_guardrail"
                    else "install_gate",
                    app_surface="play_store" if blocked_apps else "none",
                    time_role="permanent",
                    safety_risk="dating" if blocked_apps else "adult",
                    expected_guardrails=guards,
                ),
                notes="[semantics:v1][permanent:1y] adult ± dating install",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 9. media_max vs entertainment_budget contrast pairs
    # ------------------------------------------------------------------ #
    contrast_pairs = [
        (
            "v6_mmax_001",
            "only videos under 8 minutes during my 30 minute break",
            policy(
                duration=duration_fixed(30, "minutes"),
                quotas=[quota("max_item_minutes", 8, "item")],
                allowed_content=[
                    content("short_form_video", "videos under 8 minutes")
                ],
                confirm="30m break; each video must be ≤8 minutes (media length, not budget).",
                interp=["8 minutes is per-item media_max, not entertainment_minutes."],
            ),
            "media_max",
            "multi_clock",
            "combo",
            "[semantics:v1][clock:media_max] NOT entertainment_budget",
        ),
        (
            "v6_ebudget_001",
            "entertainment 8 minutes per day max then hard stop",
            policy(
                commitment_type="quota_entertainment",
                duration=duration_none(),
                quotas=[quota("entertainment_minutes", 8, "day")],
                confirm="8 minutes total entertainment budget per day.",
                interp=["8 minutes is usage budget entertainment_minutes, not media_max."],
            ),
            "usage_quota",
            "usage_quota",
            "quota_entertainment",
            "[semantics:v1][clock:entertainment_budget] contrast to media_max",
        ),
        (
            "v6_mmax_002",
            "block any video longer than 40 minutes on YouTube tonight",
            policy(
                duration=duration_none(),
                quotas=[quota("max_item_minutes", 40, "item")],
                blocked_content=[
                    content(
                        "long_form_video",
                        "videos over 40 min",
                        apps=[YT[0]],
                    )
                ],
                follow_up=True,
                follow_up_q="What time does tonight end for this commitment?",
                confidence=0.5,
                confirm="Per-video length cap 40 minutes on YouTube (not a 40m session).",
                interp=["40 is media_max, not session duration."],
            ),
            "media_max",
            "media_max",
            "focus_session",
            "[semantics:v1][clock:media_max] tonight vague → followup",
        ),
        (
            "v6_ebudget_002",
            "40 minutes entertainment max today then stop",
            policy(
                commitment_type="quota_entertainment",
                duration=duration_none(),
                quotas=[quota("entertainment_minutes", 40, "day")],
                confirm="40 minutes entertainment budget for the calendar day.",
                interp=["40 is daily usage budget, not max video length."],
            ),
            "usage_quota",
            "usage_quota",
            "quota_entertainment",
            "[semantics:v1][clock:entertainment_budget] contrast pair",
        ),
        (
            "v6_mmax_003",
            "clips max 10 min only; focus block is 2 hours",
            policy(
                duration=duration_fixed(2, "hours"),
                quotas=[quota("max_item_minutes", 10, "item")],
                confirm="2h session; each clip ≤10 minutes.",
                interp=["Session duration and media_max are separate clocks."],
            ),
            "multi_clock",
            "multi_clock",
            "combo",
            "[semantics:v1][clock:media_max+session]",
        ),
        (
            "v6_ebudget_003",
            "entertainment budget 45 minutes per day",
            policy(
                commitment_type="quota_entertainment",
                duration=duration_none(),
                quotas=[quota("entertainment_minutes", 45, "day")],
                confirm="45 minutes entertainment per day.",
                interp=[],
            ),
            "usage_quota",
            "usage_quota",
            "quota_entertainment",
            "[semantics:v1][clock:entertainment_budget]",
        ),
        (
            "v6_mmax_004",
            "sirf 8 minute se chhoti videos break me; break 30 min",
            policy(
                duration=duration_fixed(30, "minutes"),
                quotas=[quota("max_item_minutes", 8, "item")],
                confirm="30m break; media length ≤8 min.",
                interp=["Hinglish media_max vs session."],
            ),
            "multi_clock",
            "multi_clock",
            "combo",
            "[semantics:v1][clock:media_max] hinglish",
        ),
        (
            "v6_ebudget_004",
            "aaj entertainment 8 minute total",
            policy(
                commitment_type="quota_entertainment",
                duration=duration_none(),
                quotas=[quota("entertainment_minutes", 8, "day")],
                confirm="8 minutes entertainment budget today.",
                interp=[],
            ),
            "usage_quota",
            "usage_quota",
            "quota_entertainment",
            "[semantics:v1][clock:entertainment_budget] hinglish contrast",
        ),
    ]
    for cid, promise, pol, clock, time_role, ptype, notes in contrast_pairs:
        rows.append(
            case(
                cid,
                promise,
                pol,
                cluster="media_max_vs_entertainment_budget",
                clock=clock,
                dimensions=dims(
                    language="hinglish" if "sirf" in promise or "aaj" in promise else "en",
                    promise_type=ptype,
                    app_surface="youtube",
                    time_role=time_role,
                    expected_followup=bool(pol.get("followUpQuestionRequired")),
                ),
                notes=notes,
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 10. session vs calendar_day
    # ------------------------------------------------------------------ #
    sess_day = [
        (
            "v6_sess_001",
            "focus for 2 hours, no shorts",
            policy(
                duration=duration_fixed(2, "hours"),
                blocked_content=[content("short_form_video", "shorts")],
                guardrails=["no_short_form_video"],
                confirm="2-hour focus session; short-form blocked.",
                interp=[],
            ),
            "session",
            "session",
            "[semantics:v1][time:session] explicit hours",
            "en",
            "none",
            ["no_short_form_video"],
            False,
        ),
        (
            "v6_day_001",
            "no shorts for the rest of today",
            policy(
                duration=duration_fixed(1, "days"),
                blocked_content=[content("short_form_video", "shorts")],
                guardrails=["no_short_form_video"],
                confirm="Calendar-day ban on short-form (not a 60m session).",
                interp=["'Today/rest of day' → calendar day, do not invent 1h session."],
            ),
            "session",
            "session",
            "[semantics:v1][time:calendar_day] rest of today ≠ 60min",
            "en",
            "none",
            ["no_short_form_video"],
            False,
        ),
        (
            "v6_day_002",
            "block reels for today",
            policy(
                duration=duration_fixed(1, "days"),
                blocked_content=[content("short_form_video", "reels")],
                guardrails=["no_short_form_video"],
                confirm="Reels blocked for the calendar day.",
                interp=["'Today' is calendar day window."],
            ),
            "session",
            "session",
            "[semantics:v1][time:calendar_day]",
            "en",
            "none",
            ["no_short_form_video"],
            False,
        ),
        (
            "v6_sess_002",
            "90 minute study block, youtube shorts off",
            policy(
                duration=duration_fixed(90, "minutes"),
                blocked_content=[
                    content("short_form_video", "youtube shorts", apps=[YT[0]])
                ],
                guardrails=["no_short_form_video"],
                confirm="90-minute study session; YouTube Shorts blocked.",
                interp=[],
            ),
            "session",
            "session",
            "[semantics:v1][time:session]",
            "en",
            "none",
            ["no_short_form_video"],
            False,
        ),
        (
            "v6_day_003",
            "aaj bhar shorts band",
            policy(
                duration=duration_fixed(1, "days"),
                blocked_content=[content("short_form_video", "shorts")],
                guardrails=["no_short_form_video"],
                confirm="Short-form blocked for today (calendar day).",
                interp=["Hinglish 'aaj bhar' → calendar day."],
            ),
            "session",
            "session",
            "[semantics:v1][time:calendar_day] hinglish",
            "hinglish",
            "none",
            ["no_short_form_video"],
            False,
        ),
        (
            "v6_day_004",
            "10 shorts today only",
            _shorts_quota_policy(10, adult=False, long_edu=False),
            "usage_quota",
            "usage_quota",
            f"{SEM_QUOTA} daily quota not session",
            "en",
            "none",
            [],
            False,
        ),
        (
            "v6_sess_003",
            "2 ghante padhai no reels",
            policy(
                duration=duration_fixed(2, "hours"),
                blocked_content=[content("short_form_video", "reels")],
                guardrails=["no_short_form_video"],
                confirm="2-hour study; Reels blocked.",
                interp=[],
            ),
            "session",
            "session",
            "[semantics:v1][time:session] hinglish",
            "hinglish",
            "none",
            ["no_short_form_video"],
            False,
        ),
        (
            "v6_day_005",
            "for 7 days no shorts",
            policy(
                duration=duration_fixed(7, "days"),
                blocked_content=[content("short_form_video", "shorts")],
                guardrails=["no_short_form_video"],
                confirm="7-day calendar window; short-form blocked.",
                interp=["Multi-day window, not a 7-hour session."],
            ),
            "session",
            "session",
            "[semantics:v1][time:calendar_day] 7 days",
            "en",
            "none",
            ["no_short_form_video"],
            False,
        ),
    ]
    for cid, promise, pol, clock, time_role, notes, lang, typo, guards, fu in sess_day:
        rows.append(
            case(
                cid,
                promise,
                pol,
                cluster="session_vs_calendar_day",
                clock=clock,
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type=pol["commitmentType"]
                    if pol["commitmentType"] != "focus_session"
                    else "focus_session",
                    app_surface="multi",
                    time_role=time_role,
                    expected_followup=fu,
                    expected_guardrails=guards,
                ),
                notes=notes,
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 11. lock_duration vs session
    # ------------------------------------------------------------------ #
    lock_cases = [
        (
            "v6_lock_001",
            "study 2 hours; if I open reels lock me 15 minutes",
            2,
            "hours",
            15,
            "en",
            "none",
        ),
        (
            "v6_lock_002",
            "3h focus, warn twice then 10 min lock on tiktok",
            3,
            "hours",
            10,
            "en",
            "none",
        ),
        (
            "v6_lock_003",
            "2 ghante padhai, reels mt dekhna, warning 2 baar then 15 min lock",
            2,
            "hours",
            15,
            "hinglish",
            "light",
        ),
        (
            "v6_lock_004",
            "commitment until midnight; lock phone 10 minutes if TikTok twice",
            None,
            None,
            10,
            "en",
            "none",
        ),
        (
            "v6_lock_005",
            "1 hour study; lock 5 min if shorts",
            1,
            "hours",
            5,
            "en",
            "none",
        ),
        (
            "v6_lock_006",
            "focusxx 90 min; openn reels → 20 min lockk",
            90,
            "minutes",
            20,
            "en",
            "heavy",
        ),
        (
            "v6_lock_007",
            "2 hours padhai; drift pe 15 nimisham lock",
            2,
            "hours",
            15,
            "ta",
            "none",
        ),
    ]
    for cid, promise, sval, sunit, lmin, lang, typo in lock_cases:
        if sval is None:
            dur = duration_until("00:00")
            strikes = strike(warn=2, strikes=2)
            blocked_apps = [app(*TT, "full")]
            blocked_content = []
            guards = []
        else:
            dur = duration_fixed(sval, sunit)
            strikes = (
                strike(warn=2, strikes=2) if "warn" in promise.lower() or "warning" in promise.lower() else strike()
            )
            blocked_apps = []
            blocked_content = [content("short_form_video", "reels/shorts")]
            guards = ["no_short_form_video"]
        rows.append(
            case(
                cid,
                promise,
                policy(
                    duration=dur,
                    blocked_apps=blocked_apps,
                    blocked_content=blocked_content,
                    guardrails=guards,
                    strike_policy=strikes,
                    lock_policy=lock(True, lmin),
                    confirm=f"Session clock separate from {lmin}m lock cooldown.",
                    interp=[
                        "lockPolicy.durationMinutes is lock cooldown, not session length."
                    ],
                ),
                cluster="lock_duration_vs_session",
                clock="multi_clock",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="combo",
                    app_surface="multi",
                    time_role="multi_clock",
                    expected_guardrails=guards,
                ),
                notes=f"[semantics:v1][clock:lock_vs_session] lock={lmin}m",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 12. ambiguous_clarify
    # ------------------------------------------------------------------ #
    amb_cases = [
        (
            "v6_amb_001",
            "40 min youtube",
            "Is 40 minutes a study session, a daily YouTube budget, or a max video length?",
            "en",
            "none",
            "youtube",
            "ambiguous",
        ),
        (
            "v6_amb_002",
            "study only",
            "Which apps/sites count as study, and how long should this last?",
            "en",
            "none",
            "multi",
            "ambiguous",
        ),
        (
            "v6_amb_003",
            "allow youtube",
            "Allow all of YouTube, or only lectures/playlists? For how long?",
            "en",
            "none",
            "youtube",
            "ambiguous",
        ),
        (
            "v6_amb_004",
            "block bad apps",
            "Which apps are 'bad', and how long should the block last?",
            "en",
            "none",
            "multi",
            "ambiguous",
        ),
        (
            "v6_amb_005",
            "keep me off distraction apps for a while",
            "Which apps count as distraction, and how long should this last?",
            "en",
            "none",
            "multi",
            "ambiguous",
        ),
        (
            "v6_amb_006",
            "youtube thoda allow karo",
            "YouTube kaunsa part allow (lectures / all), aur kitni der?",
            "hinglish",
            "none",
            "youtube",
            "ambiguous",
        ),
        (
            "v6_amb_007",
            "40min yt studdy??",
            "Is 40 minutes the session length, daily quota, or max video length?",
            "en",
            "heavy",
            "youtube",
            "ambiguous",
        ),
        (
            "v6_amb_008",
            "normal phone but focus somehow",
            "What should be blocked or limited, and for how long?",
            "en",
            "none",
            "multi",
            "ambiguous",
        ),
    ]
    for cid, promise, q, lang, typo, surface, ptype in amb_cases:
        rows.append(
            case(
                cid,
                promise,
                policy(
                    duration=duration_none(),
                    follow_up=True,
                    follow_up_q=q,
                    confidence=0.35,
                    confirm=None,
                    interp=["Ambiguous role/scope — ask before inventing clocks."],
                ),
                cluster="ambiguous_clarify",
                clock="ambiguous",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type=ptype,
                    app_surface=surface,
                    time_role="ambiguous",
                    expected_followup=True,
                ),
                notes="[semantics:v1][followup] clarify before inventing policy",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 13. install_gate
    # ------------------------------------------------------------------ #
    install_cases = [
        (
            "v6_inst_001",
            "block tinder bumble installs this semester",
            ["no_dating_apps"],
            120,
            "days",
            "en",
            "light",
            "dating",
        ),
        (
            "v6_inst_002",
            "no dating app downloads for 6 months",
            ["no_dating_apps"],
            6,
            "months",
            "en",
            "none",
            "dating",
        ),
        (
            "v6_inst_003",
            "block entertainment app installs for 30 days",
            ["no_entertainment_installs"],
            30,
            "days",
            "en",
            "none",
            "none",
        ),
        (
            "v6_inst_004",
            "is semester dating apps install mat hone dena",
            ["no_dating_apps"],
            120,
            "days",
            "hinglish",
            "none",
            "dating",
        ),
        (
            "v6_inst_005",
            "blokk tnder bumbl instalss 4 months",
            ["no_dating_apps"],
            4,
            "months",
            "en",
            "heavy",
            "dating",
        ),
        (
            "v6_inst_006",
            "play store se dating apps mat install hone do 90 days",
            ["no_dating_apps"],
            90,
            "days",
            "hinglish",
            "none",
            "dating",
        ),
        (
            "v6_inst_007",
            "no new social apps installs for 2 weeks",
            ["no_entertainment_installs"],
            14,
            "days",
            "en",
            "none",
            "none",
        ),
    ]
    # Schema duration unit has no "months" — map months → days
    for cid, promise, guards, val, unit, lang, typo, risk in install_cases:
        if unit == "months":
            dur = duration_fixed(val * 30, "days")
            dur_note = f"{val} months ≈ {val * 30} days"
        else:
            dur = duration_fixed(val, unit)
            dur_note = f"{val} {unit}"
        blocked = []
        if "no_dating_apps" in guards:
            blocked = [
                app("com.tinder", "Tinder", "install"),
                app("com.bumble.app", "Bumble", "install"),
            ]
        rows.append(
            case(
                cid,
                promise,
                policy(
                    commitment_type="install_gate",
                    duration=dur,
                    guardrails=guards,
                    blocked_apps=blocked,
                    confirm=f"Install gate for {dur_note}.",
                    interp=["Install/download intent → install_gate commitmentType."],
                ),
                cluster="install_gate",
                clock="session",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="install_gate",
                    app_surface="play_store",
                    time_role="session",
                    safety_risk=risk,
                    expected_guardrails=guards,
                ),
                notes=f"[semantics:v1][install_gate] {dur_note}",
                now=now,
            )
        )

    # ------------------------------------------------------------------ #
    # 14. adult_false_positive
    # ------------------------------------------------------------------ #
    fp_cases = [
        (
            "v6_fp_001",
            "allow adult learning courses on Coursera, block adult sites",
            content("study", "adult learning courses"),
            content("adult_sexual", "adult sites"),
            "en",
            "none",
            "education ≠ porn",
        ),
        (
            "v6_fp_002",
            "allow romance movies, block porn tabs",
            content("entertainment", "romance movies"),
            content("adult_sexual", "porn tabs"),
            "en",
            "none",
            "romance ≠ porn",
        ),
        (
            "v6_fp_003",
            "adult education news ok, block nsfw",
            content("study", "adult education news"),
            content("adult_sexual", "nsfw"),
            "en",
            "none",
            "adult education news ≠ porn",
        ),
        (
            "v6_fp_004",
            "allow 'adulting' finance videos, block porn",
            content("study", "adulting finance videos"),
            content("adult_sexual", "porn"),
            "en",
            "none",
            "adulting ≠ adult sexual",
        ),
        (
            "v6_fp_005",
            "coursera adult learners track allow, adult websites block forever",
            content("study", "coursera adult learners"),
            content("adult_sexual", "adult websites"),
            "en",
            "none",
            "adult learners ≠ porn",
        ),
        (
            "v6_fp_006",
            "adult learning courses chalne do, porn sites band",
            content("study", "adult learning courses"),
            content("adult_sexual", "porn sites"),
            "hinglish",
            "none",
            "hinglish false adult",
        ),
        (
            "v6_fp_007",
            "allow adult literacy programs, never adult sexual content",
            content("study", "adult literacy programs"),
            content("adult_sexual", "adult sexual content"),
            "en",
            "none",
            "literacy ≠ sexual",
        ),
        (
            "v6_fp_008",
            "romance drama netflix ok, xvideos type sites block",
            content("entertainment", "romance drama"),
            content("adult_sexual", "porn sites"),
            "en",
            "light",
            "romance drama ≠ porn",
        ),
    ]
    for cid, promise, allowed, blocked, lang, typo, note in fp_cases:
        rows.append(
            case(
                cid,
                promise,
                policy(
                    commitment_type="permanent_guardrail",
                    duration=duration_indefinite(),
                    guardrails=["no_adult_content"],
                    allowed_content=[allowed],
                    blocked_content=[blocked],
                    confirm="Block adult/sexual content; keep education/romance as stated.",
                    interp=[
                        "Do not treat 'adult learning/education/romance' as porn false positive."
                    ],
                ),
                cluster="adult_false_positive",
                clock="permanent",
                dimensions=dims(
                    language=lang,
                    typo_level=typo,
                    promise_type="permanent_guardrail",
                    app_surface="chrome",
                    time_role="permanent",
                    safety_risk="false_adult",
                    expected_guardrails=["no_adult_content"],
                ),
                notes=f"[semantics:v1][safety:false_adult] {note}",
                now=now,
            )
        )

    # Extra high-signal variants to ensure >=100 and deepen weak clusters
    extras = [
        case(
            "v6_quota_en_016",
            "Cap short-form at 10 plays today. Adult always blocked. Long educational YouTube allowed after.",
            _shorts_quota_policy(10),
            cluster="short_form_daily_quota",
            clock="usage_quota",
            dimensions=dims(
                promise_type="quota_entertainment",
                app_surface="multi",
                time_role="usage_quota",
                safety_risk="adult",
                expected_guardrails=["no_adult_content"],
            ),
            notes=f"{SEM_QUOTA} paraphrase LIVE",
            now=now,
        ),
        case(
            "v6_quota_hi_017",
            "aaj max 10 short form, adult sexual kabhi nahi, education wali lambi YT allowed",
            _shorts_quota_policy(10),
            cluster="short_form_daily_quota",
            clock="usage_quota",
            dimensions=dims(
                language="hinglish",
                promise_type="quota_entertainment",
                app_surface="multi",
                time_role="usage_quota",
                safety_risk="adult",
                expected_guardrails=["no_adult_content"],
            ),
            notes=f"{SEM_QUOTA} hinglish paraphrase",
            now=now,
        ),
        case(
            "v6_scope_all_011",
            "short videos (any platform) — 10 today then stop",
            _shorts_quota_policy(10, adult=False, long_edu=False),
            cluster="youtube_shorts_only_vs_all_short_form",
            clock="usage_quota",
            dimensions=dims(
                promise_type="quota_entertainment",
                app_surface="multi",
                time_role="usage_quota",
            ),
            notes=f"{SEM_ALL} any platform phrasing",
            now=now,
        ),
        case(
            "v6_ig_009",
            "DMs with friends ok on IG; Reels completely off for 2 hours of deep work",
            policy(
                duration=duration_fixed(2, "hours"),
                allowed_apps=[app(*IG, "messages")],
                blocked_content=[content("short_form_video", "reels", apps=[IG[0]])],
                guardrails=["no_short_form_video"],
                confirm="IG DMs allowed; Reels blocked for 2h.",
                interp=["Surface split DM vs Reels."],
            ),
            cluster="instagram_dm_vs_reels",
            clock="session",
            dimensions=dims(
                promise_type="focus_session",
                app_surface="instagram",
                time_role="session",
                expected_guardrails=["no_short_form_video"],
            ),
            notes="[semantics:v1][surface:ig_dm_vs_reels]",
            now=now,
        ),
        case(
            "v6_tt_008",
            "tiktok 10 aaj ke baad band rest of day",
            policy(
                commitment_type="quota_entertainment",
                duration=duration_none(),
                quotas=[quota("shorts", 10, "day")],
                confirm="First 10 TikTok plays today then block.",
                interp=["TikTok daily count → shorts metric."],
            ),
            cluster="tiktok_quota",
            clock="usage_quota",
            dimensions=dims(
                language="hinglish",
                promise_type="quota_entertainment",
                app_surface="tiktok",
                time_role="usage_quota",
            ),
            notes="[semantics:v1][quota:allow_first_n][app:tiktok]",
            now=now,
        ),
        case(
            "v6_amb_009",
            "entertainment band but allow youtube",
            policy(
                duration=duration_none(),
                follow_up=True,
                follow_up_q="Allow which YouTube (study only vs all), and for how long?",
                confidence=0.3,
                interp=["Conflicting allow YouTube vs ban entertainment — ask."],
            ),
            cluster="ambiguous_clarify",
            clock="ambiguous",
            dimensions=dims(
                promise_type="ambiguous",
                app_surface="youtube",
                time_role="ambiguous",
                expected_followup=True,
            ),
            notes="[semantics:v1][followup] conflicting allow youtube",
            now=now,
        ),
        case(
            "v6_fp_009",
            "adult continuing education webinars ok; block adult sexual content",
            policy(
                commitment_type="permanent_guardrail",
                duration=duration_indefinite(),
                guardrails=["no_adult_content"],
                allowed_content=[content("study", "adult continuing education")],
                blocked_content=[content("adult_sexual", "adult sexual content")],
                confirm="Education allowed; adult/sexual blocked.",
                interp=["adult continuing education ≠ porn."],
            ),
            cluster="adult_false_positive",
            clock="permanent",
            dimensions=dims(
                promise_type="permanent_guardrail",
                app_surface="chrome",
                time_role="permanent",
                safety_risk="false_adult",
                expected_guardrails=["no_adult_content"],
            ),
            notes="[semantics:v1][safety:false_adult] continuing education",
            now=now,
        ),
        case(
            "v6_day_006",
            "rest of the day no reels no shorts",
            policy(
                duration=duration_fixed(1, "days"),
                blocked_content=[content("short_form_video", "reels and shorts")],
                guardrails=["no_short_form_video"],
                confirm="Short-form blocked for rest of calendar day.",
                interp=["Do not invent a 60-minute session."],
            ),
            cluster="session_vs_calendar_day",
            clock="session",
            dimensions=dims(
                promise_type="focus_session",
                app_surface="multi",
                time_role="session",
                expected_guardrails=["no_short_form_video"],
            ),
            notes="[semantics:v1][time:calendar_day]",
            now=now,
        ),
    ]
    rows.extend(extras)

    # Deduplicate ids
    seen = set()
    uniq = []
    for r in rows:
        if r["id"] in seen:
            raise ValueError(f"duplicate id: {r['id']}")
        seen.add(r["id"])
        uniq.append(r)
    return uniq


def main() -> None:
    rows = build()
    if len(rows) < 100:
        raise SystemExit(f"Need >=100 cases, got {len(rows)}")
    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} cases -> {OUT}")
    hist = Counter(r["cluster"] for r in rows)
    print("cluster histogram:")
    for k, v in sorted(hist.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {k}: {v}")
    print(f"total clusters: {len(hist)}")


if __name__ == "__main__":
    main()

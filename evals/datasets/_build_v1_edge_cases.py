#!/usr/bin/env python3
"""Build v1_edge_cases.jsonl — run once, not part of eval runner."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("v1_edge_cases.jsonl")

# Each case: dict with all required schema fields + optional commitment fields.
# notes prefix: severity tag for humans until schema adds severityLevel (see design doc).

CASES: list[dict] = []

def add(
    id: str,
    pkg: str,
    label: str,
    screen: str,
    goal: str,
    strict: str,
    guards: list[str],
    commit: str,
    decision: str,
    reason: str,
    notes: str,
    counters: dict | None = None,
    limit: str = "n/a",
) -> None:
    CASES.append(
        {
            "id": id,
            "packageName": pkg,
            "appLabel": label,
            "screenText": screen,
            "userGoal": goal,
            "strictnessLevel": strict,
            "activeGuardrails": guards,
            "commitmentType": commit,
            "sessionCounters": counters,
            "limitState": limit,
            "expectedDecision": decision,
            "expectedReasonCategory": reason,
            "notes": notes,
        }
    )


YT = "com.google.android.youtube"
CH = "com.android.chrome"
WA = "com.whatsapp"
IG = "com.instagram.android"
PS = "com.android.vending"
SET = "com.android.settings"
GPT = "com.openai.chatgpt"
HOME = "com.miui.home"
PH = "com.google.android.dialer"

LECTURE_SHELF = (
    "Organic Chemistry — Full Lecture\n"
    "Chapter 7: Reaction mechanisms\n"
    "Shorts shelf visible below player (not opened)\n"
    "Playing 58:22"
)
SHORTS_PLAYER = (
    "Shorts\nVertical swipe feed\nDance trend #47\n"
    "Swipe up for more\nAuto-advance on"
)
SHORTS_ALT = (
    "Short-form videos\nFeed\nSwipe ↑\nClip 12/∞"
)

# --- YouTube: lecture + shelf (same screen, promise-driven) ---
for i, (goal, dec, reason, sev) in enumerate(
    [
        ("Finish organic chem unit; long lectures are fine", "ALLOW", "study_aligned", "medium"),
        ("Organic chem but warn me if I tap the Shorts shelf", "WARN", "ambiguous", "high"),
        ("Zero short-form video during exam week", "BLOCK", "short_form_disallowed", "high"),
        ("Monk mode until JEE mains — study content only", "BLOCK", "strict_monk_mode", "high"),
    ],
    start=1,
):
    add(
        f"v1_yt_lecture_shelf_{i:03d}",
        YT,
        "YouTube",
        LECTURE_SHELF,
        goal,
        "STRICT",
        [],
        "focus_session" if i < 4 else "monk_mode",
        dec,
        reason,
        f"[severity:{sev}] Long lecture foreground + Shorts shelf not opened; decision from promise",
    )

# --- YouTube: actual Shorts player ---
add("v1_yt_shorts_study_block_001", YT, "YouTube", SHORTS_PLAYER, "Study DSA 2 hours no Shorts", "STRICT", [], "focus_session", "BLOCK", "short_form_disallowed", "[severity:high] Active Shorts player under study ban")
add("v1_yt_shorts_quota40_allow_001", YT, "YouTube", SHORTS_PLAYER, "Allow up to 40 Shorts today then stop", "STRICT", [], "quota_entertainment", "ALLOW", "limit_not_reached", "[severity:medium] Quota 18/40", {"shortsWatched": 18, "shortsLimit": 40}, "not_reached")
add("v1_yt_shorts_quota40_block_001", YT, "YouTube", SHORTS_PLAYER, "Allow up to 40 Shorts today then stop", "STRICT", [], "quota_entertainment", "BLOCK", "limit_reached", "[severity:medium] Quota 40/40", {"shortsWatched": 40, "shortsLimit": 40}, "reached")
add("v1_yt_shorts_quota40_adult_block_001", YT, "YouTube", "Shorts\nMature comedy 18+ preview\nSwipe feed", "Allow up to 40 Shorts today; no porn ever", "STRICT", ["no_adult_content"], "quota_entertainment", "BLOCK", "adult_content", "[severity:critical] Guardrail overrides quota", {"shortsWatched": 5, "shortsLimit": 40}, "not_reached")
add("v1_yt_shorts_monk_block_001", YT, "YouTube", SHORTS_ALT, "Monk mode: zero entertainment", "STRICT", [], "monk_mode", "BLOCK", "strict_monk_mode", "[severity:high] Shorts under monk")
add("v1_yt_shorts_guardrail_allow_001", YT, "YouTube", SHORTS_PLAYER, "No porn for 1 year; otherwise my choice", "SOFT", ["no_adult_content"], "permanent_guardrail", "ALLOW", "user_allowed_entertainment", "[severity:medium] Permanent guardrail only; Shorts OK", {"shortsWatched": 3, "shortsLimit": 100}, "not_reached")
add("v1_yt_shorts_time_warn_001", YT, "YouTube", SHORTS_PLAYER, "Nudge after 10 min in Shorts", "STRICT", [], "time_threshold", "WARN", "limit_reached", "[severity:medium] Time threshold", {"sessionMinutes": 11, "warnAfterMinutes": 10}, "reached")
add("v1_yt_shorts_lock_001", YT, "YouTube", SHORTS_PLAYER, "No Shorts; lock after 3 attempts", "LOCKED", [], "focus_session", "LOCK", "limit_reached", "[severity:critical] Attempt lock", {"attemptCount": 3}, "reached")
add("v1_yt_comment_hash_allow_001", YT, "YouTube", "MIT Lecture 3\nComment: see #shorts recap\nPaused", "Long videos for revision OK", "STRICT", [], "focus_session", "ALLOW", "study_aligned", "[severity:high] Mention not player")
add("v1_yt_home_row_warn_001", YT, "YouTube", "Home\nRecommended lectures\nShorts row label (not tapped)", "Warn if I head toward Shorts", "SMART", [], "focus_session", "WARN", "ambiguous", "[severity:medium] Home shelf drift")
add("v1_yt_loading_warn_001", YT, "YouTube", "YouTube\nBuffering…", "Exam prep no vertical feed", "STRICT", [], "focus_session", "WARN", "ambiguous", "[severity:medium] Incomplete evidence")
add("v1_yt_lecture_quota_allow_001", YT, "YouTube", "Real Analysis\nLecture 5\n1:20:00 playing", "Allow 40 Shorts daily budget", "STRICT", [], "quota_entertainment", "ALLOW", "study_aligned", "[severity:medium] Lecture not short-form despite quota promise", {"shortsWatched": 10, "shortsLimit": 40}, "not_reached")

# --- Chrome: false adult vs real adult ---
FALSE_ADULT_SCREENS = [
    ("BBC\nAdult literacy programs expand", "ALLOW", "user_allowed_entertainment", "News false positive"),
    ("Philosophy StackExchange\nMature themes in ethics essay", "ALLOW", "study_aligned", "Academic mature themes"),
    ("Wikipedia\nHuman sexual reproduction biology", "ALLOW", "study_aligned", "Educational anatomy"),
    ("LinkedIn\nSenior professionals network", "ALLOW", "study_aligned", "Adult in career context"),
]
for i, (screen, dec, reason, note) in enumerate(FALSE_ADULT_SCREENS, 1):
    add(f"v1_ch_false_adult_{i:03d}", CH, "Chrome", screen, "No porn for 1 year; everything else allowed", "SOFT", ["no_adult_content"], "permanent_guardrail", dec, reason, f"[severity:high] Chrome false adult trap: {note}")

REAL_ADULT_SCREENS = [
    ("Verify age 18+\nExplicit sexual content\nContinue", "BLOCK", "adult_content"),
    ("Pornhub\nTrending\nAge gate", "BLOCK", "adult_content"),
    ("OnlyFans\nSubscribe 18+ only", "BLOCK", "adult_content"),
    ("Dating\nMeet singles for hookups 18+", "BLOCK", "adult_content"),
]
for i, (screen, dec, reason) in enumerate(REAL_ADULT_SCREENS, 1):
    add(f"v1_ch_real_adult_{i:03d}", CH, "Chrome", screen, "No porn for 1 year; everything else allowed", "SOFT", ["no_adult_content"], "permanent_guardrail", dec, reason, f"[severity:critical] Real adult/dating gate #{i}")

add("v1_ch_movie_guardrail_allow_001", CH, "Chrome", "StreamFlix\nWatch HD films free", "No porn for 1 year; otherwise my choice", "SOFT", ["no_adult_content"], "permanent_guardrail", "ALLOW", "user_allowed_entertainment", "[severity:high] Entertainment not adult under guardrail")
add("v1_ch_movie_edu_block_001", CH, "Chrome", "StreamFlix\nWatch HD films free", "Research papers only tonight", "STRICT", [], "focus_session", "BLOCK", "short_form_disallowed", "[severity:medium] Movie under edu promise")
add("v1_ch_shortlisted_allow_001", CH, "Chrome", "Gmail\nYou are shortlisted for internship", "Research and career prep OK", "STRICT", [], "focus_session", "ALLOW", "study_aligned", "[severity:high] shortlisted substring trap")
add("v1_ch_so_allow_001", CH, "Chrome", "Stack Overflow\nKotlin coroutine\nSidebar: meme t-shirt ad", "Finish assignment tonight", "STRICT", [], "focus_session", "ALLOW", "study_aligned", "[severity:high] Foreground study beats sidebar ad")
add("v1_ch_meme_warn_001", CH, "Chrome", "reddit.com/r/memes\nTop post today", "Coding forums yes memes no", "STRICT", [], "focus_session", "WARN", "social_feed", "[severity:medium] Discouraged meme WARN not BLOCK")
add("v1_ch_blank_warn_001", CH, "Chrome", "about:blank", "Study session active", "STRICT", [], "focus_session", "WARN", "neutral_navigation", "[severity:low] Empty tab")
add("v1_ch_piracy_block_001", CH, "Chrome", "TorrentBay\nMagnet links movies", "Educational browsing only", "STRICT", [], "focus_session", "BLOCK", "ambiguous", "[severity:medium] Piracy under edu")

# --- WhatsApp ---
add("v1_wa_tutor_allow_001", WA, "WhatsApp", "Math tutor\nProblem set 6 PDF", "Academic WhatsApp allowed", "STRICT", [], "focus_session", "ALLOW", "safe_app", "[severity:medium] Useful academic")
add("v1_wa_family_allow_001", WA, "WhatsApp", "Mom\nDinner ready when home?", "Family messages always OK", "LOCKED", [], "focus_session", "ALLOW", "safe_app", "[severity:medium] Family safety")
add("v1_wa_gossip_warn_001", WA, "WhatsApp", "Hostel\nTea about professor quiz", "Finish assignment before sleep", "STRICT", [], "focus_session", "WARN", "social_feed", "[severity:medium] Gossip friction")
add("v1_wa_meme_monk_block_001", WA, "WhatsApp", "Meme factory\nForwarded chain x20", "Monk mode zero fun", "LOCKED", [], "monk_mode", "BLOCK", "strict_monk_mode", "[severity:high] Meme spam monk")
add("v1_wa_lab_monk_warn_001", WA, "WhatsApp", "Lab partner\nSubmit protocol by 5pm", "Monk mode zero social distraction", "STRICT", [], "monk_mode", "WARN", "social_feed", "[severity:high] Useful but monk friction")
add("v1_wa_party_allow_001", WA, "WhatsApp", "Friend\nHouse party 8pm?", "Social break until 7pm allowed", "STRICT", [], "focus_session", "ALLOW", "user_allowed_entertainment", "[severity:low] Allowed social break")
add("v1_wa_incomplete_warn_001", WA, "WhatsApp", "5 unread chats", "Study focus now", "STRICT", [], "focus_session", "WARN", "ambiguous", "[severity:low] Incomplete preview")
add("v1_wa_flirt_warn_001", WA, "WhatsApp", "Crush\nMiss you tons", "Exam prep no flirting", "STRICT", [], "focus_session", "WARN", "social_feed", "[severity:medium] Flirt distraction")

# --- Instagram ---
add("v1_ig_reels_block_001", IG, "Instagram", "Reels\nFor you\nSwipe up", "No Reels during study", "STRICT", [], "focus_session", "BLOCK", "short_form_disallowed", "[severity:high] Active Reels")
add("v1_ig_reels_quota_allow_001", IG, "Instagram", "Reels\nFor you\nSwipe up", "Max 15 Reels reward today", "STRICT", [], "quota_entertainment", "ALLOW", "limit_not_reached", "[severity:medium] Reels quota", {"reelsWatched": 4, "reelsLimit": 15}, "not_reached")
add("v1_ig_reels_quota_block_001", IG, "Instagram", "Reels\nFor you\nSwipe up", "Max 15 Reels reward today", "STRICT", [], "quota_entertainment", "BLOCK", "limit_reached", "[severity:medium] Reels quota full", {"reelsWatched": 15, "reelsLimit": 15}, "reached")
add("v1_ig_feed_allow_001", IG, "Instagram", "Feed\nFriend photos\nNo Reels tab", "Posts OK block Reels only", "SOFT", ["no_adult_content"], "focus_session", "ALLOW", "user_allowed_entertainment", "[severity:medium] Feed not Reels player")
add("v1_ig_dm_work_warn_001", IG, "Instagram", "DM\nClassmate\nShare slides for project", "College work only on Instagram", "STRICT", [], "focus_session", "WARN", "social_feed", "[severity:high] DM friction despite work")
add("v1_ig_dm_gossip_warn_001", IG, "Instagram", "DM\nFriend\nDid you see the drama", "Study session", "STRICT", [], "focus_session", "WARN", "social_feed", "[severity:medium] Gossip DM")
add("v1_ig_explore_reels_block_001", IG, "Instagram", "Explore\nReels grid\nAuto-play preview", "Monk mode", "STRICT", [], "monk_mode", "BLOCK", "strict_monk_mode", "[severity:high] Explore reels monk")

# --- Settings ---
add("v1_set_tamper_lock_001", SET, "Settings", "Accessibility\nPhoneCodex\nTurn off service\nConfirm", "Locked study session", "LOCKED", [], "focus_session", "LOCK", "tamper_attempt", "[severity:critical] Active tamper")
add("v1_set_tamper_lock_002", SET, "Settings", "PhoneCodex overlay\nStop protection?\nYes disable", "Clean phone LOCKED", "LOCKED", [], "focus_session", "LOCK", "tamper_attempt", "[severity:critical] Tamper variant wording")
add("v1_set_a11y_list_warn_001", SET, "Settings", "Accessibility\nInstalled services\nPhoneCodex enabled\nBrowsing", "LOCKED do not disable PhoneCodex", "LOCKED", [], "focus_session", "WARN", "neutral_navigation", "[severity:high] Browse not tamper")
add("v1_set_wifi_warn_001", SET, "Settings", "Network\nWi-Fi connected\nSignal good", "Finish assignment tonight", "STRICT", [], "focus_session", "WARN", "neutral_navigation", "[severity:low] Settings detour study")
add("v1_set_display_warn_001", SET, "Settings", "Display\nBrightness slider", "Study DSA 30 min", "STRICT", [], "focus_session", "WARN", "neutral_navigation", "[severity:low] Benign settings")

# --- Play Store ---
add("v1_ps_tiktok_block_001", PS, "Play Store", "TikTok\nInstall\nShort videos", "No vertical video apps this week", "STRICT", [], "focus_session", "BLOCK", "install_disallowed", "[severity:high] Forbidden install")
add("v1_ps_tiktok_guardrail_allow_001", PS, "Play Store", "TikTok\nInstall", "No porn for 1 year; my apps my choice", "SOFT", ["no_adult_content"], "permanent_guardrail", "ALLOW", "user_allowed_entertainment", "[severity:medium] Guardrail-only install")
add("v1_ps_tinder_block_001", PS, "Play Store", "Tinder\nInstall\nMeet people 18+", "Block porn and dating for 1 year", "STRICT", ["no_adult_content"], "permanent_guardrail", "BLOCK", "adult_content", "[severity:critical] Dating under guardrail")
add("v1_ps_anki_allow_001", PS, "Play Store", "AnkiDroid\nInstall\nFlashcards Education", "Learning apps OK", "STRICT", [], "focus_session", "ALLOW", "install_page_productivity", "[severity:low] Productivity install")
add("v1_ps_netflix_monk_block_001", PS, "Play Store", "Netflix\nInstall\nMovies TV", "Monk mode no entertainment installs", "LOCKED", [], "monk_mode", "BLOCK", "install_disallowed", "[severity:medium] Entertainment install monk")
add("v1_ps_candy_warn_001", PS, "Play Store", "Candy Crush\nInstall\nGames", "Warn on game installs", "STRICT", [], "focus_session", "WARN", "gaming", "[severity:low] Game install warn")
add("v1_ps_duolingo_allow_001", PS, "Play Store", "Duolingo\nInstall\nLanguage learning", "Education installs fine", "STRICT", [], "focus_session", "ALLOW", "install_page_productivity", "[severity:low] Edu install")

# --- ChatGPT ---
add("v1_gpt_code_allow_001", GPT, "ChatGPT", "Debug my DP solution in C++", "Study algorithms tonight", "SMART", [], "focus_session", "ALLOW", "study_aligned", "[severity:medium] Coding aligned")
add("v1_gpt_joke_warn_001", GPT, "ChatGPT", "Tell me a joke about cats", "No comedy detours during study", "SMART", [], "focus_session", "WARN", "ambiguous", "[severity:high] Comedy WARN not BLOCK")
add("v1_gpt_joke_break_allow_001", GPT, "ChatGPT", "Quick joke to relax", "10-minute humor breaks allowed", "STRICT", [], "focus_session", "ALLOW", "user_allowed_entertainment", "[severity:medium] Scheduled break")
add("v1_gpt_roleplay_monk_block_001", GPT, "ChatGPT", "Fantasy RPG adventure mode", "Monk mode study only", "STRICT", [], "monk_mode", "BLOCK", "strict_monk_mode", "[severity:high] Roleplay monk")

# --- Home / Phone ---
add("v1_home_icons_warn_001", HOME, "Home", "Launcher\nYT TT IG icons\n(not opened)", "Study now warn on distraction", "STRICT", [], "focus_session", "WARN", "neutral_navigation", "[severity:medium] Distracting icons")
add("v1_home_guardrail_allow_001", HOME, "Home", "Launcher\nYT TT IG icons\n(not opened)", "No porn for 1 year only", "SOFT", ["no_adult_content"], "permanent_guardrail", "ALLOW", "user_allowed_entertainment", "[severity:medium] Guardrail home")
add("v1_phone_call_allow_001", PH, "Phone", "In call\n00:33", "Monk mode", "LOCKED", [], "emergency_override", "ALLOW", "safe_app", "[severity:medium] Phone always")
add("v1_phone_sos_allow_001", PH, "Phone", "Emergency SOS\nConnecting", "Any commitment active", "LOCKED", [], "emergency_override", "ALLOW", "emergency_or_system", "[severity:critical] Emergency")

# Pad to 100+ with additional edge pairs and variants
EXTRA = [
    (YT, "YouTube", SHORTS_PLAYER, "Allow exactly 40 Shorts per day", "STRICT", [], "quota_entertainment", "ALLOW", "limit_not_reached", {"shortsWatched": 39, "shortsLimit": 40}, "not_reached", "[severity:medium] Edge quota 39/40"),
    (YT, "YouTube", SHORTS_PLAYER, "Allow exactly 40 Shorts per day", "STRICT", [], "quota_entertainment", "BLOCK", "limit_reached", {"shortsWatched": 40, "shortsLimit": 40}, "reached", "[severity:medium] Edge quota at cap"),
    (CH, "Chrome", "IMDb\nParent guide: mature themes discussed", "No porn for 1 year", "SOFT", ["no_adult_content"], "permanent_guardrail", "ALLOW", "user_allowed_entertainment", "n/a", "[severity:high] Mature themes movie info not porn"),
    (CH, "Chrome", "Courseera\nMachine learning certificate", "Entertainment blocked monk", "STRICT", [], "monk_mode", "ALLOW", "study_aligned", "n/a", "[severity:medium] Edu allow monk"),
    (CH, "Chrome", "Twitch\nLive stream gameplay", "Monk mode", "STRICT", [], "monk_mode", "BLOCK", "strict_monk_mode", "n/a", "[severity:medium] Gaming stream monk"),
    (WA, "WhatsApp", "Study circle\nShare past year paper", "Only academic chats", "STRICT", [], "focus_session", "ALLOW", "safe_app", "n/a", "[severity:medium] Past paper"),
    (WA, "WhatsApp", "Random group\n100 forwards", "Study focus", "STRICT", [], "focus_session", "WARN", "social_feed", "n/a", "[severity:medium] Spam warn"),
    (IG, "Instagram", "Stories\nFriend holiday pics", "Study session", "STRICT", [], "focus_session", "WARN", "social_feed", "n/a", "[severity:medium] Stories friction"),
    (IG, "Instagram", LECTURE_SHELF.replace("Organic", "Cooking").replace("Shorts shelf", "Reels tray"), "Cooking tutorials OK no Reels player", "STRICT", [], "focus_session", "ALLOW", "study_aligned", "n/a", "[severity:low] Long video cooking"),
    (PS, "Play Store", "Bumble\nInstall\nDating 18+", "No porn or dating 1 year", "STRICT", ["no_adult_content"], "permanent_guardrail", "BLOCK", "adult_content", "n/a", "[severity:critical] Bumble dating"),
    (PS, "Play Store", "Forest\nInstall\nFocus timer", "Productivity installs welcome", "STRICT", [], "focus_session", "ALLOW", "install_page_productivity", "n/a", "[severity:low] Focus app"),
    (GPT, "ChatGPT", "Explain Bayes theorem for exam", "AI tutoring allowed exam week", "LOCKED", [], "focus_session", "ALLOW", "study_aligned", "n/a", "[severity:medium] Exam AI locked ok"),
    (GPT, "ChatGPT", "Write Netflix binge list", "Educational use only", "SMART", [], "focus_session", "WARN", "ambiguous", "n/a", "[severity:medium] Netflix prompt warn"),
    (HOME, "Home", "Launcher\nCalculator Notes Chrome", "Exam prep", "STRICT", [], "focus_session", "ALLOW", "neutral_navigation", "n/a", "[severity:low] Study home"),
    (HOME, "Home", "Recent apps\nChrome PDF\nInstagram thumb", "Study DSA", "STRICT", [], "focus_session", "WARN", "neutral_navigation", "n/a", "[severity:medium] Recents drift"),
    (YT, "YouTube", "Live cricket highlights\nShorts tab visible not open", "Warn on Shorts navigation", "SMART", [], "focus_session", "WARN", "ambiguous", "n/a", "[severity:medium] Sports + shelf"),
    (YT, "YouTube", SHORTS_PLAYER, "Soft mode: warn before block on Shorts", "SOFT", [], "focus_session", "WARN", "short_form_disallowed", "n/a", "[severity:medium] SOFT first warn? actually study ban - use goal no shorts soft warn first"),
    (CH, "Chrome", "Amazon\nHeadphones deal", "Study only warn shopping", "STRICT", [], "focus_session", "WARN", "shopping", "n/a", "[severity:low] Shopping warn"),
    (SET, "Settings", "Battery saver\nOn", "Build PhoneCodex OK", "STRICT", [], "focus_session", "WARN", "neutral_navigation", "n/a", "[severity:low] Dev battery"),
    (WA, "WhatsApp", "Dad\nCall me urgent", "Monk zero social", "STRICT", [], "monk_mode", "ALLOW", "safe_app", "n/a", "[severity:high] Family urgent monk allow"),
]

# Fix SOFT shorts case - study promise with SOFT should WARN on shorts not block if "warn before block"
EXTRA[16] = (
    YT, "YouTube", SHORTS_PLAYER,
    "Prefer study but if I open Shorts just warn me first",
    "SOFT", [], "focus_session", "WARN", "short_form_disallowed", "n/a",
    "[severity:medium] SOFT warn-first on Shorts",
)

for i, row in enumerate(EXTRA, 1):
    pkg, label, screen, goal, strict, guards, commit, dec, reason, limit_or_note, *rest = row
    counters = None
    limit = "n/a"
    notes = row[-1] if isinstance(row[-1], str) and row[-1].startswith("[severity") else "n/a"
    if len(row) >= 11 and isinstance(row[9], dict):
        counters = row[9]
        limit = row[10]
        notes = row[11]
    elif len(row) == 10:
        notes = row[9]
    add(f"v1_extra_{i:03d}", pkg, label, screen, goal, strict, guards, commit, dec, reason, notes, counters, limit)

MORE = [
    ("v1_yt_pair_shelf_allow_001", YT, "YouTube", "Graph Theory\nLecture 12\nShorts shelf below (closed)", "Allow long study videos", "ALLOW", "study_aligned", "focus_session"),
    ("v1_yt_pair_shelf_warn_001", YT, "YouTube", "Graph Theory\nLecture 12\nShorts shelf below (closed)", "Ping if Shorts shelf tempts me", "WARN", "ambiguous", "focus_session"),
    ("v1_ch_pair_movie_allow_001", CH, "Chrome", "Prime free trial\nMovies", "No porn 1 year rest allowed", "ALLOW", "user_allowed_entertainment", "permanent_guardrail"),
    ("v1_ch_pair_movie_block_001", CH, "Chrome", "Prime free trial\nMovies", "Only academic PDFs tonight", "BLOCK", "short_form_disallowed", "focus_session"),
    ("v1_ig_pair_feed_allow_001", IG, "Instagram", "Feed\nCampus event photos", "Instagram posts OK no Reels", "ALLOW", "user_allowed_entertainment", "focus_session"),
    ("v1_ig_pair_reels_block_001", IG, "Instagram", "Reels\nSwipe feed", "Instagram posts OK no Reels", "BLOCK", "short_form_disallowed", "focus_session"),
    ("v1_wa_pair_academic_allow_001", WA, "WhatsApp", "Prof\nOffice hours moved", "Academic messages only", "ALLOW", "safe_app", "focus_session"),
    ("v1_wa_pair_meme_warn_001", WA, "WhatsApp", "Batch\nMeme dump lol", "Academic messages only", "WARN", "social_feed", "focus_session"),
    ("v1_ps_pair_spotify_warn_001", PS, "Play Store", "Spotify\nInstall\nMusic", "Warn non-study installs", "WARN", "ambiguous", "focus_session"),
    ("v1_gpt_pair_summarize_allow_001", GPT, "ChatGPT", "Summarize chapter 8 notes", "Exam study AI OK", "ALLOW", "study_aligned", "focus_session"),
]
for tid, pkg, label, screen, goal, dec, reason, commit in MORE:
    guards = ["no_adult_content"] if commit == "permanent_guardrail" else []
    add(tid, pkg, label, screen, goal, "STRICT", guards, commit, dec, reason, "[severity:medium] Paired promise case")

# Additional unique cases to reach 100+
for tid, pkg, label, screen, goal, strict, guards, commit, dec, reason, note in [
    ("v1_yt_music_live_allow_001", YT, "YouTube", "Jazz study live\n4h stream\nno Shorts UI", "Background music while revising", "SOFT", [], "focus_session", "ALLOW", "study_aligned", "[severity:low] Live music study"),
    ("v1_ch_reddit_cs_allow_001", CH, "Chrome", "reddit r/cpp\nThread on templates", "Programming forums allowed", "STRICT", [], "focus_session", "ALLOW", "study_aligned", "[severity:medium] CS forum"),
    ("v1_ch_reddit_meme_warn_001", CH, "Chrome", "reddit r/dankmemes", "Programming forums only", "STRICT", [], "focus_session", "WARN", "social_feed", "[severity:medium] Wrong sub warn"),
    ("v1_ig_stories_warn_001", IG, "Instagram", "Stories tray\nFriends\nTap to view", "Study session", "STRICT", [], "focus_session", "WARN", "social_feed", "[severity:medium] Stories"),
    ("v1_set_dev_warn_001", SET, "Settings", "Developer options\nUSB debugging", "Building app OK", "STRICT", [], "focus_session", "WARN", "neutral_navigation", "[severity:low] Dev settings"),
    ("v1_ps_hinge_block_001", PS, "Play Store", "Hinge\nInstall\nDating 18+", "No dating apps 1 year", "STRICT", ["no_adult_content"], "permanent_guardrail", "BLOCK", "adult_content", "[severity:critical] Hinge"),
    ("v1_wa_voice_gossip_warn_001", WA, "WhatsApp", "Group\n4 min voice note gossip", "Study now", "STRICT", [], "focus_session", "WARN", "social_feed", "[severity:medium] Voice gossip"),
    ("v1_gpt_cheating_warn_001", GPT, "ChatGPT", "Write my assignment essay fully", "Use AI to learn not cheat", "STRICT", [], "focus_session", "WARN", "ambiguous", "[severity:medium] Academic integrity edge"),
    ("v1_home_split_allow_001", HOME, "Home", "Split screen\nYouTube lecture\nNotes app", "Study session", "STRICT", [], "focus_session", "ALLOW", "study_aligned", "[severity:medium] Split study"),
    ("v1_yt_premiere_allow_001", YT, "YouTube", "Live premiere\n3h documentary\neducation", "Long form OK", "STRICT", [], "focus_session", "ALLOW", "study_aligned", "[severity:low] Premiere long"),
    ("v1_ch_guardrail_netflix_allow_001", CH, "Chrome", "Netflix.com\nSign in", "No porn 1 year only rule", "SOFT", ["no_adult_content"], "permanent_guardrail", "ALLOW", "user_allowed_entertainment", "[severity:medium] Netflix guardrail"),
    ("v1_ch_edu_block_netflix_001", CH, "Chrome", "Netflix.com\nSign in", "Educational sites only", "STRICT", [], "focus_session", "BLOCK", "short_form_disallowed", "[severity:medium] Netflix edu block"),
    ("v1_ig_reels_monk_block_001", IG, "Instagram", "Reels\nFor you", "Monk mode", "STRICT", [], "monk_mode", "BLOCK", "strict_monk_mode", "[severity:high] Reels monk"),
    ("v1_wa_sticker_monk_block_001", WA, "WhatsApp", "Stickers only spam", "Monk zero fun", "LOCKED", [], "monk_mode", "BLOCK", "strict_monk_mode", "[severity:high] Stickers monk"),
    ("v1_ps_youtube_install_allow_001", PS, "Play Store", "YouTube\nInstall\nVideo", "No porn 1 year", "SOFT", ["no_adult_content"], "permanent_guardrail", "ALLOW", "user_allowed_entertainment", "[severity:low] YT install guardrail"),
    ("v1_yt_shorts_soft_warn_001", YT, "YouTube", SHORTS_PLAYER, "Prefer study but warn if I open Shorts", "SOFT", [], "focus_session", "WARN", "short_form_disallowed", "[severity:medium] SOFT warn-first"),
    ("v1_ch_geeksforgeeks_allow_001", CH, "Chrome", "GeeksforGeeks\nTrie data structure", "DSA study 2h", "STRICT", [], "focus_session", "ALLOW", "study_aligned", "[severity:low] GFG study"),
    ("v1_wa_exam_hall_allow_001", WA, "WhatsApp", "Admin\nExam hall changed B block", "Exam week updates OK", "LOCKED", [], "focus_session", "ALLOW", "safe_app", "[severity:medium] Exam admin"),
]:
    add(tid, pkg, label, screen, goal, strict, guards, commit, dec, reason, note)

def main() -> None:
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)), "duplicate ids"
    assert len(CASES) >= 100, f"only {len(CASES)} cases"
    with OUT.open("w", encoding="utf-8") as f:
        for c in CASES:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Wrote {len(CASES)} cases to {OUT}")


if __name__ == "__main__":
    main()

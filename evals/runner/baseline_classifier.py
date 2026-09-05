"""Commitment-aware keyword baseline classifier."""

from __future__ import annotations

import re
from dataclasses import dataclass

from models import Classification, EvalCase

DECISIONS = ("ALLOW", "WARN", "BLOCK", "LOCK")

SAFE_PACKAGES = {
    "com.google.android.dialer",
    "com.android.dialer",
    "com.android.phone",
}

HOME_PACKAGES = {
    "com.miui.home",
    "com.google.android.apps.nexuslauncher",
    "com.android.launcher3",
}

SYSTEM_UI_PACKAGES = {
    "com.android.systemui",
}

@dataclass(frozen=True)
class PromiseProfile:
    """Parsed user commitment — drives decisions before screen keywords."""

    monk_mode: bool
    guardrail_only: bool
    edu_only: bool
    no_short_form: bool
    warn_not_block: bool
    allows_quota: bool
    allows_entertainment: bool
    allows_study_tools: bool
    allows_academic_social: bool
    allows_family_safety: bool
    allows_social_break: bool
    allows_light_breaks: bool
    lock_after_attempts: int | None
    warns_on_shorts_navigation: bool
    narrow_forums_only: bool
    blocks_entertainment_installs: bool
    warns_on_installs: bool


@dataclass(frozen=True)
class ScreenProfile:
    lowered: str
    is_emergency: bool
    is_home_screen: bool
    is_recent_apps: bool
    in_shorts_player: bool
    in_reels_player: bool
    shorts_shelf_only: bool
    study_foreground: bool
    entertainment_foreground: bool
    adult_signals: bool
    movie_streaming: bool
    piracy: bool
    install_page: bool
    settings_tamper: bool
    settings_browse: bool
    social_distraction: bool
    academic_social: bool
    family_safety: bool
    coding_assistant: bool
    entertainment_assistant: bool
    productivity_install: bool
    entertainment_install: bool
    dating_install: bool
    shopping: bool
    neutral_navigation: bool

def _goal(goal: str) -> str:
    return goal.lower()


def parse_promise(case: EvalCase) -> PromiseProfile:
    g = _goal(case.user_goal)
    commitment = case.commitment_type

    monk_mode = commitment == "monk_mode" or any(
        token in g
        for token in (
            "monk mode",
            "zero entertainment",
            "zero social",
            "study and build only",
            "no youtube at all",
        )
    )

    guardrail_only = commitment == "permanent_guardrail" or any(
        token in g
        for token in (
            "only permanent guardrail",
            "only guardrail",
            "only block adult",
            "only adult guardrail",
            "i choose my apps",
            "i control everything",
            "my choice",
            "home is free",
            "home is unrestricted",
            "everything else is my choice",
        )
    )

    edu_only = any(
        token in g
        for token in (
            "educational browsing only",
            "educational use only",
            "edu only",
            "programming forums only",
        )
    )

    no_short_form = any(
        token in g
        for token in (
            "no short",
            "zero shorts",
            "no reels",
            "no short-video",
            "no short video",
        )
    )

    warn_not_block = "warn" in g and ("do not hard block" in g or "not hard block" in g)

    allows_quota = commitment in {"quota_entertainment"} or bool(
        re.search(r"(allow|max|up to)\s+\d+\s+(shorts|reels)", g)
    )

    allows_entertainment = guardrail_only or allows_quota or any(
        token in g
        for token in (
            "allow normal youtube",
            "allow instagram posts",
            "allow light breaks",
            "humor breaks",
            "social break allowed",
            "normal browsing",
        )
    )

    allows_study_tools = any(
        token in g for token in ("study", "exam", "build phonecodex", "dsa", "productivity installs")
    )

    allows_academic_social = any(
        token in g
        for token in ("academic", "study group", "academic whatsapp", "academic messages")
    )

    allows_family_safety = any(
        token in g for token in ("family safety", "calls always", "always allowed")
    )

    allows_social_break = "social break" in g or "party" in g

    allows_light_breaks = "light break" in g or "humor break" in g

    lock_match = re.search(r"lock after (\d+) attempts?", g)
    lock_after_attempts = int(lock_match.group(1)) if lock_match else None

    warns_on_shorts_navigation = "warn" in g and "shorts" in g and "navigate" in g

    narrow_forums_only = "forums only" in g or "programming forums" in g

    blocks_entertainment_installs = monk_mode or any(
        token in g
        for token in (
            "no entertainment installs",
            "no short video apps",
            "no short-video apps",
            "not during study",
            "after session ends",
        )
    )

    warns_on_installs = "warn on" in g and "install" in g

    return PromiseProfile(
        monk_mode=monk_mode,
        guardrail_only=guardrail_only,
        edu_only=edu_only,
        no_short_form=no_short_form,
        warn_not_block=warn_not_block,
        allows_quota=allows_quota,
        allows_entertainment=allows_entertainment,
        allows_study_tools=allows_study_tools,
        allows_academic_social=allows_academic_social,
        allows_family_safety=allows_family_safety,
        allows_social_break=allows_social_break,
        allows_light_breaks=allows_light_breaks,
        lock_after_attempts=lock_after_attempts,
        warns_on_shorts_navigation=warns_on_shorts_navigation,
        narrow_forums_only=narrow_forums_only,
        blocks_entertainment_installs=blocks_entertainment_installs,
        warns_on_installs=warns_on_installs,
    )


def _is_shorts_player(lowered: str) -> bool:
    if "no shorts tab" in lowered:
        return False
    if "shorts shelf" in lowered or "shorts row" in lowered:
        return False
    if "vertical swipe feed" in lowered and "shorts" in lowered:
        return True
    if lowered.startswith("shorts") and "swipe up" in lowered:
        return True
    return False


def _is_reels_player(lowered: str) -> bool:
    if "no reels tab" in lowered:
        return False
    if "reels" in lowered and ("for you" in lowered or "swipe up" in lowered):
        return True
    return False


def analyze_screen(case: EvalCase) -> ScreenProfile:
    lowered = case.screen_text.lower()

    is_home = (
        "home screen" in lowered
        or "not opened" in lowered
        or "not launched" in lowered
        or case.package_name in HOME_PACKAGES
    )
    is_recent = "recent apps" in lowered

    study_tokens = (
        "lecture",
        "chapter",
        "course",
        "tutorial",
        "documentation",
        "docs",
        "opencourseware",
        "algorithm",
        "study music",
        "deep focus",
        "stack overflow",
        "kotlin",
        "merge sort",
        "recursion",
        "geeksforgeeks",
        "learnprogramming",
        "split screen",
        "keep notes",
        "exam",
        "flashcard",
        "education",
        "productivity",
        "language learning",
        "anki",
        "duolingo",
        "forest focus",
    )
    entertainment_tokens = (
        "prank",
        "movie",
        "streaming",
        "netflix",
        "binge",
        "party tonight",
        "meme",
        "gossip",
        "dance trend",
        "candy crush",
        "games",
        "spotify",
        "r/memes",
    )
    adult_tokens = (
        "mature 17+",
        "rated for 18+",
        "age restricted",
        "verify age",
        "xxx",
        "porn",
        "18+",
        "meet singles",
    )
    academic_social_tokens = (
        "study group",
        "assignment",
        "exam timetable",
        "practice set",
        "math tutor",
        "pdf",
        "algorithm for this",
        "due tomorrow",
        "class rep",
        "hall seating",
    )
    family_tokens = ("dad", "mom", "where are you", "missed call", "reply when free")
    social_distraction_tokens = (
        "gossip",
        "voice note",
        "sticker spam",
        "forwarded joke",
        "hey cutie",
        "meme group",
        "haha lol",
    )
    coding_assistant_tokens = (
        "implement",
        "debug",
        "merge sort",
        "recursion",
        "summarize chapter",
        "policy engine",
        "accessibility service",
        "explain complexity",
    )
    entertainment_assistant_tokens = (
        "funny story",
        "joke",
        "netflix",
        "binge",
        "roleplay",
        "viral instagram",
        "movie trivia",
    )
    productivity_install_tokens = (
        "education",
        "productivity",
        "flashcards",
        "language learning",
        "focus timer",
        "developer",
    )
    entertainment_install_tokens = (
        "tiktok",
        "short videos",
        "candy crush",
        "games",
        "netflix",
        "movies and tv",
        "spotify",
        "music podcasts",
    )

    return ScreenProfile(
        lowered=lowered,
        is_emergency="emergency" in lowered or "112" in lowered,
        is_home_screen=is_home and not is_recent,
        is_recent_apps=is_recent,
        in_shorts_player=_is_shorts_player(lowered),
        in_reels_player=_is_reels_player(lowered),
        shorts_shelf_only=("shorts shelf" in lowered or "shorts row" in lowered)
        and not _is_shorts_player(lowered),
        study_foreground=any(token in lowered for token in study_tokens),
        entertainment_foreground=any(token in lowered for token in entertainment_tokens),
        adult_signals=any(token in lowered for token in adult_tokens),
        movie_streaming=any(token in lowered for token in ("watch latest movies", "free hd", "no signup streaming")),
        piracy=any(token in lowered for token in ("torrent", "magnet", "free movie downloads")),
        install_page="install" in lowered and case.package_name == "com.android.vending",
        settings_tamper=(
            case.package_name == "com.android.settings"
            and "phonecodex" in lowered
            and any(token in lowered for token in ("turn off", "disable service", "confirm disable", "are you sure"))
            and "browsing only" not in lowered
        ),
        settings_browse=case.package_name == "com.android.settings"
        and not (
            "phonecodex" in lowered
            and any(token in lowered for token in ("turn off", "disable service", "confirm disable"))
        ),
        social_distraction=any(token in lowered for token in social_distraction_tokens),
        academic_social=any(token in lowered for token in academic_social_tokens),
        family_safety=any(token in lowered for token in family_tokens),
        coding_assistant=any(token in lowered for token in coding_assistant_tokens),
        entertainment_assistant=any(token in lowered for token in entertainment_assistant_tokens),
        productivity_install=any(token in lowered for token in productivity_install_tokens),
        entertainment_install=any(token in lowered for token in entertainment_install_tokens),
        dating_install="dating" in lowered,
        shopping=any(token in lowered for token in ("amazon", "add to cart", "deals on")),
        neutral_navigation=any(
            token in lowered
            for token in ("wi-fi", "wifi", "bluetooth", "display", "sound", "battery", "new tab", "developer options")
        ),
    )


def _has_guardrail(case: EvalCase, name: str) -> bool:
    return name in case.active_guardrails


def quota_decision(case: EvalCase, short_form: bool) -> Classification | None:
    if not short_form or case.commitment_type != "quota_entertainment":
        return None

    if case.limit_state == "reached":
        return Classification(
            decision="BLOCK",
            confidence=0.92,
            reason="Short-form quota reached per user promise",
            reason_category="limit_reached",
        )

    if case.limit_state == "not_reached":
        if _has_guardrail(case, "no_adult_content"):
            screen = analyze_screen(case)
            if screen.adult_signals:
                return Classification(
                    decision="BLOCK",
                    confidence=0.95,
                    reason="Adult guardrail overrides quota allowance",
                    reason_category="adult_content",
                )
        return Classification(
            decision="ALLOW",
            confidence=0.9,
            reason="Short-form quota not reached per user promise",
            reason_category="limit_not_reached",
        )
    return None


def time_threshold_decision(case: EvalCase, short_form: bool) -> Classification | None:
    if case.commitment_type != "time_threshold" or not short_form:
        return None

    counters = case.session_counters or {}
    session_minutes = counters.get("sessionMinutes", 0)
    warn_after = counters.get("warnAfterMinutes", 0)
    block_after = counters.get("blockAfterMinutes")

    if block_after is not None and session_minutes >= block_after:
        return Classification(
            decision="BLOCK",
            confidence=0.9,
            reason="Short-form time block threshold reached",
            reason_category="limit_reached",
        )

    if case.limit_state == "reached" or session_minutes >= warn_after:
        return Classification(
            decision="WARN",
            confidence=0.85,
            reason="Short-form time warn threshold reached",
            reason_category="limit_reached",
        )

    return Classification(
        decision="ALLOW",
        confidence=0.88,
        reason="Short-form time threshold not reached",
        reason_category="limit_not_reached",
    )


def attempt_lock_decision(case: EvalCase, short_form: bool) -> Classification | None:
    promise = parse_promise(case)
    counters = case.session_counters or {}
    attempt_count = counters.get("attemptCount", 0)
    if (
        promise.lock_after_attempts
        and short_form
        and attempt_count >= promise.lock_after_attempts
        and case.limit_state == "reached"
    ):
        return Classification(
            decision="LOCK",
            confidence=0.95,
            reason="Repeated short-form attempts exceeded promise limit",
            reason_category="limit_reached",
        )
    return None


def adult_guardrail_decision(case: EvalCase, screen: ScreenProfile) -> Classification | None:
    if not _has_guardrail(case, "no_adult_content"):
        return None
    if screen.adult_signals or screen.dating_install:
        return Classification(
            decision="BLOCK",
            confidence=0.96,
            reason="Permanent no-adult guardrail triggered",
            reason_category="adult_content",
        )
    return None


def classify_youtube(case: EvalCase, promise: PromiseProfile, screen: ScreenProfile) -> Classification | None:
    if case.package_name != "com.google.android.youtube":
        return None

    locked = attempt_lock_decision(case, screen.in_shorts_player)
    if locked:
        return locked

    timed = time_threshold_decision(case, screen.in_shorts_player)
    if timed:
        return timed

    quota = quota_decision(case, screen.in_shorts_player)
    if quota:
        return quota

    if screen.in_shorts_player:
        if promise.monk_mode or promise.no_short_form:
            return Classification(
                decision="BLOCK",
                confidence=0.9,
                reason="Short-form disallowed by user promise",
                reason_category="strict_monk_mode" if promise.monk_mode else "short_form_disallowed",
            )
        if promise.guardrail_only or promise.allows_entertainment:
            return Classification(
                decision="ALLOW",
                confidence=0.8,
                reason="Short-form allowed under user entertainment promise",
                reason_category="user_allowed_entertainment",
            )

    if screen.shorts_shelf_only:
        if promise.monk_mode:
            return Classification(
                decision="BLOCK",
                confidence=0.88,
                reason="YouTube blocked under monk-mode promise",
                reason_category="strict_monk_mode",
            )
        if promise.warns_on_shorts_navigation or ("warn" in _goal(case.user_goal) and "shorts" in _goal(case.user_goal)):
            return Classification(
                decision="WARN",
                confidence=0.75,
                reason="Shorts shelf visible; promise requests warn not block",
                reason_category="ambiguous",
            )
        if screen.study_foreground or promise.allows_study_tools:
            return Classification(
                decision="ALLOW",
                confidence=0.85,
                reason="Lecture foreground aligned with study promise",
                reason_category="study_aligned",
            )

    if screen.study_foreground and (promise.allows_study_tools or not promise.monk_mode):
        return Classification(
            decision="ALLOW",
            confidence=0.85,
            reason="Educational YouTube content aligned with promise",
            reason_category="study_aligned",
        )

    if "home feed" in screen.lowered and screen.shorts_shelf_only:
        if promise.guardrail_only:
            return Classification(
                decision="ALLOW",
                confidence=0.8,
                reason="Home browsing allowed under guardrail-only promise",
                reason_category="user_allowed_entertainment",
            )
        if promise.warns_on_shorts_navigation:
            return Classification(
                decision="WARN",
                confidence=0.7,
                reason="Home Shorts shelf visible during study promise",
                reason_category="ambiguous",
            )

    if promise.monk_mode:
        return Classification(
            decision="BLOCK",
            confidence=0.85,
            reason="YouTube entertainment blocked under monk mode",
            reason_category="strict_monk_mode",
        )

    return None


def classify_instagram(case: EvalCase, promise: PromiseProfile, screen: ScreenProfile) -> Classification | None:
    if case.package_name != "com.instagram.android":
        return None

    quota = quota_decision(case, screen.in_reels_player)
    if quota:
        return quota

    if screen.in_reels_player:
        if promise.monk_mode or promise.no_short_form:
            return Classification(
                decision="BLOCK",
                confidence=0.9,
                reason="Reels disallowed by user promise",
                reason_category="strict_monk_mode" if promise.monk_mode else "short_form_disallowed",
            )

    if "no reels tab" in screen.lowered or ("home feed" in screen.lowered and not screen.in_reels_player):
        if promise.guardrail_only or "allow instagram posts" in _goal(case.user_goal):
            return Classification(
                decision="ALLOW",
                confidence=0.82,
                reason="Instagram feed allowed; promise blocks only Reels",
                reason_category="user_allowed_entertainment",
            )

    if "direct messages" in screen.lowered:
        return Classification(
            decision="WARN",
            confidence=0.65,
            reason="Social messaging with friction under study promise",
            reason_category="social_feed",
        )

    if screen.in_reels_player and promise.allows_quota:
        return quota_decision(case, True)

    return None


def classify_chrome(case: EvalCase, promise: PromiseProfile, screen: ScreenProfile) -> Classification | None:
    if case.package_name != "com.android.chrome":
        return None

    adult = adult_guardrail_decision(case, screen)
    if adult:
        return adult

    if screen.piracy and (promise.edu_only or promise.monk_mode):
        return Classification(
            decision="BLOCK",
            confidence=0.9,
            reason="Piracy page blocked under educational promise",
            reason_category="ambiguous",
        )

    if screen.study_foreground:
        if promise.monk_mode or promise.edu_only or promise.allows_study_tools or promise.narrow_forums_only:
            return Classification(
                decision="ALLOW",
                confidence=0.85,
                reason="Educational page aligned with study promise",
                reason_category="study_aligned",
            )

    if promise.narrow_forums_only and "r/memes" in screen.lowered:
        return Classification(
            decision="WARN",
            confidence=0.7,
            reason="Non-study forum under narrow browsing promise",
            reason_category="social_feed",
        )

    if screen.movie_streaming or "netflix" in screen.lowered:
        if promise.guardrail_only:
            return Classification(
                decision="ALLOW",
                confidence=0.82,
                reason="Entertainment browsing allowed under guardrail-only promise",
                reason_category="user_allowed_entertainment",
            )
        if promise.monk_mode or promise.edu_only:
            return Classification(
                decision="BLOCK",
                confidence=0.88,
                reason="Entertainment page blocked by study or monk promise",
                reason_category="strict_monk_mode" if promise.monk_mode else "short_form_disallowed",
            )
        if promise.warn_not_block:
            return Classification(
                decision="WARN",
                confidence=0.7,
                reason="Non-study browsing warned per soft promise",
                reason_category="ambiguous",
            )

    if screen.shopping and promise.allows_study_tools:
        return Classification(
            decision="WARN",
            confidence=0.65,
            reason="Shopping page unrelated to study promise",
            reason_category="shopping",
        )

    if screen.neutral_navigation and promise.allows_study_tools:
        return Classification(
            decision="WARN",
            confidence=0.55,
            reason="Neutral browser navigation during study session",
            reason_category="neutral_navigation",
        )

    if promise.monk_mode and screen.entertainment_foreground:
        return Classification(
            decision="BLOCK",
            confidence=0.85,
            reason="Entertainment browsing blocked under monk mode",
            reason_category="strict_monk_mode",
        )

    return None


def classify_chatgpt(case: EvalCase, promise: PromiseProfile, screen: ScreenProfile) -> Classification | None:
    if case.package_name != "com.openai.chatgpt":
        return None

    if screen.coding_assistant and (promise.allows_study_tools or "ai study help still allowed" in _goal(case.user_goal)):
        return Classification(
            decision="ALLOW",
            confidence=0.85,
            reason="Assistant use aligned with study or build promise",
            reason_category="study_aligned",
        )

    if screen.entertainment_assistant:
        if promise.monk_mode:
            return Classification(
                decision="BLOCK",
                confidence=0.88,
                reason="Entertainment assistant use blocked under monk mode",
                reason_category="strict_monk_mode",
            )
        if promise.allows_light_breaks or promise.allows_social_break or "humor breaks" in _goal(case.user_goal):
            return Classification(
                decision="ALLOW",
                confidence=0.8,
                reason="Light entertainment allowed by break promise",
                reason_category="user_allowed_entertainment",
            )
        if promise.guardrail_only and "movie trivia" in screen.lowered:
            return Classification(
                decision="ALLOW",
                confidence=0.78,
                reason="Trivia allowed when only adult guardrail is active",
                reason_category="user_allowed_entertainment",
            )
        if promise.allows_study_tools or promise.edu_only:
            return Classification(
                decision="WARN",
                confidence=0.7,
                reason="Entertainment prompt during study-focused promise",
                reason_category="ambiguous",
            )

    if "viral instagram" in screen.lowered:
        return Classification(
            decision="WARN",
            confidence=0.68,
            reason="Social-media assistant use during study promise",
            reason_category="social_feed",
        )

    return Classification(
        decision="WARN",
        confidence=0.5,
        reason="Assistant use unclear relative to promise",
        reason_category="ambiguous",
    )


def classify_whatsapp(case: EvalCase, promise: PromiseProfile, screen: ScreenProfile) -> Classification | None:
    if case.package_name != "com.whatsapp":
        return None

    if screen.family_safety and (promise.allows_family_safety or "family" in _goal(case.user_goal)):
        return Classification(
            decision="ALLOW",
            confidence=0.9,
            reason="Family safety message allowed by promise",
            reason_category="safe_app",
        )

    if screen.academic_social and (promise.allows_academic_social or promise.allows_study_tools):
        if promise.monk_mode and "zero social" in _goal(case.user_goal):
            return Classification(
                decision="WARN",
                confidence=0.72,
                reason="Social message flagged under monk-mode promise",
                reason_category="social_feed",
            )
        return Classification(
            decision="ALLOW",
            confidence=0.85,
            reason="Academic or exam-related message allowed",
            reason_category="safe_app",
        )

    if screen.social_distraction:
        if promise.monk_mode:
            return Classification(
                decision="BLOCK",
                confidence=0.88,
                reason="Social distraction blocked under monk or locked promise",
                reason_category="strict_monk_mode",
            )
        return Classification(
            decision="WARN",
            confidence=0.68,
            reason="Low-value social chat during study promise",
            reason_category="social_feed",
        )

    if screen.entertainment_foreground and promise.allows_social_break:
        return Classification(
            decision="ALLOW",
            confidence=0.8,
            reason="Social message allowed during break promise",
            reason_category="user_allowed_entertainment",
        )

    if promise.allows_study_tools:
        return Classification(
            decision="WARN",
            confidence=0.55,
            reason="WhatsApp message unclear relative to study promise",
            reason_category="social_feed",
        )

    return None


def classify_play_store(case: EvalCase, promise: PromiseProfile, screen: ScreenProfile) -> Classification | None:
    if not screen.install_page:
        return None

    adult = adult_guardrail_decision(case, screen)
    if adult:
        return adult

    if screen.productivity_install and (promise.allows_study_tools or "education apps ok" in _goal(case.user_goal)):
        return Classification(
            decision="ALLOW",
            confidence=0.85,
            reason="Productivity install aligned with study promise",
            reason_category="install_page_productivity",
        )

    if screen.entertainment_install or screen.dating_install:
        if promise.guardrail_only and not screen.dating_install:
            return Classification(
                decision="ALLOW",
                confidence=0.82,
                reason="Install allowed under guardrail-only promise",
                reason_category="user_allowed_entertainment",
            )
        if promise.blocks_entertainment_installs or promise.no_short_form or promise.monk_mode:
            return Classification(
                decision="BLOCK",
                confidence=0.88,
                reason="Entertainment install blocked by focus or monk promise",
                reason_category="install_disallowed",
            )
        if promise.warns_on_installs:
            category = "gaming" if "games" in screen.lowered else "ambiguous"
            return Classification(
                decision="WARN",
                confidence=0.7,
                reason="Non-study install warned per user promise",
                reason_category=category,
            )

    if promise.warns_on_installs:
        return Classification(
            decision="WARN",
            confidence=0.6,
            reason="Install page warned during study promise",
            reason_category="ambiguous",
        )

    return Classification(
        decision="WARN",
        confidence=0.5,
        reason="Install page unclear relative to promise",
        reason_category="ambiguous",
    )


def classify_settings(case: EvalCase, screen: ScreenProfile) -> Classification | None:
    if case.package_name != "com.android.settings":
        return None

    if screen.settings_tamper and case.strictness_level == "LOCKED":
        return Classification(
            decision="LOCK",
            confidence=0.95,
            reason="Attempt to disable PhoneCodex during locked session",
            reason_category="tamper_attempt",
        )

    if screen.settings_browse:
        return Classification(
            decision="WARN",
            confidence=0.6,
            reason="Benign settings navigation during commitment",
            reason_category="neutral_navigation",
        )

    return None


def classify_home(case: EvalCase, promise: PromiseProfile, screen: ScreenProfile) -> Classification | None:
    if not (screen.is_home_screen or case.package_name in HOME_PACKAGES | SYSTEM_UI_PACKAGES):
        return None

    if screen.family_safety and promise.allows_family_safety:
        return Classification(
            decision="ALLOW",
            confidence=0.9,
            reason="Phone or family widget allowed by promise",
            reason_category="safe_app",
        )

    if "split screen" in screen.lowered and screen.study_foreground:
        return Classification(
            decision="ALLOW",
            confidence=0.85,
            reason="Split-screen study setup aligned with promise",
            reason_category="study_aligned",
        )

    if screen.is_recent_apps and promise.allows_study_tools:
        return Classification(
            decision="WARN",
            confidence=0.65,
            reason="Recent apps may include distractions during study",
            reason_category="neutral_navigation",
        )

    study_home_icons = any(token in screen.lowered for token in ("anki", "calculator", "chrome"))
    distraction_home_icons = any(token in screen.lowered for token in ("tiktok", "instagram", "snapchat"))

    if study_home_icons and promise.allows_study_tools and not distraction_home_icons:
        return Classification(
            decision="ALLOW",
            confidence=0.8,
            reason="Home screen shows study apps",
            reason_category="neutral_navigation",
        )

    if promise.guardrail_only:
        return Classification(
            decision="ALLOW",
            confidence=0.82,
            reason="Home screen unrestricted under guardrail-only promise",
            reason_category="user_allowed_entertainment",
        )

    if distraction_home_icons and promise.allows_study_tools:
        return Classification(
            decision="WARN",
            confidence=0.65,
            reason="Distracting app icons visible on home during study",
            reason_category="neutral_navigation",
        )

    if "notification shade" in screen.lowered:
        return Classification(
            decision="WARN",
            confidence=0.6,
            reason="Social notification on home during study",
            reason_category="social_feed",
        )

    return None


def classify_commitment_aware(case: EvalCase) -> Classification:
    promise = parse_promise(case)
    screen = analyze_screen(case)

    if case.package_name in SAFE_PACKAGES or screen.is_emergency or case.commitment_type == "emergency_override":
        return Classification(
            decision="ALLOW",
            confidence=0.99,
            reason="Emergency or phone use always allowed",
            reason_category="emergency_or_system",
        )

    adult = adult_guardrail_decision(case, screen)
    if adult:
        return adult

    # App- and context-specific handlers (promise-first)
    for handler in (
        lambda c, p, s: classify_settings(c, s),
        lambda c, p, s: classify_youtube(c, p, s),
        lambda c, p, s: classify_instagram(c, p, s),
        lambda c, p, s: classify_chrome(c, p, s),
        lambda c, p, s: classify_chatgpt(c, p, s),
        lambda c, p, s: classify_whatsapp(c, p, s),
        lambda c, p, s: classify_play_store(c, p, s),
        lambda c, p, s: classify_home(c, p, s),
    ):
        result = handler(case, promise, screen)
        if result:
            return result

    if screen.in_shorts_player or screen.in_reels_player:
        if promise.no_short_form or promise.monk_mode:
            return Classification(
                decision="BLOCK",
                confidence=0.85,
                reason="Short-form content blocked by promise",
                reason_category="short_form_disallowed",
            )

    if screen.study_foreground and promise.allows_study_tools:
        return Classification(
            decision="ALLOW",
            confidence=0.75,
            reason="Study-aligned content under active promise",
            reason_category="study_aligned",
        )

    if promise.guardrail_only:
        return Classification(
            decision="ALLOW",
            confidence=0.7,
            reason="Allowed under guardrail-only promise",
            reason_category="user_allowed_entertainment",
        )

    if promise.monk_mode and screen.entertainment_foreground:
        return Classification(
            decision="BLOCK",
            confidence=0.8,
            reason="Entertainment blocked under monk mode",
            reason_category="strict_monk_mode",
        )

    return Classification(
        decision="WARN",
        confidence=0.45,
        reason="No strong allow or block signal relative to promise",
        reason_category="ambiguous",
    )

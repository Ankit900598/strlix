"""Rule-based baseline Promise Compiler for eval plumbing."""

from __future__ import annotations

import re
from typing import Any

from promise_models import PromiseCase

COMMITMENT_TYPES = (
    "focus_session",
    "quota_entertainment",
    "time_threshold",
    "permanent_guardrail",
    "monk_mode",
    "install_gate",
    "emergency_override",
)


class PromiseBaselineCompiler:
    name = "baseline"

    def compile(self, case: PromiseCase) -> dict[str, Any] | None:
        text = case.user_promise.lower()
        if self._is_unsafe(text):
            return self._unsafe_policy(text)
        if self._is_ambiguous(text):
            return self._ambiguous_policy(text)
        return self._heuristic_policy(text)

    def _is_unsafe(self, text: str) -> bool:
        unsafe_markers = [
            "spy on",
            "girlfriend's messages",
            "block all emergency",
            "block 112",
            "keylogger",
            "banking password",
            "brick the phone",
            "disable sos",
            "stalk",
            "ex's location",
            "roommate",
            "public server",
            "root silently",
            "hospital and ambulance",
        ]
        return any(marker in text for marker in unsafe_markers)

    def _is_ambiguous(self, text: str) -> bool:
        ambiguous_exact = {
            "be stricter with me",
            "help me focus better",
            "block distractions",
            "less phone",
            "study mode",
            "clean phone",
            "productivity",
            "focus",
            "healthy habits",
        }
        if text.strip() in ambiguous_exact:
            return True
        if text in {"no bad stuff", "restrict social", "i need discipline", "limit youtube"}:
            return True
        if len(text.split()) <= 3 and not any(
            k in text for k in ("hour", "day", "year", "monk", "porn", "shorts", "youtube", "instagram")
        ):
            return True
        return False

    def _base(self, **overrides: Any) -> dict[str, Any]:
        policy = {
            "commitmentType": "focus_session",
            "duration": {"kind": "none", "value": None, "unit": None, "until": None},
            "startCondition": "immediate",
            "strictnessLevel": "STRICT",
            "allowedApps": [],
            "blockedApps": [],
            "allowedContent": [],
            "blockedContent": [],
            "activeGuardrails": [],
            "quotas": [],
            "strikePolicy": {"warnBeforeLock": 0, "strikesBeforeLock": 0, "resetPeriod": "session"},
            "lockPolicy": {"enabled": False, "durationMinutes": None, "scope": "commitment_pause"},
            "emergencyExceptions": [],
            "tamperPolicy": {
                "preventDisable": False,
                "onTamper": "NONE",
                "allowSettingsBrowse": True,
            },
            "followUpQuestionRequired": False,
            "followUpQuestion": None,
            "rejectedUnsafeParts": [],
            "confidence": 0.55,
        }
        policy.update(overrides)
        return policy

    def _unsafe_policy(self, text: str) -> dict[str, Any]:
        rejected = []
        if "emergency" in text or "112" in text or "sos" in text or "hospital" in text:
            rejected.append("blocking emergency access")
        if "spy" in text or "keylogger" in text or "roommate" in text or "stalk" in text:
            rejected.append("non-consensual surveillance")
        if "password" in text or "banking" in text:
            rejected.append("credential harvesting")
        if "brick" in text:
            rejected.append("permanent device damage")
        if not rejected:
            rejected.append("unsafe request")
        return self._base(
            rejectedUnsafeParts=rejected,
            confidence=0.95,
            followUpQuestionRequired=False,
        )

    def _ambiguous_policy(self, text: str) -> dict[str, Any]:
        return self._base(
            followUpQuestionRequired=True,
            followUpQuestion="What should I restrict, allow, and for how long?",
            confidence=0.35,
        )

    def _heuristic_policy(self, text: str) -> dict[str, Any]:
        policy = self._base()

        if any(k in text for k in ("1 year", "1 yr", "365", "forever", "permanent", "no porn", "no xxx", "nsfw", "adult content")):
            policy["commitmentType"] = "permanent_guardrail"
            policy["activeGuardrails"] = ["no_adult_content"]
            policy["blockedContent"] = [
                {"type": "adult_sexual", "description": "explicit sexual content", "apps": []}
            ]
            if "year" in text or "365" in text:
                policy["duration"] = {"kind": "fixed", "value": 1, "unit": "years", "until": None}
            elif "forever" in text or "permanent" in text:
                policy["duration"] = {"kind": "indefinite", "value": None, "unit": None, "until": None}

        if "monk" in text or "zero entertainment" in text or "laser focus" in text:
            policy["commitmentType"] = "monk_mode"
            policy["blockedContent"].append(
                {"type": "entertainment", "description": "entertainment", "apps": []}
            )

        shorts_match = re.search(r"(\d+)\s*shorts", text)
        if shorts_match:
            policy["commitmentType"] = "quota_entertainment"
            policy["quotas"] = [
                {"metric": "shorts", "limit": int(shorts_match.group(1)), "period": "day"}
            ]

        if "no shorts" in text or "no reels" in text or "vertical" in text:
            if "no_short_form_video" not in policy["activeGuardrails"]:
                policy["activeGuardrails"].append("no_short_form_video")
            policy["blockedContent"].append(
                {"type": "short_form_video", "description": "short form video", "apps": []}
            )

        if "youtube" in text and ("calculus" in text or "lecture" in text):
            policy["allowedApps"].append(
                {
                    "packageName": "com.google.android.youtube",
                    "appLabel": "YouTube",
                    "scope": "calculus_only" if "calculus" in text else "lectures_only",
                }
            )

        if "instagram" in text and ("team" in text or "college" in text or "dm" in text):
            policy["allowedApps"].append(
                {
                    "packageName": "com.instagram.android",
                    "appLabel": "Instagram",
                    "scope": "college_team_dm_only",
                }
            )
            policy["blockedContent"].append(
                {"type": "short_form_video", "description": "reels", "apps": ["com.instagram.android"]}
            )

        if "install" in text or "play store" in text or "tiktok" in text:
            policy["commitmentType"] = "install_gate"
            policy["activeGuardrails"].append("no_entertainment_installs")

        if "family" in text or "mom" in text or "dad" in text or "parents" in text:
            policy["emergencyExceptions"].append(
                {"type": "family_calls", "detail": "family"}
            )

        if "don't let me disable" in text or "can't disable" in text or "can't turn off" in text:
            policy["tamperPolicy"] = {
                "preventDisable": True,
                "onTamper": "LOCK",
                "allowSettingsBrowse": True,
            }
            policy["strictnessLevel"] = "LOCKED"

        if "warn twice" in text or "warn 2" in text:
            policy["strikePolicy"] = {
                "warnBeforeLock": 2,
                "strikesBeforeLock": 2,
                "resetPeriod": "session",
            }
        if "lock" in text and re.search(r"(\d+)\s*(min|minute)", text):
            mins = int(re.search(r"(\d+)\s*(min|minute)", text).group(1))
            policy["lockPolicy"] = {
                "enabled": True,
                "durationMinutes": mins,
                "scope": "commitment_pause",
            }

        hours_match = re.search(r"(\d+)\s*h(?:our|rs?)?", text)
        if hours_match:
            policy["duration"] = {
                "kind": "fixed",
                "value": int(hours_match.group(1)),
                "unit": "hours",
                "until": None,
            }

        until_match = re.search(r"till\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", text)
        if until_match:
            policy["duration"] = {
                "kind": "until_clock",
                "value": None,
                "unit": None,
                "until": until_match.group(1).replace(" ", ""),
            }

        policy["activeGuardrails"] = sorted(set(policy["activeGuardrails"]))
        policy["confidence"] = 0.65
        return policy

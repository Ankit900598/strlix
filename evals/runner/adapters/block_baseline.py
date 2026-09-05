"""Rule-based Block Experience baseline (deterministic gold-aligned heuristics)."""

from __future__ import annotations

from block_experience_models import BlockCase


class BlockBaselineWriter:
    name = "baseline"

    def write(self, case: BlockCase) -> dict:
        """Return overlay dict — mirrors dataset gold rules closely."""
        decision = case.decision
        strict = case.strictness_level
        reason = case.reason_category
        promise = case.user_promise

        forbidden = ["DISABLE_PHONECODEX", "OPEN_SETTINGS_EDITOR", "UNINSTALL_HINT"]
        if strict in ("SMART", "STRICT", "LOCKED") or decision in ("LOCK", "COOLING_OFF", "BLOCK"):
            forbidden += ["IGNORE_ANYWAY", "CONTINUE_FREE"]
        if decision in ("LOCK", "COOLING_OFF"):
            forbidden.append("SKIP_COOLDOWN")

        show_cooldown = decision == "COOLING_OFF"
        show_promise = True
        emergency = True

        if reason == "tamper_attempt" or decision == "LOCK":
            return {
                "title": "Tamper blocked" if reason == "tamper_attempt" else "Commitment locked",
                "message": f'Your promise is active: "{promise[:60]}". Wait out the lock.',
                "primaryAction": "WAIT_LOCK",
                "secondaryAction": "EMERGENCY_EXIT",
                "forbiddenActions": sorted(set(forbidden + ["SKIP_COOLDOWN", "CONTINUE_FREE", "IGNORE_ANYWAY"])),
                "tone": "tamper_cold" if reason == "tamper_attempt" else "locked_vault",
                "showCooldown": False,
                "showPromise": True,
                "allowEmergencyExit": True,
            }

        if decision == "COOLING_OFF":
            return {
                "title": "Cooling-off before override",
                "message": f'Friction before breaking: "{promise[:50]}". Wait the timer.',
                "primaryAction": "WAIT_LOCK",
                "secondaryAction": "EMERGENCY_EXIT",
                "forbiddenActions": sorted(set(forbidden + ["SKIP_COOLDOWN", "IGNORE_ANYWAY"])),
                "tone": "locked_vault",
                "showCooldown": True,
                "showPromise": True,
                "allowEmergencyExit": True,
            }

        if decision == "REDIRECT":
            primary = "OPEN_PLAYLIST" if "playlist" in reason or "rail" in reason else "REDIRECT_NOW"
            return {
                "title": "Returning to your rail",
                "message": f'Not on your allowed path. Promise: "{promise[:50]}". Redirecting.',
                "primaryAction": primary if primary == "OPEN_PLAYLIST" else "REDIRECT_NOW",
                "secondaryAction": "OPEN_ALLOWED_LECTURE",
                "forbiddenActions": sorted(set(forbidden)),
                "tone": "strict_guard",
                "showCooldown": False,
                "showPromise": True,
                "allowEmergencyExit": True,
            }

        if reason in ("adult_guardrail", "long_term_promise", "chrome_adult"):
            return {
                "title": "Guardrail: no adult content" if "adult" in reason or "porn" in promise.lower() else "Active life rule",
                "message": f'Long-term / guardrail promise: "{promise[:55]}". This screen is blocked.',
                "primaryAction": "RETURN_SAFE",
                "secondaryAction": "REVIEW_PROMISE",
                "forbiddenActions": sorted(set(forbidden)),
                "tone": "contract_life_rule",
                "showCooldown": show_cooldown,
                "showPromise": show_promise,
                "allowEmergencyExit": emergency,
            }

        if reason == "emergency_exception":
            return {
                "title": "Emergency path stays open",
                "message": f'Emergency/family access remains available under "{promise[:40]}".',
                "primaryAction": "EMERGENCY_EXIT",
                "secondaryAction": "REVIEW_PROMISE",
                "forbiddenActions": sorted(
                    set(
                        [
                            "DISABLE_PHONECODEX",
                            "IGNORE_ANYWAY",
                            "CONTINUE_FREE",
                            "UNINSTALL_HINT",
                            "OPEN_SETTINGS_EDITOR",
                        ]
                    )
                ),
                "tone": "strict_guard",
                "showCooldown": False,
                "showPromise": True,
                "allowEmergencyExit": True,
            }

        if reason in ("whatsapp_distract", "instagram_reels", "reels_temptation", "shorts_temptation", "quota_reached"):
            primary = "EXIT_SURFACE"
            secondary = "STAY_IN_MESSAGES" if "whatsapp" in reason or "instagram" in reason or "reels" in reason else "REVIEW_PROMISE"
            if decision == "WARN" and strict in ("SOFT", "SMART"):
                secondary = "CONTINUE_WITH_STRIKE"
            title = "Shorts on your radar" if "shorts" in reason or "quota" in reason else "Surface blocked by your promise"
            if reason == "quota_reached":
                title = "Shorts quota reached"
            return {
                "title": title,
                "message": f'Promise: "{promise[:50]}". Forbidden surface detected.',
                "primaryAction": primary,
                "secondaryAction": secondary,
                "forbiddenActions": sorted(set(forbidden)),
                "tone": "soft_nudge" if strict == "SOFT" and decision == "WARN" else ("smart_cost" if decision == "WARN" else "strict_guard"),
                "showCooldown": False,
                "showPromise": True,
                "allowEmergencyExit": True,
            }

        if reason in ("whatsapp_risk", "instagram_dm", "whatsapp_useful_warn"):
            return {
                "title": "Useful surface — stay aligned",
                "message": f'Looks allowed under "{promise[:45]}". Don\'t drift to feed/Reels/memes.',
                "primaryAction": "STAY_IN_MESSAGES",
                "secondaryAction": "REVIEW_PROMISE",
                "forbiddenActions": sorted(set(forbidden)),
                "tone": "smart_cost" if strict != "SOFT" else "soft_nudge",
                "showCooldown": False,
                "showPromise": True,
                "allowEmergencyExit": True,
            }

        if reason == "playlist_rail" or "rail" in reason:
            if decision == "REDIRECT":
                return {
                    "title": "Returning to your rail",
                    "message": f'Off-rail content. Promise: "{promise[:50]}".',
                    "primaryAction": "REDIRECT_NOW",
                    "secondaryAction": "OPEN_PLAYLIST",
                    "forbiddenActions": sorted(set(forbidden)),
                    "tone": "strict_guard",
                    "showCooldown": False,
                    "showPromise": True,
                    "allowEmergencyExit": True,
                }
            return {
                "title": "Off your study rail",
                "message": f'Not on allowed playlist/channel. "{promise[:50]}".',
                "primaryAction": "OPEN_PLAYLIST",
                "secondaryAction": "EXIT_SURFACE",
                "forbiddenActions": sorted(set(forbidden)),
                "tone": "strict_guard",
                "showCooldown": False,
                "showPromise": True,
                "allowEmergencyExit": True,
            }

        # default study / chrome / monk
        if decision == "WARN":
            return {
                "title": "Drift from your study promise" if "study" in reason or "chrome" in reason else "Nudge from your promise",
                "message": f'Promise: "{promise[:55]}". This screen may be off-path.',
                "primaryAction": "RETURN_SAFE" if strict == "SOFT" else "EXIT_SURFACE",
                "secondaryAction": "CONTINUE_WITH_STRIKE" if strict in ("SOFT", "SMART") else "REVIEW_PROMISE",
                "forbiddenActions": sorted(set(forbidden)),
                "tone": "soft_nudge" if strict == "SOFT" else "smart_cost",
                "showCooldown": False,
                "showPromise": True,
                "allowEmergencyExit": True,
            }

        return {
            "title": "Outside your study rail" if "monk" not in reason else "Monk mode: entertainment blocked",
            "message": f'Blocked by your promise: "{promise[:55]}".',
            "primaryAction": "OPEN_STUDY_HOME" if "monk" in reason else "EXIT_SURFACE",
            "secondaryAction": "CONTINUE_WITH_STRIKE" if strict == "SOFT" else "REVIEW_PROMISE",
            "forbiddenActions": sorted(set(forbidden)),
            "tone": "strict_guard",
            "showCooldown": False,
            "showPromise": True,
            "allowEmergencyExit": True,
        }

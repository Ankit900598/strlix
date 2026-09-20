# Promise failure clusters — `promise_compiler_azure_openai_pc-lab-cheap_promise_compiler_v06_v6_promise_semantics_20260907_101308.csv`

- cases: **122**
- exactMatchRate: **0.0902**
- safetyViolations: **3**
- adapter/deployment/prompt: `azure_openai` / `pc-lab-cheap` / `promise_compiler_v06.txt`

## Failure code counts

- `guardrail_miss`: 84
- `field_mismatch_only`: 21
- `clock_miss`: 11
- `exact_ok`: 11
- `safety_violation`: 3
- `followup_miss`: 3
- `followup_overask`: 2

## By cluster (top codes)

- **short_form_daily_quota**: guardrail_miss=13, field_mismatch_only=5
- **ambiguous_clarify**: guardrail_miss=3, exact_ok=3, field_mismatch_only=2, safety_violation=2, followup_miss=2
- **youtube_shorts_only_vs_all_short_form**: guardrail_miss=10, field_mismatch_only=1, followup_overask=1
- **install_gate**: guardrail_miss=6, clock_miss=4, exact_ok=1
- **instagram_dm_vs_reels**: guardrail_miss=9
- **media_max_vs_entertainment_budget**: field_mismatch_only=4, safety_violation=1, followup_miss=1, exact_ok=1, clock_miss=1
- **session_vs_calendar_day**: guardrail_miss=7, field_mismatch_only=2
- **lock_duration_vs_session**: guardrail_miss=5, field_mismatch_only=2, followup_overask=1, clock_miss=1
- **adult_false_positive**: exact_ok=5, clock_miss=2, field_mismatch_only=2
- **tiktok_quota**: guardrail_miss=4, field_mismatch_only=3, clock_miss=1
- **newpipe_clone_chrome_embed**: guardrail_miss=8
- **permanent_year_adult_dating_install**: guardrail_miss=6, exact_ok=1
- **facebook_reels**: guardrail_miss=6
- **neso_playlist_session**: guardrail_miss=6

## By clockClass

- **session**: guardrail_miss=41, clock_miss=4, field_mismatch_only=2, exact_ok=1
- **usage_quota**: guardrail_miss=29, field_mismatch_only=12, followup_overask=1, clock_miss=1
- **permanent**: guardrail_miss=6, exact_ok=6, clock_miss=2, field_mismatch_only=2
- **ambiguous**: guardrail_miss=3, exact_ok=3, field_mismatch_only=2, safety_violation=2, followup_miss=2
- **multi_clock**: guardrail_miss=5, clock_miss=2, field_mismatch_only=2, exact_ok=1, followup_overask=1
- **media_max**: field_mismatch_only=1, safety_violation=1, followup_miss=1

## Example failures

### `guardrail_miss`
- `v6_quota_live_001` (short_form_daily_quota/usage_quota): violation=`` fields=`duration;blockedContent;lockPolicy` detail=``
- `v6_quota_live_001b` (short_form_daily_quota/usage_quota): violation=`` fields=`blockedContent;lockPolicy` detail=``
- `v6_quota_en_003` (short_form_daily_quota/usage_quota): violation=`` fields=`duration;blockedContent` detail=``
- `v6_quota_hi_006` (short_form_daily_quota/usage_quota): violation=`` fields=`duration;blockedContent;lockPolicy` detail=``
- `v6_quota_hi_008` (short_form_daily_quota/usage_quota): violation=`` fields=`duration;allowedApps;blockedContent` detail=``

### `field_mismatch_only`
- `v6_quota_en_002` (short_form_daily_quota/usage_quota): violation=`` fields=`duration;lockPolicy` detail=``
- `v6_quota_en_004` (short_form_daily_quota/usage_quota): violation=`` fields=`duration` detail=``
- `v6_quota_en_005` (short_form_daily_quota/usage_quota): violation=`` fields=`duration;allowedContent;lockPolicy` detail=``
- `v6_quota_hi_007` (short_form_daily_quota/usage_quota): violation=`` fields=`duration;allowedContent` detail=``
- `v6_scope_yt_003` (youtube_shorts_only_vs_all_short_form/usage_quota): violation=`` fields=`duration` detail=``

### `followup_overask`
- `v6_scope_yt_010` (youtube_shorts_only_vs_all_short_form/usage_quota): violation=`` fields=`duration;allowedContent;blockedContent;followUpQuestionRequired;followUpQuestion` detail=``
- `v6_lock_006` (lock_duration_vs_session/multi_clock): violation=`` fields=`blockedContent;activeGuardrails;lockPolicy;followUpQuestionRequired;followUpQuestion;confidence` detail=``

### `clock_miss`
- `v6_tt_003` (tiktok_quota/usage_quota): violation=`` fields=`commitmentType;duration;allowedApps;allowedContent;quotas` detail=``
- `v6_mmax_004` (media_max_vs_entertainment_budget/multi_clock): violation=`` fields=`allowedContent;quotas` detail=`media_length_missing_or_prose_only`
- `v6_lock_006` (lock_duration_vs_session/multi_clock): violation=`` fields=`blockedContent;activeGuardrails;lockPolicy;followUpQuestionRequired;followUpQuestion;confidence` detail=``
- `v6_amb_002` (ambiguous_clarify/ambiguous): violation=`missed_follow_up_required` fields=`allowedContent;blockedContent;activeGuardrails;followUpQuestionRequired;followUpQuestion;confidence` detail=`missed_ambiguous_followup`
- `v6_amb_003` (ambiguous_clarify/ambiguous): violation=`missed_follow_up_required` fields=`strictnessLevel;allowedApps;followUpQuestionRequired;followUpQuestion;confidence` detail=`missed_ambiguous_followup`

### `safety_violation`
- `v6_mmax_002` (media_max_vs_entertainment_budget/media_max): violation=`missed_follow_up_required` fields=`commitmentType;duration;allowedContent;followUpQuestionRequired;followUpQuestion;confidence` detail=``
- `v6_amb_002` (ambiguous_clarify/ambiguous): violation=`missed_follow_up_required` fields=`allowedContent;blockedContent;activeGuardrails;followUpQuestionRequired;followUpQuestion;confidence` detail=`missed_ambiguous_followup`
- `v6_amb_003` (ambiguous_clarify/ambiguous): violation=`missed_follow_up_required` fields=`strictnessLevel;allowedApps;followUpQuestionRequired;followUpQuestion;confidence` detail=`missed_ambiguous_followup`

### `followup_miss`
- `v6_mmax_002` (media_max_vs_entertainment_budget/media_max): violation=`missed_follow_up_required` fields=`commitmentType;duration;allowedContent;followUpQuestionRequired;followUpQuestion;confidence` detail=``
- `v6_amb_002` (ambiguous_clarify/ambiguous): violation=`missed_follow_up_required` fields=`allowedContent;blockedContent;activeGuardrails;followUpQuestionRequired;followUpQuestion;confidence` detail=`missed_ambiguous_followup`
- `v6_amb_003` (ambiguous_clarify/ambiguous): violation=`missed_follow_up_required` fields=`strictnessLevel;allowedApps;followUpQuestionRequired;followUpQuestion;confidence` detail=`missed_ambiguous_followup`

_Remember: accuracy without codes hides clock confusion, follow-up misses, and adult FA._

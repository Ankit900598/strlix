# Promise failure clusters — `promise_compiler_azure_openai_pc-lab-cheap_promise_compiler_v05_v4_temporal_clocks_20260907_072341.csv`

- cases: **87**
- exactMatchRate: **0.4483**
- safetyViolations: **0**
- adapter/deployment/prompt: `azure_openai` / `pc-lab-cheap` / `promise_compiler_v05.txt`

## Failure code counts

- `exact_ok`: 39
- `field_mismatch_only`: 30
- `guardrail_miss`: 15
- `followup_overask`: 4

## By cluster (top codes)

- **media_max**: exact_ok=8, field_mismatch_only=3, guardrail_miss=2, followup_overask=1
- **duration_ambiguous**: exact_ok=7, field_mismatch_only=5
- **session_duration**: exact_ok=5, field_mismatch_only=3, followup_overask=2, guardrail_miss=1
- **usage_quota**: exact_ok=6, guardrail_miss=1, field_mismatch_only=1
- **contrast_pair**: field_mismatch_only=4, exact_ok=4
- **session_and_media**: exact_ok=3, guardrail_miss=3, field_mismatch_only=1
- **app_surface**: exact_ok=3, guardrail_miss=2, followup_overask=1, field_mismatch_only=1
- **media_min**: guardrail_miss=5, exact_ok=1
- **lock_duration**: field_mismatch_only=4, exact_ok=1
- **permanent_guardrail**: field_mismatch_only=4, guardrail_miss=1
- **messy_typo**: field_mismatch_only=2, exact_ok=1
- **session_and_usage**: field_mismatch_only=2

## By clockClass

- **media_max**: exact_ok=9, field_mismatch_only=5, guardrail_miss=2, followup_overask=1
- **session**: exact_ok=7, field_mismatch_only=4, followup_overask=3, guardrail_miss=2
- **ambiguous**: exact_ok=7, field_mismatch_only=5
- **usage_quota**: exact_ok=8, field_mismatch_only=2, guardrail_miss=1
- **lock**: field_mismatch_only=6, exact_ok=1
- **session_and_media**: exact_ok=3, guardrail_miss=3, field_mismatch_only=1
- **media_min**: guardrail_miss=5, exact_ok=1
- **permanent**: field_mismatch_only=4, guardrail_miss=1
- **surface**: exact_ok=2, guardrail_miss=1, field_mismatch_only=1
- **session_and_usage**: field_mismatch_only=2
- **shorts_quota**: exact_ok=1

## Example failures

### `field_mismatch_only`
- `tc_sess_005` (session_duration/session): violation=`` fields=`allowedContent` detail=``
- `tc_sess_007` (session_duration/session): violation=`` fields=`allowedContent` detail=``
- `tc_sess_008` (session_duration/session): violation=`` fields=`strictnessLevel;lockPolicy;tamperPolicy` detail=``
- `tc_mmax_013` (media_max/media_max): violation=`` fields=`allowedContent` detail=``
- `tc_mmax_016` (media_max/media_max): violation=`` fields=`allowedContent` detail=``

### `guardrail_miss`
- `tc_mmax_009` (media_max/media_max): violation=`` fields=`allowedContent;blockedContent` detail=``
- `tc_mmax_017` (media_max/media_max): violation=`` fields=`blockedContent` detail=``
- `tc_mmin_019` (media_min/media_min): violation=`` fields=`allowedApps;blockedContent` detail=``
- `tc_mmin_020` (media_min/media_min): violation=`` fields=`blockedContent` detail=``
- `tc_mmin_022` (media_min/media_min): violation=`` fields=`allowedApps;blockedContent` detail=``

### `followup_overask`
- `tc_surf_066` (app_surface/session): violation=`` fields=`allowedApps;allowedContent;blockedContent;followUpQuestionRequired;followUpQuestion;confidence` detail=``
- `tc_mmax2_072` (media_max/media_max): violation=`` fields=`allowedContent;followUpQuestionRequired;followUpQuestion;confidence` detail=``
- `tc_sess2_079` (session_duration/session): violation=`` fields=`startCondition;followUpQuestionRequired;followUpQuestion` detail=``
- `tc_sess2_080` (session_duration/session): violation=`` fields=`followUpQuestionRequired;followUpQuestion` detail=``

_Remember: accuracy without codes hides clock confusion, follow-up misses, and adult FA._

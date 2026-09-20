package com.phonecodex.app.domain.model

data class StudyWorldSettings(
    val durationMinutes: Int,
    val lockAttemptThreshold: Int,
    val blockAttemptCooldownMinutes: Int,
    /**
     * Clock B: block individual videos longer than this many minutes.
     * Null means no structured max-length gate (goal-text heuristics may still apply).
     */
    val maxVideoLengthBlockMinutes: Int? = null,
    /**
     * Clock B: block individual videos shorter than this many minutes.
     * Null means no structured min-length gate (goal-text heuristics may still apply).
     */
    val minVideoLengthBlockMinutes: Int? = null,
    /**
     * Daily short-form play quota (clock C / count). Null = no daily short-form quota.
     * Boundary: plays 1..N ALLOW; N+1+ BLOCK until local day ends.
     */
    val shortFormDailyQuotaLimit: Int? = null,
    /** When true, long educational players are allowed outside the short-form quota. */
    val allowLongEducationalVideos: Boolean = true,
    /**
     * `session_fixed` | `calendar_day` | null (unspecified / legacy).
     * calendar_day → do not invent a second 60m timer; duration is typically 1440.
     */
    val timeWindowKind: String? = null,
    /**
     * When non-empty, media-length / short-form clocks only apply inside these packages.
     * Empty = legacy unrestricted platform set.
     */
    val enforcementScopePackages: List<String> = emptyList(),
    /**
     * Developer opt-in for the 10-day vision counsel experiment.
     * Default OFF. Still requires [VisionExperiment] calendar window.
     * Not a promise clock — [StudyWorldSettingsStore.replaceSettings] must not wipe it.
     */
    val visionExperimentEnabled: Boolean = false
)

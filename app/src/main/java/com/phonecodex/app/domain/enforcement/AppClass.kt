package com.phonecodex.app.domain.enforcement

/**
 * Cheap app-class buckets. Play genre and local heuristics fill these.
 * SOCIAL / COMMUNICATION / UNKNOWN are the leftover that needs more than a store chip.
 */
enum class AppClass {
    GAME,
    DATING,
    SOCIAL,
    COMMUNICATION,
    EDUCATION,
    UTILITY,
    MEDIA,
    MUSIC,
    UNKNOWN
}

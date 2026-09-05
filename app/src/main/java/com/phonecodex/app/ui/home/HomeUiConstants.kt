package com.phonecodex.app.ui.home

internal const val MAX_VISIBLE_INSTALLED_APPS = 30

/**
 * Tap targets on the home screen.
 *
 * [chipLabel] is what the user reads; [promiseText] is the fuller sentence dropped into the
 * input so the parser has something real to work with. The user can still edit it before
 * confirming.
 */
internal data class ExamplePromise(
    val chipLabel: String,
    val promiseText: String
)

internal val EXAMPLE_PROMISES = listOf(
    ExamplePromise(
        chipLabel = "Keep me on one OS playlist for 3 hours",
        promiseText = "Tomorrow I have my OS exam. Keep me on one OS lecture playlist on " +
            "YouTube for 3 hours. No shorts, no other channels. Strict."
    ),
    ExamplePromise(
        chipLabel = "No adult content for 1 year",
        promiseText = "No adult content for 1 year. Locked. Do not let me turn protection " +
            "off in a weak moment."
    ),
    ExamplePromise(
        chipLabel = "Allow YouTube only for calculus",
        promiseText = "Allow YouTube only for calculus lectures for 90 minutes. Block shorts, " +
            "memes and entertainment. Strict."
    ),
    ExamplePromise(
        chipLabel = "Monk mode until 2am",
        promiseText = "Monk mode for 4 hours. Only calls and study. No social, no shorts, " +
            "no games."
    ),
    ExamplePromise(
        chipLabel = "Instagram only for college replies",
        promiseText = "Allow Instagram only for replying to my college team for 20 minutes. " +
            "No reels, no scrolling."
    )
)

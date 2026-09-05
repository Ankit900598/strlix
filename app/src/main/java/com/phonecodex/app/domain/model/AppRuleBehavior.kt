package com.phonecodex.app.domain.model

enum class AppRuleBehavior {
    ALLOW,
    WARN,
    BLOCK,
    AI_DECIDE;

    fun next(): AppRuleBehavior {
        return when (this) {
            ALLOW -> WARN
            WARN -> BLOCK
            BLOCK -> AI_DECIDE
            AI_DECIDE -> ALLOW
        }
    }
}

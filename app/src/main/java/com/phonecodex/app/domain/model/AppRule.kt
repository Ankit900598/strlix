package com.phonecodex.app.domain.model

data class AppRule(
    val packageName: String,
    val label: String,
    val behavior: AppRuleBehavior
)

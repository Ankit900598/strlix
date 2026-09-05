package com.phonecodex.app.domain.model

data class ContextSnapshot(
    val timestampMillis: Long,
    val packageName: String?,
    val appLabel: String?,
    val screenText: String?,
    val url: String? = null
)

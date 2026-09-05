package com.phonecodex.app.domain.model

data class PermanentGuardrail(
    val id: String,
    val name: String,
    val enabled: Boolean,
    val blockedKeywords: Set<String>,
    val blockedPackages: Set<String>,
    val createdAtMillis: Long,
    val expiresAtMillis: Long?
)

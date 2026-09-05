package com.phonecodex.app.domain.model

data class FocusWorld(
    val id: String,
    val name: String,
    val mode: WorldMode,
    val defaultStrictness: StrictnessLevel,
    val allowedPackages: Set<String> = emptySet(),
    val blockedPackages: Set<String> = emptySet(),
    val conditionalPackages: Set<String> = emptySet()
)

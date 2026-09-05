package com.phonecodex.app.domain.classifier

/** Backend response meta — Decision Inspector / debug only. */
data class ClassificationBackendMeta(
    val provider: String?,
    val deployment: String?,
    val promptVersion: String?,
    val latencyMs: Long?
)

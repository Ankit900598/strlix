package com.phonecodex.app.domain.classifier

/**
 * Payload sent to POST /classify. Field names match backend classifierService.js.
 */
data class ClassificationRequest(
    val packageName: String,
    val appLabel: String?,
    val screenText: String,
    val goal: String,
    val strictnessLevel: String,
    val activeGuardrails: List<String>,
    val commitmentType: String,
    val sessionCounters: Map<String, Int>?,
    val limitState: String?,
    /**
     * Optional downscaled JPEG (base64). Never log this field.
     * Backend treats it as advisory counsel and may reject unless AZURE_VISION_EXPERIMENT=1.
     */
    val imageJpegBase64: String? = null
)

package com.phonecodex.app.domain.promise

import com.phonecodex.app.domain.model.FocusPromise

/**
 * Network-first compile with local parser fallback.
 * Pure helper so confirmation wiring stays unit-testable without Android UI.
 */
object PromiseUnderstandingResolver {

    fun resolve(
        text: String,
        compiledResult: Result<CompiledPromiseResponse>,
        parser: FocusPromiseParser = FocusPromiseParser(),
        selectedClarificationOptionId: String? = null,
        namedPackageHint: String? = null
    ): ResolvedPromiseUnderstanding {
        val parseText = CompoundIntentLaw.effectivePromiseText(text, selectedClarificationOptionId)
        val local = parser.parse(parseText, namedPackageHint)
        return compiledResult.fold(
            onSuccess = { compiled ->
                val mapped = CompiledPromiseMapper.toFocusPromise(compiled, fallbackRawText = text)
                ResolvedPromiseUnderstanding(
                    draft = PromiseClarificationLaw.apply(
                        mapped.copy(
                            sessionDurationMinutes = reconcileSessionDurationMinutes(
                                rawText = text,
                                compiledMinutes = mapped.sessionDurationMinutes,
                                localMinutes = local.sessionDurationMinutes
                            )
                        ),
                        selectedClarificationOptionId
                    ),
                    fromCompiler = true
                )
            },
            onFailure = {
                ResolvedPromiseUnderstanding(
                    draft = PromiseClarificationLaw.apply(
                        local.copy(
                            rawText = text,
                            warnings = (local.warnings + CompiledPromiseMapper.LOCAL_FALLBACK_CAUTION)
                                .distinct()
                        ),
                        selectedClarificationOptionId
                    ),
                    fromCompiler = false
                )
            }
        )
    }

    /**
     * Azure often returns the 30-minute default when the user said "1 hrs" / "one hours".
     * Local explicit hour/session phrases win over that leftover default. AI is not law.
     */
    internal fun reconcileSessionDurationMinutes(
        rawText: String,
        compiledMinutes: Int,
        localMinutes: Int
    ): Int {
        if (compiledMinutes == localMinutes) return compiledMinutes.coerceAtLeast(1)
        if (compiledMinutes != FocusPromiseParser.DEFAULT_DURATION_MINUTES) {
            return compiledMinutes.coerceAtLeast(1)
        }
        if (localMinutes <= 0 || localMinutes == FocusPromiseParser.DEFAULT_DURATION_MINUTES) {
            return compiledMinutes.coerceAtLeast(1)
        }
        val normalized = rawText.lowercase()
        val explicitDefaultThirty =
            Regex("""\b(?:for\s+(?:the\s+)?(?:next\s+)?|next\s+)?30\s*(?:min|mins|minutes?)\b""")
                .containsMatchIn(normalized)
        if (explicitDefaultThirty) return compiledMinutes.coerceAtLeast(1)
        return localMinutes
    }
}

data class ResolvedPromiseUnderstanding(
    val draft: FocusPromise,
    val fromCompiler: Boolean
)

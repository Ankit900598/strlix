package com.phonecodex.app.domain.feedback

import com.phonecodex.app.data.FeedbackStore
import com.phonecodex.app.domain.model.DecisionType
import com.phonecodex.app.domain.model.FeedbackEntry

class FeedbackMemory(
    private val feedbackStore: FeedbackStore
) {

    fun findMatchingDecision(packageName: String, screenText: String): String? {
        val currentWords = importantWords(screenText)
        if (currentWords.isEmpty()) return null

        var bestMatch: FeedbackEntry? = null
        var bestOverlap = 0

        feedbackStore.getRecentFeedback()
            .asSequence()
            .filter { entry -> entry.packageName == packageName }
            .forEach { entry ->
                val overlap = countSharedWords(
                    currentWords,
                    importantWords(entry.screenTextPreview)
                )
                if (overlap >= MIN_SHARED_WORDS && overlap > bestOverlap) {
                    bestOverlap = overlap
                    bestMatch = entry
                }
            }

        val decision = bestMatch?.correctedDecision?.uppercase() ?: return null
        return when (decision) {
            DecisionType.ALLOW.name, DecisionType.BLOCK.name -> decision
            else -> null
        }
    }

    private fun importantWords(text: String): Set<String> {
        return text
            .lowercase()
            .split(Regex("\\W+"))
            .asSequence()
            .filter { word -> word.length >= 3 && word !in STOP_WORDS }
            .toSet()
    }

    private fun countSharedWords(left: Set<String>, right: Set<String>): Int {
        return left.intersect(right).size
    }

    companion object {
        private const val MIN_SHARED_WORDS = 2

        private val STOP_WORDS = setOf(
            "the",
            "and",
            "is",
            "for",
            "to",
            "app",
            "home"
        )
    }
}

package com.phonecodex.app.domain.classifier

import com.phonecodex.app.domain.model.DecisionType

class FakeAiContentClassifier : ContentClassifier {

    override fun classify(request: ClassificationRequest): ContentClassification? {
        if (request.packageName !in CLASSIFIED_PACKAGES) return null

        val text = request.screenText.lowercase()
        val sessionGoal = request.goal.lowercase()

        if (BLOCK_KEYWORDS.any { keyword -> text.contains(keyword) }) {
            return ContentClassification(
                decision = DecisionType.BLOCK,
                confidence = 0.85,
                reason = "Fake AI detected distraction",
                source = SOURCE
            )
        }

        if (ALLOW_KEYWORDS.any { keyword ->
                text.contains(keyword) || sessionGoal.contains(keyword)
            }
        ) {
            return ContentClassification(
                decision = DecisionType.ALLOW,
                confidence = 0.75,
                reason = "Fake AI detected study intent",
                source = SOURCE
            )
        }

        return null
    }

    companion object {
        private const val SOURCE = "fake_ai"

        private val CLASSIFIED_PACKAGES = setOf(
            "com.android.chrome",
            "com.google.android.youtube",
            "com.android.vending"
        )

        private val BLOCK_KEYWORDS = listOf(
            "porn",
            "xxx",
            "adult",
            "reels",
            "incognito",
            "rated for 18+",
            "mature 17+",
            "dating",
            "hookup",
            "casino",
            "gambling",
            "betting"
        )

        private val ALLOW_KEYWORDS = listOf(
            "lecture",
            "course",
            "tutorial",
            "documentation",
            "docs",
            "compiler",
            "architecture",
            "math",
            "dsa",
            "algorithm",
            "study",
            "education",
            "productivity",
            "learning",
            "books",
            "developer",
            "coding"
        )
    }
}

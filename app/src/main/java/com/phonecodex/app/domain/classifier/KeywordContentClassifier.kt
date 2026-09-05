package com.phonecodex.app.domain.classifier

import com.phonecodex.app.domain.model.DecisionType

class KeywordContentClassifier : ContentClassifier {

    override fun classify(request: ClassificationRequest): ContentClassification? {
        if (request.packageName !in CLASSIFIED_PACKAGES) return null

        val text = request.screenText.lowercase()
        if (text.contains("blocked by phonecodex")) return null

        // goal is available for later smarter matching; keywords only for now.
        if (ALLOW_KEYWORDS.any { keyword -> text.contains(keyword) }) {
            return ContentClassification(
                decision = DecisionType.ALLOW,
                confidence = KEYWORD_CONFIDENCE,
                reason = "Allowed by study keyword",
                source = SOURCE
            )
        }

        if (BLOCK_KEYWORDS.any { keyword -> text.contains(keyword) }) {
            return ContentClassification(
                decision = DecisionType.BLOCK,
                confidence = KEYWORD_CONFIDENCE,
                reason = "Blocked by distraction keyword",
                source = SOURCE
            )
        }

        return null
    }

    companion object {
        private const val SOURCE = "keyword"
        private const val KEYWORD_CONFIDENCE = 0.6

        private val CLASSIFIED_PACKAGES = setOf(
            "com.android.chrome",
            "com.google.android.youtube",
            "com.android.vending"
        )

        private val BLOCK_KEYWORDS = listOf(
            "reels",
            "porn",
            "xxx",
            "adult",
            "hot videos",
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

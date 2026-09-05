package com.phonecodex.app.domain.classifier

interface ContentClassifier {
    fun classify(request: ClassificationRequest): ContentClassification?
}

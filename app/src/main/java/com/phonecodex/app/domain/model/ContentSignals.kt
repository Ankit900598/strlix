package com.phonecodex.app.domain.model

data class ContentSignals(
    val isYouTubeShorts: Boolean,
    val isLikelySearchOrLecture: Boolean,
    val isChromeAdultOrPorn: Boolean,
    val isChromeStudyLike: Boolean,
    val matchedSignals: List<String>
)

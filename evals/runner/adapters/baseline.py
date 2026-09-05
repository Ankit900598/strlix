"""Local commitment-aware keyword baseline adapter."""

from __future__ import annotations

from baseline_classifier import classify_commitment_aware
from models import Classification, EvalCase


class BaselineAdapter:
    name = "baseline"

    def classify(self, case: EvalCase) -> Classification:
        return classify_commitment_aware(case)

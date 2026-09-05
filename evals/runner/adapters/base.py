"""Classifier adapter protocol."""

from __future__ import annotations

from typing import Protocol

from models import Classification, EvalCase


class ClassifierAdapter(Protocol):
    """Classify one eval case and return a structured decision."""

    name: str

    def classify(self, case: EvalCase) -> Classification:
        """Return decision, confidence, reason, and reason category for the case."""

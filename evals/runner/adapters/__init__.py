"""Classifier adapter registry."""

from __future__ import annotations

from pathlib import Path

from adapters.azure_openai import AzureOpenAIAdapter
from adapters.baseline import BaselineAdapter
from adapters.base import ClassifierAdapter

ADAPTER_NAMES = ("baseline", "azure_openai")


def get_adapter(
    name: str,
    *,
    prompt_path: Path | None = None,
    deployment: str | None = None,
) -> ClassifierAdapter:
    if name not in ADAPTER_NAMES:
        choices = ", ".join(ADAPTER_NAMES)
        raise ValueError(f"Unknown adapter {name!r}. Choose from: {choices}")
    if name == "azure_openai":
        return AzureOpenAIAdapter(prompt_path=prompt_path, deployment=deployment)
    return BaselineAdapter()

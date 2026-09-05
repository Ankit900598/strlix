"""Azure OpenAI classifier adapter for batch eval runs."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from models import Classification, EvalCase

# Env var names only — never hardcode secrets in this repo.
AZURE_OPENAI_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
AZURE_OPENAI_API_KEY = "AZURE_OPENAI_API_KEY"
AZURE_OPENAI_DEPLOYMENT = "AZURE_OPENAI_DEPLOYMENT"
AZURE_OPENAI_API_VERSION = "AZURE_OPENAI_API_VERSION"

REQUIRED_ENV_VARS = (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
)

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "classifier_v01.txt"

# Lab deployments on ay186mnc-1561-resource (westus3). Names only — no secrets.
KNOWN_DEPLOYMENTS: dict[str, str] = {
    "pc-lab-cheap": "gpt-4.1-mini",
    "pc-lab-strong": "gpt-4.1",
    "pc-lab-vision": "gpt-4o",
}

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class AzureConfigError(RuntimeError):
    """Raised when Azure adapter is selected but configuration is incomplete."""


def missing_azure_env_vars() -> list[str]:
    return [name for name in REQUIRED_ENV_VARS if not os.environ.get(name, "").strip()]


def require_azure_env() -> None:
    missing = missing_azure_env_vars()
    if missing:
        names = ", ".join(missing)
        raise AzureConfigError(
            "Azure OpenAI adapter cannot run: the following environment variables are not set: "
            f"{names}. Copy .env.example to .env at the repo root and fill in values from "
            "Azure Portal (ay186mnc-1561-resource → Keys and Endpoint)."
        )


def json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False)


def parse_classifier_json(raw_text: str) -> dict[str, object]:
    text = raw_text.strip()
    block = _JSON_BLOCK_RE.search(text)
    if block:
        text = block.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Classifier response must be a JSON object.")
    return data


class AzureOpenAIAdapter:
    """Batch Azure OpenAI inference using a selectable classifier prompt file."""

    name = "azure_openai"

    def __init__(
        self,
        prompt_path: Path | None = None,
        deployment: str | None = None,
    ) -> None:
        require_azure_env()
        self._endpoint = os.environ[AZURE_OPENAI_ENDPOINT].rstrip("/")
        self._api_key = os.environ[AZURE_OPENAI_API_KEY]
        if deployment:
            if deployment not in KNOWN_DEPLOYMENTS:
                known = ", ".join(sorted(KNOWN_DEPLOYMENTS))
                raise ValueError(
                    f"Unknown deployment {deployment!r}. Choose from: {known}"
                )
            self._deployment = deployment
        else:
            self._deployment = os.environ[AZURE_OPENAI_DEPLOYMENT]
        self._api_version = os.environ[AZURE_OPENAI_API_VERSION]
        self._model_name = KNOWN_DEPLOYMENTS.get(self._deployment, "unknown")
        path = prompt_path or DEFAULT_PROMPT_PATH
        if not path.is_file():
            raise FileNotFoundError(f"Classifier prompt not found: {path}")
        self._prompt_path = path
        self._prompt_template = path.read_text(encoding="utf-8")
        self.last_latency_ms: float | None = None

    @property
    def deployment(self) -> str:
        return self._deployment

    @property
    def model_name(self) -> str:
        return self._model_name

    def classify(self, case: EvalCase) -> Classification:
        messages = self.build_messages(case)
        content = self._chat_completion(messages)
        parsed = parse_classifier_json(content)
        return Classification(
            decision=str(parsed.get("decision", "WARN")).upper(),
            confidence=float(parsed.get("confidence", 0.0)),
            reason=str(parsed.get("reason", "")),
            reason_category=str(parsed.get("reasonCategory", "ambiguous")),
        )

    def build_messages(self, case: EvalCase) -> list[dict[str, str]]:
        user_payload = {
            "packageName": case.package_name,
            "appLabel": case.app_label,
            "screenText": case.screen_text,
            "userGoal": case.user_goal,
            "strictnessLevel": case.strictness_level,
            "activeGuardrails": case.active_guardrails,
            "commitmentType": case.commitment_type,
            "sessionCounters": case.session_counters,
            "limitState": case.limit_state,
        }
        return [
            {"role": "system", "content": self._prompt_template},
            {"role": "user", "content": json_dumps(user_payload)},
        ]

    def _chat_completion(self, messages: list[dict[str, str]]) -> str:
        url = (
            f"{self._endpoint}/openai/deployments/{self._deployment}/chat/completions"
            f"?api-version={self._api_version}"
        )
        body = json.dumps(
            {
                "messages": messages,
                "temperature": 0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "api-key": self._api_key,
            },
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Azure OpenAI request failed ({exc.code}): {detail[:500]}"
            ) from exc
        finally:
            self.last_latency_ms = (time.perf_counter() - started) * 1000.0

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("Azure OpenAI returned no choices.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content:
            raise RuntimeError("Azure OpenAI returned empty message content.")
        return str(content)

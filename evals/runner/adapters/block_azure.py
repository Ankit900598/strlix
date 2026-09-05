"""Azure OpenAI Block Experience writer adapter."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from adapters.azure_openai import (
    KNOWN_DEPLOYMENTS,
    parse_classifier_json,
    require_azure_env,
)
from block_experience_models import BlockCase, BlockResult

DEFAULT_PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "block_experience_v01.txt"
)


class BlockAzureWriter:
    name = "azure_openai"

    def __init__(
        self,
        prompt_path: Path | None = None,
        deployment: str | None = None,
    ) -> None:
        require_azure_env()
        self._endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        self._api_key = os.environ["AZURE_OPENAI_API_KEY"]
        if deployment:
            if deployment not in KNOWN_DEPLOYMENTS:
                known = ", ".join(sorted(KNOWN_DEPLOYMENTS))
                raise ValueError(f"Unknown deployment {deployment!r}. Choose from: {known}")
            self._deployment = deployment
        else:
            self._deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self._api_version = os.environ["AZURE_OPENAI_API_VERSION"]
        path = prompt_path or DEFAULT_PROMPT_PATH
        if not path.is_file():
            raise FileNotFoundError(f"Block experience prompt not found: {path}")
        self._prompt_path = path
        self._prompt_template = path.read_text(encoding="utf-8")

    def write(self, case: BlockCase) -> BlockResult:
        payload = {
            "userPromise": case.user_promise,
            "currentApp": case.current_app,
            "screenSummary": case.screen_summary,
            "decision": case.decision,
            "strictnessLevel": case.strictness_level,
            "reasonCategory": case.reason_category,
            "attemptCount": case.attempt_count,
        }
        messages = [
            {"role": "system", "content": self._prompt_template},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        started = time.perf_counter()
        try:
            raw = self._chat_completion(messages)
            latency = (time.perf_counter() - started) * 1000.0
            overlay = parse_classifier_json(raw)
            if not isinstance(overlay, dict):
                return BlockResult(overlay=None, raw_text=raw, error="not_object", latency_ms=latency)
            return BlockResult(overlay=overlay, raw_text=raw, error=None, latency_ms=latency)
        except Exception as exc:
            latency = (time.perf_counter() - started) * 1000.0
            return BlockResult(overlay=None, raw_text="", error=str(exc), latency_ms=latency)

    def _chat_completion(self, messages: list[dict[str, str]]) -> str:
        url = (
            f"{self._endpoint}/openai/deployments/{self._deployment}/chat/completions"
            f"?api-version={self._api_version}"
        )
        body = json.dumps(
            {
                "messages": messages,
                "temperature": 0,
                "max_tokens": 800,
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
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Azure OpenAI failed ({exc.code}): {detail[:500]}") from exc

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("Azure OpenAI returned no choices")
        content = (choices[0].get("message") or {}).get("content")
        if not content:
            raise RuntimeError("Azure OpenAI returned empty content")
        return str(content)


def get_block_writer(name: str, **kwargs: object):
    if name == "baseline":
        from adapters.block_baseline import BlockBaselineWriter

        return BlockBaselineWriter()
    if name == "azure_openai":
        return BlockAzureWriter(**kwargs)
    raise ValueError(f"Unknown block experience adapter: {name!r}")

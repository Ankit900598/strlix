"""Azure OpenAI Promise Compiler adapter."""

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
from adapters.promise_baseline import PromiseBaselineCompiler
from promise_models import CompileResult, PromiseCase

DEFAULT_PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "promise_compiler_v01.txt"
)


class PromiseAzureCompiler:
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
            raise FileNotFoundError(f"Promise compiler prompt not found: {path}")
        self._prompt_path = path
        self._prompt_template = path.read_text(encoding="utf-8")
        self.last_latency_ms: float | None = None

    def compile(self, case: PromiseCase) -> CompileResult:
        messages = [
            {"role": "system", "content": self._prompt_template},
            {
                "role": "user",
                "content": json.dumps({"userPromise": case.user_promise}, ensure_ascii=False),
            },
        ]
        started = time.perf_counter()
        try:
            raw = self._chat_completion(messages)
            self.last_latency_ms = (time.perf_counter() - started) * 1000.0
            policy = parse_classifier_json(raw)
            if not isinstance(policy, dict):
                return CompileResult(policy=None, raw_text=raw, error="not_object")
            return CompileResult(policy=policy, raw_text=raw, error=None, latency_ms=self.last_latency_ms)
        except Exception as exc:
            self.last_latency_ms = (time.perf_counter() - started) * 1000.0
            return CompileResult(
                policy=None,
                raw_text="",
                error=str(exc),
                latency_ms=self.last_latency_ms,
            )

    def _chat_completion(self, messages: list[dict[str, str]]) -> str:
        url = (
            f"{self._endpoint}/openai/deployments/{self._deployment}/chat/completions"
            f"?api-version={self._api_version}"
        )
        body = json.dumps(
            {
                "messages": messages,
                "temperature": 0,
                "max_tokens": 2000,
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


def get_promise_compiler(name: str, **kwargs: object) -> PromiseBaselineCompiler | PromiseAzureCompiler:
    if name == "baseline":
        return PromiseBaselineCompiler()
    if name == "azure_openai":
        return PromiseAzureCompiler(**kwargs)
    raise ValueError(f"Unknown promise compiler adapter: {name!r}")

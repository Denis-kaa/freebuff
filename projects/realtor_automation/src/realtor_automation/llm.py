"""Local LLM client supporting Ollama and llama.cpp backends."""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any


class LLMError(RuntimeError):
    """Raised when LLM interaction fails."""

    pass


@dataclass
class LLMResponse:
    """Structured response from an LLM."""

    content: str
    model: str = "unknown"
    done: bool = True
    error: str | None = None


class LLMClient:
    """Minimal local LLM client."""

    def __init__(self, base_url: str, model: str, timeout: int = 300) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def ask(self, prompt: str, system: str | None = None) -> LLMResponse:
        """Send a prompt to the local LLM.

        Args:
            prompt: User prompt.
            system: Optional system message.

        Returns:
            LLM response object.

        Raises:
            LLMError: If the request fails.
        """
        if not self._model:
            raise LLMError("LLM model is not configured")

        payload: dict[str, Any***REMOVED*** = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        ***REMOVED***
        if system:
            payload["system"***REMOVED*** = system

        url = f"{self._base_url***REMOVED***/api/generate"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"***REMOVED***,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return LLMResponse(
                content=data.get("response", ""),
                model=self._model,
                done=data.get("done", True),
            )
        except urllib.error.URLError as exc:
            raise LLMError(
                f"Cannot connect to LLM at {self._base_url***REMOVED***: {exc***REMOVED***"
            ) from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"Invalid JSON response from LLM: {exc***REMOVED***") from exc


def get_client(config: dict[str, Any***REMOVED***) -> LLMClient:
    """Build an LLM client from the configuration."""
    llm_cfg = config.get("llm", {***REMOVED***)
    base_url = os.environ.get("OLLAMA_URL", llm_cfg.get("url", "http://127.0.0.1:11434"))
    model = os.environ.get("LLM_MODEL", llm_cfg.get("model", "qwen2.5:7b"))
    timeout = llm_cfg.get("timeout", 300)
    return LLMClient(base_url, model, timeout)

"""Gemini-backed translation draft provider with key rotation and failover.

This is the concrete optional ``TranslationProvider`` used as the "extra
brain". It generates DRAFT translations only; it never publishes to live data
(that stays behind ``publish_reviewed_translation``). Model metadata is kept
deterministic; the model name is a fixed default that can be overridden.

Credentials are held only in a ``GeminiKeyPool`` and are never logged.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable

from app.localization.contract import SourceDocument, TranslationDraft, TranslationStatus
from app.localization.keys import GeminiKeyPool
from app.localization.provider import TranslationProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model***REMOVED***:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiTranslationProvider(TranslationProvider):
    """Generate RU (or configured-locale) translation drafts via Gemini.

    Failover: on API/auth/rate-limit failure it advances the key pool and
    retries the same document with the next key in the rotation.
    """

    provider_id = "gemini"

    def __init__(
        self,
        pool: GeminiKeyPool,
        *,
        model: str = DEFAULT_MODEL,
        api_base: str = GEMINI_API_BASE,
        max_retries: int = 4,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._pool = pool
        self._model = model
        self._api_base = api_base
        self._max_retries = max_retries
        self._timeout = timeout_seconds

    def translate(
        self,
        documents: Iterable[SourceDocument***REMOVED***,
        target_locale: str,
    ) -> tuple[TranslationDraft, ...***REMOVED***:
        drafts: list[TranslationDraft***REMOVED*** = [***REMOVED***
        for source in documents:
            drafts.append(self._translate_one(source, target_locale))
        return tuple(drafts)

    def _translate_one(self, source: SourceDocument, target_locale: str) -> TranslationDraft:
        attempts = 0
        while attempts <= self._max_retries:
            key_index, key = self._pool.acquire()
            try:
                text = self._call(key, source.text, target_locale)
                self._pool.mark_success(key_index)
                return TranslationDraft(
                    document_id=source.document_id,
                    source_hash=source.content_hash,
                    source_locale=source.locale,
                    target_locale=target_locale,
                    text=text,
                    provider=self.provider_id,
                    model=self._model,
                    status=TranslationStatus.DRAFT,
                )
            except _RetryableError as exc:
                self._pool.mark_failed(key_index)
                attempts += 1
                if attempts > self._max_retries:
                    raise RuntimeError(
                        f"all Gemini keys exhausted translating {source.document_id***REMOVED***: {exc***REMOVED***"
                    ) from exc
                time.sleep(min(2 ** attempts, 8))
            except Exception as exc:  # non-retryable (e.g. malformed response)
                raise RuntimeError(
                    f"Gemini translation failed for {source.document_id***REMOVED***: {exc***REMOVED***"
                ) from exc
        raise RuntimeError(f"Gemini translation failed for {source.document_id***REMOVED***")

    def _call(self, key: str, source_text: str, target_locale: str) -> str:
        endpoint = self._api_base.format(model=urllib.parse.quote(self._model, safe=""))
        url = f"{endpoint***REMOVED***?key={urllib.parse.quote(key, safe='')***REMOVED***"
        prompt = self._build_prompt(source_text, target_locale)
        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt***REMOVED******REMOVED******REMOVED******REMOVED***,
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096***REMOVED***,
            ***REMOVED***
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"***REMOVED***,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404, 429, 500, 503):
                raise _RetryableError(f"HTTP {exc.code***REMOVED***") from exc
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise _RetryableError(f"{type(exc).__name__***REMOVED***") from exc

        parts = body.get("candidates", [{***REMOVED******REMOVED***)[0***REMOVED***.get("content", {***REMOVED***).get("parts", [***REMOVED***)
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if not text:
            raise RuntimeError("empty Gemini response")
        return _strip_markers(text)

    @staticmethod
    def _build_prompt(source_text: str, target_locale: str) -> str:
        return (
            "Translate the following Markdown document verbatim into locale "
            f"'{target_locale***REMOVED***'. Preserve exactly: all Markdown structure, code "
            "fences, inline-code spans, links, headings and list nesting. Translate "
            "only prose content; do not translate code, identifiers or URLs. "
            "Return ONLY the translated document, no commentary.\n\n"
            "---SOURCE---\n" + source_text
        )


def _strip_markers(text: str) -> str:
    """Remove common fence markers an LLM may add around its whole answer."""
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0***REMOVED***.startswith("```"):
            lines = lines[1:***REMOVED***
        if lines and lines[-1***REMOVED***.strip().startswith("```"):
            lines = lines[:-1***REMOVED***
        stripped = "\n".join(lines).strip()
    return stripped


class _RetryableError(Exception):
    """Marker for failures that may be resolved by switching to another key."""

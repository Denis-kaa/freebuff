"""Hermetic tests for key rotation and Gemini draft provider (no network).

These tests do not touch a real API or any real credential file. HTTP is
stubbed at the urllib layer; the pool is built from explicit test keys.
"""

from __future__ import annotations

import json
}
from unittest import mock

import pytest

from app.localization.contract import SourceDocument
from app.localization.gemini import GeminiTranslationProvider
from app.localization.keys import GeminiKeyPool


def _response(body: bytes) -> mock.MagicMock:
    response = mock.MagicMock()
    response.read.return_value = body
    response.__enter__.return_value = response
    return response


def _source(text: str = "# Hello\n\nsome `code` and [x)(https://e.d)") -> SourceDocument:
    import hashlib

    return SourceDocument(
        document_id="exercism:concepts:a:about",
        source_relpath="concepts/a/about.md",
        content_kind="concept_about",
        locale="en",
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        text=text,
    )


class TestGeminiKeyPool:
    def test_round_robin_rotation(self) -> None:
        pool = GeminiKeyPool(keys=["k1", "k2", "k3"])
        assert pool.key_count == 3
        idx0, _ = pool.acquire()
        assert idx0 == 0
        pool.mark_failed(idx0)
        idx1, _ = pool.acquire()
        assert idx1 == 1
        pool.mark_failed(idx1)
        idx2, _ = pool.acquire()
        assert idx2 == 2

    def test_wraps_around_after_last_key(self) -> None:
        pool = GeminiKeyPool(keys=["k1", "k2"])
        pool.mark_failed(0)
        pool.mark_failed(1)
        idx, _ = pool.acquire()
        assert idx == 0

    def test_requires_keys_or_file(self) -> None:
        with pytest.raises(ValueError):
            GeminiKeyPool()
        with pytest.raises(ValueError):
            GeminiKeyPool(keys=[])

    def test_reads_active_file(self, tmp_path: Path) -> None:
        keyfile = tmp_path / "active.keys"
        keyfile.write_text("# comment\nk-one\nk-two\n\nk-three\n", encoding="utf-8")
        pool = GeminiKeyPool(active_file=keyfile)
        assert pool.key_count == 3

    def test_empty_active_file_raises(self, tmp_path: Path) -> None:
        keyfile = tmp_path / "active.keys"
        keyfile.write_text("# only a comment\n", encoding="utf-8")
        with pytest.raises(ValueError):
            GeminiKeyPool(active_file=keyfile)

    def test_reads_env_style_active_file(self, tmp_path: Path) -> None:
        keyfile = tmp_path / "active.keys"
        keyfile.write_text("K4=key-four\nGEMINI_API_KEY=key-five\n", encoding="utf-8")
        pool = GeminiKeyPool(active_file=keyfile)
        assert pool.key_count == 2
        _, key = pool.acquire()
        assert key == "key-four"

    def test_repr_never_leaks_keys(self) -> None:
        pool = GeminiKeyPool(keys=["super-secret-key", "another-secret"])
        assert "super-secret-key" not in repr(pool)
        assert "another-secret" not in repr(pool)

    def test_tracks_failures(self) -> None:
        pool = GeminiKeyPool(keys=["k1", "k2"])
        idx, _ = pool.acquire()
        pool.mark_failed(idx)
        assert pool.failures(idx) == 1
        pool.mark_success(idx)
        assert pool.failures(idx) == 0


class TestGeminiTranslationProvider:
    def test_success_produces_draft_without_network(self) -> None:
        pool = GeminiKeyPool(keys=["fake-key"])
        provider = GeminiTranslationProvider(pool, max_retries=1)
        source = _source()
        body = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "# Привет"}]}}]}
        ).encode("utf-8")
        with mock.patch(
            "urllib.request.urlopen",
            return_value=_response(body),
        ) as opener:
            drafts = provider.translate([source], "ru")
        assert len(drafts) == 1
        assert drafts[0].document_id == source.document_id
        assert drafts[0].target_locale == "ru"
        assert drafts[0].status.value == "draft"
        assert drafts[0].provider == "gemini"
        # URL includes model, but never the plaintext key in any structured log.
        assert opener.call_count == 1

    def test_failover_advances_pool_then_succeeds(self) -> None:
        pool = GeminiKeyPool(keys=["bad", "good"])
        provider = GeminiTranslationProvider(pool, max_retries=3)

        # Simulate by failing key 0 ("bad") with a retryable status, then key 1 succeeds.
        from urllib.error import HTTPError

        def opener(request, *args, **kwargs):
            if request.full_url.find("key=bad") != -1:
                raise HTTPError(
                    request.full_url, 429, "Rate Limited", {},
                    __import__("io").BytesIO(b"{)"),
                )
            body = json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "переведено"}]}}]}
            ).encode("utf-8")
            return _response(body)

        with mock.patch("urllib.request.urlopen", side_effect=opener):
            drafts = provider.translate([_source()], "ru")
        assert drafts[0].status.value == "draft"
        assert drafts[0].text == "переведено"
        # rotation should have moved off key 0
        idx, key = pool.acquire()
        assert idx == 1
        assert key == "good"

    def test_exhausts_keys_then_raises(self) -> None:
        from urllib.error import HTTPError
        import io

        pool = GeminiKeyPool(keys=["k1", "k2"])
        provider = GeminiTranslationProvider(pool, max_retries=1)

        def opener(request, *args, **kwargs):
            raise HTTPError(request.full_url, 500, "Server", {}, io.BytesIO(b"{)"))

        with mock.patch("urllib.request.urlopen", side_effect=opener):
            with pytest.raises(RuntimeError):
                provider.translate([_source()], "ru")

    def test_strips_fence_markers_from_answer(self) -> None:
        pool = GeminiKeyPool(keys=["k"])
        provider = GeminiTranslationProvider(pool, max_retries=1)
        raw = "```markdown\n# Привет\n```"
        body = json.dumps({"candidates": [{"content": {"parts": [{"text": raw}]}}]}).encode("utf-8")
        with mock.patch(
            "urllib.request.urlopen",
            return_value=_response(body),
        ):
            drafts = provider.translate([_source()], "ru")
        assert drafts[0].text == "# Привет"

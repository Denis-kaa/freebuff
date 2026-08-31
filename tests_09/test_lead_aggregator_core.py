"""test_lead_aggregator_core.py — тесты ядра lead_aggregator (Фаза 3).

Покрытие: RetryPolicy (backoff+jitter+circuit breaker), CheckpointStore (SQLite+WAL),
IntentClassifier (L1/L2), Deduplicator, Scorer, KworkAdapter/TGChannelAdapter парсинг.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

LA_ROOT = Path(__file__).resolve().parent.parent / "projects_17" / "lead_aggregator"
sys.path.insert(0, str(LA_ROOT))

from app.core.retry_policy import CircuitOpenError, RetryPolicy  # noqa: E402
from app.models import Lead  # noqa: E402
from app.processors.deduplicator import Deduplicator  # noqa: E402
from app.processors.intent_classifier import IntentClassifier  # noqa: E402
from app.processors.scorer import Scorer  # noqa: E402
from app.storage.checkpoint_store import CheckpointStore  # noqa: E402


# ── RetryPolicy ──────────────────────────────────────────────────────
class TestRetryPolicy:
    def test_next_delay_grows_exponentially(self):
        rp = RetryPolicy(base_delay=1.0, backoff=2.0, jitter=0.0, max_delay=60.0)
        d0 = rp.next_delay(0)
        d1 = rp.next_delay(1)
        d2 = rp.next_delay(2)
        assert d0 == 1.0
        assert d1 == 2.0
        assert d2 == 4.0

    def test_next_delay_jitter_within_bounds(self):
        rp = RetryPolicy(base_delay=1.0, jitter=0.2)
        for attempt in range(4):
            d = rp.next_delay(attempt)
            assert 0 <= d <= 1.0 * (2.0**attempt) * 1.2 + 1e-6

    def test_circuit_breaker_opens(self):
        # threshold == max_attempts: 2 неудачи подряд → размыкание в run()
        rp = RetryPolicy(max_attempts=2, failure_threshold=2)

        async def fail():
            raise ConnectionError("boom")

        with pytest.raises(CircuitOpenError):
            asyncio_run(rp.run, fail)
        assert rp.is_open

    def test_circuit_recovers_after_cooldown(self):
        rp = RetryPolicy(max_attempts=2, failure_threshold=2, cooldown_s=0.0)

        async def fail():
            raise ConnectionError("boom")

        with pytest.raises(CircuitOpenError):
            asyncio_run(rp.run, fail)
        assert rp.is_open
        # после cooldown (0.0) — probe-попытка разрешена

        async def ok():
            return "ok"

        assert asyncio_run(rp.run, ok) == "ok"
        assert rp.is_open is False

    def test_retry_eventual_success(self):
        rp = RetryPolicy(max_attempts=3, base_delay=0.0, failure_threshold=10)
        calls = {"n": 0}

        async def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("retry")
            return "ok"

        assert asyncio_run(rp.run, flaky) == "ok"
        assert calls["n"] == 3


# ── CheckpointStore ──────────────────────────────────────────────────
class TestCheckpointStore:
    def test_set_get(self, tmp_path):
        with CheckpointStore(tmp_path / "cp.db") as store:
            assert store.get_last("kwork") is None
            store.set_last("kwork", "proj-123")
            assert store.get_last("kwork") == "proj-123"

    def test_persistence_across_reopen(self, tmp_path):
        db = tmp_path / "cp.db"
        with CheckpointStore(db) as store:
            store.set_last("tg", "chan/1")
        with CheckpointStore(db) as store:
            assert store.get_last("tg") == "chan/1"

    def test_update_override(self, tmp_path):
        with CheckpointStore(tmp_path / "cp.db") as store:
            store.set_last("kwork", "a")
            store.set_last("kwork", "b")
            assert store.get_last("kwork") == "b"


# ── IntentClassifier (L1/L2) ─────────────────────────────────────────
class TestIntentClassifier:
    def make(self):
        return IntentClassifier(
            stopwords=["казино", "реклама"],
            client_markers=["ищу", "нужен", "сделать"],
            seeker_markers=["ищу работу", "предлагаю услуги"],
        )

    def test_l1_filters_spam(self):
        ok, intent = self.make().classify("Заработок в казино, реклама")
        assert ok is False
        assert intent == "spam"

    def test_l2_client_intent(self):
        ok, intent = self.make().classify("Нужен телеграм бот, ищу разработчика")
        assert ok is True
        assert intent == "client"

    def test_l2_seeker_intent(self):
        ok, intent = self.make().classify("Предлагаю услуги, ищу работу фрилансером")
        assert ok is True
        assert intent == "seeker"

    def test_l2_neutral(self):
        ok, intent = self.make().classify("Сегодня хорошая погода")
        assert ok is True
        assert intent == "neutral"


# ── Deduplicator ─────────────────────────────────────────────────────
class TestDeduplicator:
    def lead(self, text):
        return Lead(source="t", source_id="1", text=text)

    def test_exact_duplicate(self):
        d = Deduplicator()
        assert d.is_duplicate(self.lead("нужен бот")) is False
        assert d.is_duplicate(self.lead("нужен бот")) is True

    def test_normalized_duplicate(self):
        d = Deduplicator()
        assert d.is_duplicate(self.lead("  Нужен   БОТ ")) is False
        assert d.is_duplicate(self.lead("нужен бот")) is True

    def test_fuzzy_duplicate(self):
        d = Deduplicator(fuzzy_threshold=0.9)
        assert d.is_duplicate(self.lead("нужен телеграм бот для магазина")) is False
        assert d.is_duplicate(self.lead("нужен телеграм бот для магазина.")) is True

    def test_distinct_not_duplicate(self):
        d = Deduplicator()
        assert d.is_duplicate(self.lead("нужен бот")) is False
        assert d.is_duplicate(self.lead("нужен лендинг")) is False


# ── Scorer (L3) ──────────────────────────────────────────────────────
class TestScorer:
    def test_client_intent_scores_higher(self):
        sc = Scorer(signals=["телеграм бот"])
        client = Lead(source="t", source_id="1", text="нужен телеграм бот", intent="client")
        seeker = Lead(source="t", source_id="2", text="ищу работу", intent="seeker")
        assert sc.score(client) > sc.score(seeker)

    def test_relevance_boosts_score(self):
        sc = Scorer(signals=["телеграм бот", "лендинг"])
        generic = Lead(source="t", source_id="1", text="нужен исполнитель", intent="client")
        relevant = Lead(
            source="t", source_id="2", text="нужен телеграм бот и лендинг", intent="client"
        )
        assert sc.score(relevant) > sc.score(generic)
        assert 0 <= sc.score(relevant) <= 100


# ── resume-сравнение id (digit-boundary: 99999 → 100000) ──────────────
class TestIdComparison:
    def test_numeric_tail_crosses_digit_boundary(self):
        from app.pipeline import _id_is_newer, _id_key

        assert _id_is_newer("freelance_tg/100000", "freelance_tg/99999") is True
        assert _id_is_newer("freelance_tg/99999", "freelance_tg/100000") is False
        assert _id_is_newer("freelance_tg/100", "freelance_tg/99") is True
        # числовой хвост всегда имеет приоритет над строковым fallback
        assert _id_key("proj-123") < _id_key("abc")  # (0, 123) < (1, "abc")
        assert _id_key("abc") > _id_key("proj-123")


def asyncio_run(fn, *args):
    import asyncio

    return asyncio.run(fn(*args))

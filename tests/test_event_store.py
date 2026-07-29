"""
Unit тесты для Event Platform: Event Store, Replay, Timeline, Audit, Pulse.

Основание: docs/EVENT_PLATFORM_SPECIFICATION.md §11
~60 тестов
"""

from __future__ import annotations

import json
import os
import tempfile
***REMOVED***
from typing import Any, Dict, Generator, List

import pytest

from freebuff_plugin.event import (
    AuditAction,
    AuditConfigChange,
    AuditDecision,
    AuditEntry,
    EventEntry,
    EventQuery,
    PulseEntry,
    Timeline,
    TimelineEntry,
    get_event_icon,
)
from freebuff_plugin.event.store import EventStore
from freebuff_plugin.event.replay import EventReplay, ReplayResult, RebuildResult
from freebuff_plugin.event.timeline import TimelineEngine
from freebuff_plugin.event.audit import AuditEngine
from freebuff_plugin.event.pulse import PulseEngine


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_db() -> Generator[Path, None, None***REMOVED***:
    """Временная БД для тестов."""
    tmp = tempfile.mktemp(suffix=".db", prefix="event_store_test_")
    yield Path(tmp)
    if Path(tmp).exists():
        Path(tmp).unlink(missing_ok=True)


@pytest.fixture
def store(tmp_db: Path) -> EventStore:
    """EventStore с временной БД."""
    return EventStore(db_path=tmp_db)


@pytest.fixture
def populated_store(store: EventStore) -> EventStore:
    """EventStore с тестовыми данными."""
    _populate(store)
    return store


def _populate(s: EventStore) -> None:
    """Наполняет EventStore тестовыми событиями."""
    events = [
        {"event_type": "system.startup", "source": "system",
         "data": {"version": "4.6.0"***REMOVED******REMOVED***,
        {"event_type": "session.created", "source": "context_manager",
         "data": {"topic": "Code Review"***REMOVED***, "session_id": "sess-001"***REMOVED***,
        {"event_type": "task.created", "source": "orchestrator",
         "data": {"task_id": "t-001"***REMOVED***, "correlation_id": "corr-001",
         "session_id": "sess-001"***REMOVED***,
        {"event_type": "step.started", "source": "orchestrator",
         "data": {"step_id": "s1", "description": "Analyze code"***REMOVED***,
         "correlation_id": "corr-001", "session_id": "sess-001"***REMOVED***,
        {"event_type": "step.completed", "source": "orchestrator",
         "data": {"step_id": "s1", "duration_ms": 500***REMOVED***,
         "correlation_id": "corr-001", "session_id": "sess-001"***REMOVED***,
        {"event_type": "task.completed", "source": "orchestrator",
         "data": {"task_id": "t-001", "duration_ms": 1200***REMOVED***,
         "correlation_id": "corr-001", "session_id": "sess-001"***REMOVED***,
        {"event_type": "session.completed", "source": "context_manager",
         "data": {***REMOVED***, "session_id": "sess-001"***REMOVED***,
        {"event_type": "system.error", "source": "system",
         "data": {"error": "OOM detected"***REMOVED******REMOVED***,
        {"event_type": "memory.stored", "source": "memory_engine",
         "data": {"key": "project_config", "level": "project", "content": "Important config data"***REMOVED***,
         "session_id": "sess-001"***REMOVED***,
        {"event_type": "knowledge.indexed", "source": "knowledge_engine",
         "data": {"doc_id": "mem_project_config", "source": "memory/project/project_config"***REMOVED******REMOVED***,
    ***REMOVED***
    for ev in events:
        s.store(**ev)


# ═══════════════════════════════════════════════════════════════
# 1. Event Store: CRUD
# ═══════════════════════════════════════════════════════════════


class TestEventStoreCRUD:
    """EventStore: store, get_by_id, query — 4 теста"""

    def test_store_and_get_by_id(self, store: EventStore):
        """store и get_by_id."""
        event_id = store.store(
            event_type="test.event",
            source="test",
            data={"message": "hello"***REMOVED***,
            correlation_id="corr-1",
        )
        assert event_id is not None
        assert len(event_id) == 12  # uuid4 hex[:12***REMOVED***

        entry = store.get_by_id(event_id)
        assert entry is not None
        assert entry.event_type == "test.event"
        assert entry.data["message"***REMOVED*** == "hello"

    def test_store_duplicate_event(self, store: EventStore):
        """INSERT OR IGNORE — дубликаты игнорируются."""
        eid = store.store(event_type="test.dup", source="test")
        store.store(event_type="test.dup", source="test", event_id=eid)

        result = store.query(EventQuery(event_type="test.dup"))
        assert len(result) == 1

    def test_get_by_id_not_found(self, store: EventStore):
        """get_by_id возвращает None для несуществующего ID."""
        entry = store.get_by_id("nonexistent")
        assert entry is None

    def test_store_minimal(self, store: EventStore):
        """store с минимальными параметрами."""
        eid = store.store(event_type="minimal.event")
        assert eid is not None

        entry = store.get_by_id(eid)
        assert entry is not None
        assert entry.source == ""
        assert entry.data == {***REMOVED***


class TestEventStoreQuery:
    """EventStore: query — 8 тестов"""

    def test_query_by_type_exact(self, populated_store: EventStore):
        """Точное совпадение event_type."""
        result = populated_store.query(EventQuery(event_type="system.startup"))
        assert len(result) == 1

    def test_query_by_type_wildcard(self, populated_store: EventStore):
        """Wildcard: task.* → task.created, task.completed."""
        result = populated_store.query(EventQuery(event_type="task.*"))
        assert len(result) == 2

    def test_query_by_type_all_wildcard(self, populated_store: EventStore):
        """Wildcard: * → все события."""
        result = populated_store.query(EventQuery(event_type="*"))
        assert len(result) == 10

    def test_query_by_source(self, populated_store: EventStore):
        """Фильтр по source."""
        result = populated_store.query(EventQuery(source="orchestrator"))
        assert len(result) == 4  # task.created, step.started, step.completed, task.completed
        assert all(e.source == "orchestrator" for e in result)

    def test_query_by_session(self, populated_store: EventStore):
        """Фильтр по session_id."""
        result = populated_store.query(EventQuery(session_id="sess-001"))
        # 7 events with session_id=sess-001
        assert len(result) >= 6
        assert all(e.session_id == "sess-001" for e in result)

    def test_query_by_correlation(self, populated_store: EventStore):
        """Фильтр по correlation_id."""
        result = populated_store.query(EventQuery(correlation_id="corr-001"))
        assert len(result) == 4  # task, step.started, step.completed, task.completed
        assert all(e.correlation_id == "corr-001" for e in result)

    def test_query_with_limit(self, populated_store: EventStore):
        """Лимит записей."""
        result = populated_store.query(EventQuery(limit=3))
        assert len(result) <= 3

    def test_query_with_offset(self, populated_store: EventStore):
        """Offset + limit."""
        first = populated_store.query(EventQuery(limit=3, order="asc"))
        second = populated_store.query(EventQuery(limit=3, offset=3, order="asc"))
        assert len(first) == 3
        assert len(second) >= 1
        # Убеждаемся что это разные записи
        first_ids = {e.event_id for e in first***REMOVED***
        second_ids = {e.event_id for e in second***REMOVED***
        assert first_ids.isdisjoint(second_ids)


class TestEventStoreTimeRange:
    """EventStore: временной диапазон — 3 теста"""

    def test_query_since(self, populated_store: EventStore):
        """Фильтр since."""
        # Все события имеют timestamp, since пустая строка
        result = populated_store.query(EventQuery(since="2000-01-01"))
        assert len(result) == 10

    def test_query_until(self, populated_store: EventStore):
        """Фильтр until."""
        result = populated_store.query(EventQuery(until="2100-01-01"))
        assert len(result) == 10

    def test_query_since_until(self, populated_store: EventStore):
        """since + until."""
        result = populated_store.query(
            EventQuery(since="2000-01-01", until="2100-01-01")
        )
        assert len(result) == 10


class TestEventStoreBatch:
    """EventStore: batch — 2 теста"""

    def test_store_batch(self, store: EventStore):
        """Batch сохранение."""
        events = [
            {"event_type": "batch.1", "data": {"n": 1***REMOVED******REMOVED***,
            {"event_type": "batch.2", "data": {"n": 2***REMOVED******REMOVED***,
            {"event_type": "batch.3", "data": {"n": 3***REMOVED******REMOVED***,
        ***REMOVED***
        count = store.store_batch(events)
        assert count >= 1

        result = store.query(EventQuery(event_type="batch.*"))
        assert len(result) == 3

    def test_store_batch_empty(self, store: EventStore):
        """Пустой batch."""
        count = store.store_batch([***REMOVED***)
        assert count == 0


class TestEventStoreSearch:
    """EventStore: FTS5 поиск — 3 теста"""

    def test_search_basic(self, populated_store: EventStore):
        """FTS5: поиск по data_json."""
        result = populated_store.query(
            EventQuery(data_search="config")
        )
        # Должен найти "project_config" и "Important config data"
        assert len(result) >= 1

    def test_search_no_match(self, populated_store: EventStore):
        """FTS5: нет совпадений."""
        result = populated_store.query(
            EventQuery(data_search="zzz_nonexistent_zzz")
        )
        assert len(result) == 0

    def test_search_with_type_filter(self, populated_store: EventStore):
        """FTS5 + фильтр по event_type."""
        result = populated_store.query(
            EventQuery(data_search="config", event_type="memory.*")
        )
        assert len(result) >= 1
        assert all("memory." in e.event_type for e in result)


class TestEventStoreAggregation:
    """EventStore: aggregation — 3 теста"""

    def test_count_by_type(self, populated_store: EventStore):
        """count_by_type."""
        counts = populated_store.count_by_type()
        assert "task.created" in counts
        assert counts["task.created"***REMOVED*** == 1
        assert counts["task.completed"***REMOVED*** == 1

    def test_count_by_type_since(self, populated_store: EventStore):
        """count_by_type с since."""
        counts = populated_store.count_by_type(since="2000-01-01")
        assert len(counts) >= 1

    def test_get_stats(self, populated_store: EventStore):
        """get_stats."""
        stats = populated_store.get_stats()
        assert stats["total_events"***REMOVED*** >= 10
        assert stats["unique_types"***REMOVED*** >= 8
        assert stats["fts_indexed"***REMOVED*** >= 1


class TestEventStoreClear:
    """EventStore: clear — 1 тест"""

    def test_clear(self, populated_store: EventStore):
        """clear удаляет все данные."""
        assert populated_store.get_stats()["total_events"***REMOVED*** > 0
        count = populated_store.clear()
        assert count > 0
        assert populated_store.get_stats()["total_events"***REMOVED*** == 0


class TestEventStoreMigration:
    """EventStore: миграция — 2 теста"""

    def test_migrate_no_old_db(self, store: EventStore, tmp_path: Path):
        """Миграция без старой БД."""
        count = store.migrate_from_event_log(tmp_path / "nonexistent.db")
        assert count == 0

    def test_migrate_from_event_log(self, tmp_path: Path, store: EventStore):
        """Миграция из event_log."""
        old_db = tmp_path / "old_events.db"
        import sqlite3
        old_conn = sqlite3.connect(str(old_db))
        old_conn.execute(
            "CREATE TABLE IF NOT EXISTS event_log ("
            "event_id TEXT PRIMARY KEY, event_type TEXT, source TEXT, "
            "data_json TEXT, timestamp TEXT, delivered_to INTEGER DEFAULT 0"
            ")"
        )
        old_conn.execute(
            "INSERT INTO event_log (event_id, event_type, source, data_json, timestamp) "
            "VALUES ('legacy-1', 'test.legacy', 'legacy', '{\"msg\": \"old\"***REMOVED***', '2025-01-01T00:00:00')"
        )
        old_conn.commit()
        old_conn.close()

        count = store.migrate_from_event_log(old_db)
        assert count == 1

        # Проверяем что данные перенесены
        entries = store.query(EventQuery(event_type="test.legacy"))
        assert len(entries) == 1
        assert entries[0***REMOVED***.data["msg"***REMOVED*** == "old"


# ═══════════════════════════════════════════════════════════════
# 2. Event Replay
# ═══════════════════════════════════════════════════════════════


class TestEventReplay:
    """EventReplay — 5 тестов"""

    def test_replay_basic(self, populated_store: EventStore):
        """replay: базовое воспроизведение."""
        replay = EventReplay(populated_store)
        result = replay.replay(EventQuery(event_type="task.*"))
        assert isinstance(result, ReplayResult)
        assert result.total_events == 2
        assert result.delivered == 0  # нет handler
        assert result.errors == 0

    def test_replay_with_handler(self, populated_store: EventStore):
        """replay: с handler."""
        processed = [***REMOVED***

        def handler(event):
            processed.append(event.event_type)

        replay = EventReplay(populated_store)
        result = replay.replay(
            EventQuery(event_type="task.*"),
            handler=handler,
        )
        assert result.delivered == 2
        assert "task.created" in processed
        assert "task.completed" in processed

    def test_replay_session(self, populated_store: EventStore):
        """replay_session."""
        replay = EventReplay(populated_store)
        result = replay.replay_session("sess-001")
        assert result.total_events >= 6

    def test_replay_workflow(self, populated_store: EventStore):
        """replay_workflow."""
        replay = EventReplay(populated_store)
        result = replay.replay_workflow("corr-001")
        assert result.total_events == 4

    def test_replay_empty(self, store: EventStore):
        """replay с пустым результатом."""
        replay = EventReplay(store)
        result = replay.replay(EventQuery(event_type="nonexistent"))
        assert result.total_events == 0
        assert result.delivered == 0


class TestEventReplayRebuild:
    """EventReplay: rebuild — 3 теста"""

    def test_rebuild_basic(self, populated_store: EventStore):
        """rebuild: базовая перестройка."""
        replay = EventReplay(populated_store)
        processed = [***REMOVED***

        def process(event):
            processed.append(event.event_type)

        result = replay.rebuild(
            target="memory_engine",
            process_func=process,
        )
        assert isinstance(result, RebuildResult)
        assert result.target == "memory_engine"
        assert result.events_processed >= 1  # memory.stored

    def test_rebuild_with_clear(self, populated_store: EventStore):
        """rebuild: с clear_func."""
        cleared = [***REMOVED***

        def clear_func():
            cleared.append("cleared")

        replay = EventReplay(populated_store)
        result = replay.rebuild(
            target="memory_engine",
            clear_func=clear_func,
        )
        assert len(cleared) == 1

    def test_rebuild_with_filter(self, populated_store: EventStore):
        """rebuild: с event_filter."""
        replay = EventReplay(populated_store)

        def only_completed(event):
            return "completed" in event.event_type

        processed = [***REMOVED***

        def process(event):
            processed.append(event.event_type)

        result = replay.rebuild(
            target="memory_engine",
            process_func=process,
            event_filter=only_completed,
        )
        assert all("completed" in t for t in processed)


# ═══════════════════════════════════════════════════════════════
# 3. Timeline
# ═══════════════════════════════════════════════════════════════


class TestTimeline:
    """TimelineEngine — 5 тестов"""

    def test_get_timeline(self, populated_store: EventStore):
        """get_timeline."""
        timeline = TimelineEngine(populated_store)
        result = timeline.get_timeline()
        assert isinstance(result, Timeline)
        assert result.total >= 10

    def test_timeline_entries_format(self, populated_store: EventStore):
        """TimelineEntry форматирование."""
        timeline = TimelineEngine(populated_store)
        result = timeline.get_timeline(limit=5)
        for entry in result.entries:
            assert isinstance(entry, TimelineEntry)
            assert entry.icon != ""
            assert entry.title != ""

    def test_timeline_by_session(self, populated_store: EventStore):
        """get_timeline_by_session."""
        timeline = TimelineEngine(populated_store)
        result = timeline.get_timeline_by_session("sess-001")
        assert result.total >= 6
        assert all(e.session_id == "sess-001" for e in result.entries)

    def test_timeline_by_user(self, populated_store: EventStore):
        """get_timeline_by_user."""
        timeline = TimelineEngine(populated_store)
        result = timeline.get_timeline_by_user("test_user", limit=10)
        # нет событий от test_user
        assert result.total == 0

    def test_timeline_search(self, populated_store: EventStore):
        """search_timeline."""
        timeline = TimelineEngine(populated_store)
        result = timeline.search_timeline("config")
        assert result.total >= 1


class TestTimelineIcons:
    """Timeline icons — 2 теста"""

    def test_get_event_icon_exact(self):
        """Точное совпадение."""
        assert get_event_icon("system.startup") == "🚀"
        assert get_event_icon("task.completed") == "✅"
        assert get_event_icon("memory.stored") == "💾"

    def test_get_event_icon_wildcard(self):
        """Wildcard fallback — если нет точного совпадения и нет wildcard."""
        # task.xxx не имеет task.* в EVENT_ICONS, возвращает 📌
        assert get_event_icon("task.unknown") == "📌"
        assert get_event_icon("unknown.event") == "📌"


class TestTimelineFormatting:
    """Timeline форматирование — 2 теста"""

    def test_format_timeline_text(self, populated_store: EventStore):
        """format_timeline_text."""
        timeline = TimelineEngine(populated_store)
        result = timeline.get_timeline(limit=3)
        text = timeline.format_timeline_text(result)
        assert len(text) > 0
        assert any(icon in text for icon in ["🚀", "▶️", "📋", "✅", "🔄", "💾", "📚", "📌"***REMOVED***)


    def test_format_timeline_empty(self, store: EventStore):
        """Пустая временная шкала."""
        timeline = TimelineEngine(store)
        result = timeline.get_timeline()
        assert result.total == 0
        text = timeline.format_timeline_text(result)
        assert "Нет событий" in text


# ═══════════════════════════════════════════════════════════════
# 4. Audit
# ═══════════════════════════════════════════════════════════════


class TestAuditEngine:
    """AuditEngine — 6 тестов"""

    def test_log_decision(self, store: EventStore):
        """log_decision."""
        audit = AuditEngine(store)
        decision = AuditDecision(
            policy_name="review-default",
            capability="review",
            runtime_selected="claude-code",
            model_selected="claude-3.5-sonnet",
            cost_estimate=0.02,
            context={"correlation_id": "corr-audit-1"***REMOVED***,
        )
        event_id = audit.log_decision(decision)
        assert event_id is not None

        # Проверяем что сохранено
        entry = store.get_by_id(event_id)
        assert entry is not None
        assert entry.event_type == "audit.decision"

    def test_log_action(self, store: EventStore):
        """log_action."""
        audit = AuditEngine(store)
        action = AuditAction(
            actor="user",
            action="policy.override",
            target="default_runtime",
            before="claude-code",
            after="freebuff",
        )
        event_id = audit.log_action(action)
        assert event_id is not None

        entry = store.get_by_id(event_id)
        assert entry.event_type == "audit.action"

    def test_log_config_change(self, store: EventStore):
        """log_config_change."""
        audit = AuditEngine(store)
        change = AuditConfigChange(
            component="policy_engine",
            setting="default_runtime",
            old_value="claude-code",
            new_value="freebuff",
            changed_by="user",
            version=2,
        )
        event_id = audit.log_config_change(change)
        assert event_id is not None

        entry = store.get_by_id(event_id)
        assert entry.event_type == "audit.config_change"

    def test_get_audit_trail(self, store: EventStore):
        """get_audit_trail."""
        audit = AuditEngine(store)
        audit.log_decision(AuditDecision(
            policy_name="default",
            capability="coding",
            runtime_selected="freebuff",
        ))
        audit.log_action(AuditAction(
            actor="user", action="override", target="runtime"
        ))

        trail = audit.get_audit_trail()
        assert len(trail) == 2
        assert all(isinstance(e, AuditEntry) for e in trail)

    def test_search_audit(self, store: EventStore):
        """search_audit."""
        audit = AuditEngine(store)
        audit.log_decision(AuditDecision(
            policy_name="review-pro",
            capability="review",
            runtime_selected="claude-code",
        ))

        result = audit.search_audit("review")
        assert len(result) >= 1

    def test_format_audit_entry(self, store: EventStore):
        """format_audit_entry."""
        audit = AuditEngine(store)
        decision = AuditDecision(
            policy_name="test-policy",
            capability="testing",
            runtime_selected="freebuff",
            cost_estimate=0.01,
        )
        audit.log_decision(decision)

        trail = audit.get_audit_trail()
        assert len(trail) >= 1

        text = audit.format_audit_entry(trail[0***REMOVED***)
        assert "DECISION" in text
        assert "test-policy" in text


# ═══════════════════════════════════════════════════════════════
# 5. Pulse
# ═══════════════════════════════════════════════════════════════


class TestPulseEngine:
    """PulseEngine — 4 теста"""

    def test_pulse_init(self, store: EventStore):
        """Инициализация PulseEngine."""
        pulse = PulseEngine(bus=None, store=store)
        assert not pulse._running

    def test_pulse_get_empty(self, store: EventStore):
        """get_pulse с пустым store."""
        pulse = PulseEngine(bus=None, store=store)
        feed = pulse.get_pulse(limit=10)
        assert isinstance(feed, list)
        assert len(feed) == 0

    def test_pulse_get_with_data(self, store: EventStore):
        """get_pulse с данными — использует fallback поиск по категориям."""
        # Сохраняем тестовые события через _on_event симуляцию
        # (добавляет _pulse=True в data)
        store.store(
            event_type="task.completed",
            source="orchestrator",
            data={"task_id": "t-001", "duration_ms": 500, "_pulse": True***REMOVED***,
            session_id="sess-001",
        )
        store.store(
            event_type="memory.stored",
            source="memory_engine",
            data={"key": "note", "level": "session", "_pulse": True***REMOVED***,
            session_id="sess-001",
        )

        pulse = PulseEngine(bus=None, store=store)
        feed = pulse.get_pulse(limit=10)
        assert len(feed) >= 2
        assert all(isinstance(e, PulseEntry) for e in feed)

    def test_pulse_entry_format(self, store: EventStore):
        """Формат PulseEntry."""
        store.store(
            event_type="task.completed",
            source="orchestrator",
            data={"task_id": "t-done", "duration_ms": 1200, "_pulse": True***REMOVED***,
        )

        pulse = PulseEngine(bus=None, store=store)
        feed = pulse.get_pulse(limit=5)
        assert len(feed) >= 1
        entry = feed[0***REMOVED***
        assert entry.icon != ""
        assert entry.title != ""
        assert entry.severity in ("info", "success", "warning", "error")


# ═══════════════════════════════════════════════════════════════
# 6. Integration Tests
# ═══════════════════════════════════════════════════════════════


class TestEventPlatformIntegration:
    """Интеграционные тесты — 4 теста"""

    def test_store_query_cycle(self, store: EventStore):
        """Полный цикл: store → query → get_by_id."""
        eid = store.store(
            event_type="integration.test",
            source="test",
            data={"step": 1, "value": "hello"***REMOVED***,
            correlation_id="int-corr",
            session_id="int-sess",
            project="test-project",
        )
        assert eid is not None

        # Query
        results = store.query(EventQuery(
            event_type="integration.test",
            project="test-project",
        ))
        assert len(results) == 1

        # get_by_id
        entry = store.get_by_id(eid)
        assert entry is not None
        assert entry.data["value"***REMOVED*** == "hello"

    def test_audit_timeline_integration(self, store: EventStore):
        """Audit + Timeline: запись и отображение."""
        # Audit
        audit = AuditEngine(store)
        audit.log_decision(AuditDecision(
            policy_name="integ-test",
            capability="testing",
            runtime_selected="freebuff",
        ))

        # Timeline
        timeline = TimelineEngine(store)
        result = timeline.get_timeline()
        assert result.total >= 1

        # Проверяем что audit событие отображается
        assert any("audit.decision" in e.event_type for e in result.entries)

    def test_replay_timeline(self, populated_store: EventStore):
        """Replay + Timeline: воспроизведение и шкала."""
        replay = EventReplay(populated_store)
        replay.replay(EventQuery(event_type="system.*"))

        timeline = TimelineEngine(populated_store)
        result = timeline.get_timeline()
        assert result.total >= 10

    def test_boundary_empty_store(self, store: EventStore):
        """EventStore без данных — все операции корректны."""
        assert store.get_by_id("fake") is None
        assert store.query(EventQuery(limit=10)) == [***REMOVED***
        assert store.count_by_type() == {***REMOVED***
        stats = store.get_stats()
        assert stats["total_events"***REMOVED*** == 0


# ═══════════════════════════════════════════════════════════════
# 7. Boundary Tests
# ═══════════════════════════════════════════════════════════════


class TestBoundary:
    """Boundary тесты — 4 теста"""

    def test_large_data_json(self, store: EventStore):
        """Большой data_json."""
        large_data = {"key": "x" * 10000***REMOVED***
        eid = store.store(
            event_type="test.large",
            source="test",
            data=large_data,
        )
        entry = store.get_by_id(eid)
        assert entry is not None
        assert len(entry.data["key"***REMOVED***) == 10000

    def test_many_event_types(self, store: EventStore):
        """Много разных типов событий."""
        for i in range(20):
            store.store(event_type=f"test.type{i***REMOVED***", source="test")
        counts = store.count_by_type()
        assert len(counts) == 20

    def test_query_order_asc(self, store: EventStore):
        """Сортировка asc."""
        for i in range(5):
            import time
            time.sleep(0.01)
            store.store(event_type="test.order", data={"i": i***REMOVED***)

        result = store.query(EventQuery(event_type="test.order", order="asc"))
        assert len(result) == 5
        # Проверяем что по возрастанию
        for i, e in enumerate(result):
            assert e.data["i"***REMOVED*** == i

    def test_query_order_desc(self, store: EventStore):
        """Сортировка desc."""
        for i in range(5):
            import time
            time.sleep(0.01)
            store.store(event_type="test.order", data={"i": i***REMOVED***)

        result = store.query(EventQuery(event_type="test.order", order="desc"))
        assert len(result) == 5
        # Проверяем что по убыванию
        assert result[0***REMOVED***.data["i"***REMOVED*** == 4
        assert result[-1***REMOVED***.data["i"***REMOVED*** == 0

-- Event Store SQLite Schema
-- Версия: 1.0.0
-- Основание: docs/EVENT_PLATFORM_SPECIFICATION.md

-- Core event_store table
CREATE TABLE IF NOT EXISTS event_store (
    event_id        TEXT PRIMARY KEY,
    event_type      TEXT NOT NULL,
    source          TEXT DEFAULT '',
    correlation_id  TEXT DEFAULT '',
    session_id      TEXT DEFAULT '',
    project         TEXT DEFAULT '',
    user_id         TEXT DEFAULT '',
    data_json       TEXT DEFAULT '{***REMOVED***',
    metadata_json   TEXT DEFAULT '{***REMOVED***',
    timestamp       TEXT NOT NULL
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_es_type ON event_store(event_type);
CREATE INDEX IF NOT EXISTS idx_es_correlation ON event_store(correlation_id);
CREATE INDEX IF NOT EXISTS idx_es_session ON event_store(session_id);
CREATE INDEX IF NOT EXISTS idx_es_project ON event_store(project);
CREATE INDEX IF NOT EXISTS idx_es_timestamp ON event_store(timestamp);

-- FTS5 для полнотекстового поиска
-- External content FTS: индекс хранится отдельно, данные из event_store по rowid
CREATE VIRTUAL TABLE IF NOT EXISTS event_fts USING fts5(
    event_id, event_type, data_json,
    content='event_store',
    content_rowid='rowid'
);

-- Триггеры синхронизации FTS5
CREATE TRIGGER IF NOT EXISTS event_fts_ai AFTER INSERT ON event_store BEGIN
    INSERT INTO event_fts(rowid, event_id, event_type, data_json)
    VALUES (new.rowid, new.event_id, new.event_type, new.data_json);
END;

CREATE TRIGGER IF NOT EXISTS event_fts_ad AFTER DELETE ON event_store BEGIN
    INSERT INTO event_fts(event_fts, rowid)
    VALUES ('delete', old.rowid);
END;

CREATE TRIGGER IF NOT EXISTS event_fts_au AFTER UPDATE ON event_store BEGIN
    INSERT INTO event_fts(event_fts, rowid)
    VALUES ('delete', old.rowid);
    INSERT INTO event_fts(rowid, event_id, event_type, data_json)
    VALUES (new.rowid, new.event_id, new.event_type, new.data_json);
END;

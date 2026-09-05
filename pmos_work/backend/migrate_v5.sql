-- ============================================================================
-- migrate_v5.sql — этап 5: Calendar & Events Engine
-- Таблица calendar_events предназначена ПРЕИМУЩЕСТВЕННО для CUSTOM-событий.
-- Системные события не дублируются — CalendarService строит их из источников
-- (5.md §1, §22, §23).
-- ============================================================================

CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_type VARCHAR(30) NOT NULL DEFAULT 'REMINDER',
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ,
    all_day BOOLEAN NOT NULL DEFAULT FALSE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    project_item_id UUID REFERENCES project_items(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    created_by VARCHAR(150),
    recurrence_rule VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Индексы для календарных запросов диапазона (5.md §48)
CREATE INDEX IF NOT EXISTS ix_calendar_events_workspace_id ON calendar_events(workspace_id);
CREATE INDEX IF NOT EXISTS ix_calendar_events_start_at     ON calendar_events(start_at);
CREATE INDEX IF NOT EXISTS ix_calendar_events_project_id   ON calendar_events(project_id);
CREATE INDEX IF NOT EXISTS ix_calendar_events_project_item_id ON calendar_events(project_item_id);
CREATE INDEX IF NOT EXISTS ix_calendar_events_task_id      ON calendar_events(task_id);
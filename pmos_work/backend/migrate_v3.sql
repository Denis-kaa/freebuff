-- Системная миграция этапа 3 (НЕ пользовательские поля).

-- 1. Новые таблицы
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_item_id UUID REFERENCES project_items(id) ON DELETE CASCADE,
    document_type VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'NOT_READY',
    file_name VARCHAR(300),
    storage_key VARCHAR(500),
    uploaded_by VARCHAR(150),
    doc_date DATE,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_item ON documents(project_item_id);

CREATE TABLE IF NOT EXISTS project_events (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_item_id UUID REFERENCES project_items(id) ON DELETE CASCADE,
    event_type VARCHAR(30) NOT NULL,
    event_date DATE,
    title VARCHAR(300),
    description TEXT,
    source VARCHAR(30) DEFAULT 'derived',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_events_project ON project_events(project_id);
CREATE INDEX IF NOT EXISTS idx_events_item ON project_events(project_item_id);

-- 2. Колонки для существующих таблиц
ALTER TABLE projects ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE project_items ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE project_items ADD COLUMN IF NOT EXISTS factory VARCHAR(150);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assignee_name VARCHAR(150);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS project_item_id UUID REFERENCES project_items(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_item ON tasks(project_item_id);

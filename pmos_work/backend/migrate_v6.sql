-- ============================================================================
-- migrate_v6.sql — этап 6: Import / Export Engine
-- ============================================================================

CREATE TABLE IF NOT EXISTS import_mappings (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    source_type VARCHAR(30) NOT NULL DEFAULT 'excel',
    mapping_config JSONB,
    created_by VARCHAR(150),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_import_mappings_workspace_id ON import_mappings(workspace_id);

CREATE TABLE IF NOT EXISTS import_jobs (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source_type VARCHAR(30) NOT NULL,
    file_name VARCHAR(300),
    sheet_name VARCHAR(200),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    duplicate_mode VARCHAR(10) NOT NULL DEFAULT 'update',
    partial BOOLEAN NOT NULL DEFAULT FALSE,
    created_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    preview JSONB,
    errors JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_by VARCHAR(150),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_import_jobs_workspace_id ON import_jobs(workspace_id);
CREATE INDEX IF NOT EXISTS ix_import_jobs_status ON import_jobs(status);

CREATE TABLE IF NOT EXISTS export_presets (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_export_presets_workspace_id ON export_presets(workspace_id);
-- Additive tag storage for projects.
CREATE TABLE IF NOT EXISTS project_tags (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tag VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(project_id, tag)
);
CREATE INDEX IF NOT EXISTS ix_project_tags_workspace ON project_tags(workspace_id, tag);

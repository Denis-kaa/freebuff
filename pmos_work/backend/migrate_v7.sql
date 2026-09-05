-- Этап 7 (7.md §2, §27): расширение представлений.
-- entity_type, view_type, visibility, is_favorite, created_by — аддитивно.

ALTER TABLE views ADD COLUMN IF NOT EXISTS entity_type VARCHAR(30) NOT NULL DEFAULT 'projects';
ALTER TABLE views ADD COLUMN IF NOT EXISTS view_type   VARCHAR(20) NOT NULL DEFAULT 'TABLE';
ALTER TABLE views ADD COLUMN IF NOT EXISTS visibility  VARCHAR(20) NOT NULL DEFAULT 'workspace';
ALTER TABLE views ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN     NOT NULL DEFAULT FALSE;
ALTER TABLE views ADD COLUMN IF NOT EXISTS created_by  VARCHAR(150);

CREATE INDEX IF NOT EXISTS ix_views_entity_type ON views (workspace_id, entity_type);
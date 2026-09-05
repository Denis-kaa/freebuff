-- ============================================================================
-- migrate_v4.sql — этап 4: Dashboard Engine
-- Аддитивные изменения (Additive Architecture): новые колонки, без потери данных.
-- ============================================================================

-- Dashboards: is_default (4.md §20), created_by, version (optimistic locking §44), updated_at
ALTER TABLE dashboards
    ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS created_by UUID,
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- DashboardWidgets: config (настройки §15), layout (grid §16), is_hidden (hide vs delete §9)
ALTER TABLE dashboard_widgets
    ADD COLUMN IF NOT EXISTS config JSONB,
    ADD COLUMN IF NOT EXISTS layout JSONB,
    ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;

-- 1) Единственный default-дашборд на workspace (4.md §20): старейший становится default
UPDATE dashboards d
SET is_default = TRUE
WHERE d.id = (
    SELECT d2.id FROM dashboards d2
    WHERE d2.workspace_id = d.workspace_id
    ORDER BY d2.created_at ASC, d2.id ASC
    LIMIT 1
);

-- 2) Backfill layout из legacy-колонок position ("x,y") + width/height
UPDATE dashboard_widgets w
SET layout = jsonb_build_object(
        'x', COALESCE(
            NULLIF(split_part(COALESCE(w.position, ''), ',', 1), '')::numeric,
            0
        )::int,
        'y', COALESCE(
            NULLIF(split_part(COALESCE(w.position, ''), ',', 2), '')::numeric,
            0
        )::int,
        'w', COALESCE(w.width, 1),
        'h', COALESCE(w.height, 1)
    )
WHERE w.layout IS NULL;

-- 3) config из legacy configuration (если была) — json -> jsonb
UPDATE dashboard_widgets w
SET config = COALESCE(w.config, w.configuration::jsonb)
WHERE w.config IS NULL AND w.configuration IS NOT NULL;

-- 4) Remap legacy widget_type -> современные (Widget Registry aliases)
UPDATE dashboard_widgets SET widget_type = 'today-tasks' WHERE widget_type = 'tasks';
UPDATE dashboard_widgets SET widget_type = 'finance'    WHERE widget_type = 'payments';

-- 5) is_hidden из legacy is_visible (обратная совместимость)
UPDATE dashboard_widgets SET is_hidden = NOT is_visible WHERE is_visible = FALSE;
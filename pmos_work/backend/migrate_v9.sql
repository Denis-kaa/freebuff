-- PM OS Stage 9: RBAC foundation
-- Additive migration. Existing users/workspaces remain intact.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(80) NOT NULL,
    code VARCHAR(40) NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, code)
);

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(120) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, name)
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES workspace_members(id) ON DELETE CASCADE,
    PRIMARY KEY (team_id, member_id)
);

CREATE TABLE IF NOT EXISTS workspace_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role_id UUID NOT NULL REFERENCES roles(id),
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    invited_by UUID REFERENCES users(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS field_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    field_code VARCHAR(160) NOT NULL,
    can_read BOOLEAN NOT NULL DEFAULT FALSE,
    can_update BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (role_id, field_code)
);

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS timezone VARCHAR(80) NOT NULL DEFAULT 'UTC';
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS default_currency VARCHAR(20) NOT NULL DEFAULT 'RUB';
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS working_days JSONB;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS working_hours JSONB;

ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(80) NOT NULL DEFAULT 'UTC';
ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(20) NOT NULL DEFAULT 'ru';
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
UPDATE users SET name = display_name WHERE name IS NULL;

INSERT INTO permissions(code, description) VALUES
('project.read','Read projects'),('project.create','Create projects'),('project.update','Update projects'),('project.delete','Delete projects'),('project.import','Import projects'),('project.bulk_update','Bulk update projects'),
('task.read','Read tasks'),('task.create','Create tasks'),('task.update','Update tasks'),('task.delete','Delete tasks'),('task.bulk_update','Bulk update tasks'),
('production.read','Read production'),('production.update','Update production'),('finance.read','Read finance'),('finance.update','Update finance'),
('document.read','Read documents'),('document.create','Create documents'),('document.update','Update documents'),('document.delete','Delete documents'),
('automation.read','Read automations'),('automation.create','Create automations'),('automation.update','Update automations'),('automation.delete','Delete automations'),
('view.read','Read views'),('view.create','Create views'),('view.update','Update views'),('view.delete','Delete views'),
('workspace.read','Read workspace'),('workspace.update','Update workspace'),('member.read','Read members'),('member.invite','Invite members'),('member.update','Update members'),('member.remove','Remove members'),('role.manage','Manage roles')
ON CONFLICT (code) DO NOTHING;

-- Null workspace_id means a reusable system role template.
INSERT INTO roles(workspace_id,name,code,description,is_system) VALUES
(NULL,'Owner','OWNER','Full workspace access',TRUE),
(NULL,'Admin','ADMIN','Workspace administration',TRUE),
(NULL,'Manager','MANAGER','Operational management',TRUE),
(NULL,'Member','MEMBER','Standard member access',TRUE),
(NULL,'Viewer','VIEWER','Read-only access',TRUE)
ON CONFLICT (workspace_id, code) DO NOTHING;

INSERT INTO role_permissions(role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
WHERE r.workspace_id IS NULL AND r.code = 'OWNER'
ON CONFLICT DO NOTHING;
INSERT INTO role_permissions(role_id, permission_id)
SELECT r.id,p.id FROM roles r JOIN permissions p ON p.code IN (
'project.read','project.create','project.update','project.delete','project.import','project.bulk_update','task.read','task.create','task.update','task.delete','task.bulk_update','production.read','production.update','finance.read','finance.update','document.read','document.create','document.update','document.delete','automation.read','automation.create','automation.update','automation.delete','view.read','view.create','view.update','view.delete','workspace.read','workspace.update','member.read','member.invite','member.update','member.remove','role.manage') WHERE r.workspace_id IS NULL AND r.code='ADMIN' ON CONFLICT DO NOTHING;
INSERT INTO role_permissions(role_id, permission_id)
SELECT r.id,p.id FROM roles r JOIN permissions p ON p.code IN ('project.read','project.create','project.update','task.read','task.create','task.update','production.read','production.update','finance.read','finance.update','document.read','document.create','document.update','view.read','view.create','view.update','automation.read') WHERE r.workspace_id IS NULL AND r.code='MANAGER' ON CONFLICT DO NOTHING;
INSERT INTO role_permissions(role_id, permission_id)
SELECT r.id,p.id FROM roles r JOIN permissions p ON p.code IN ('project.read','task.read','task.create','task.update','production.read','document.read','view.read') WHERE r.workspace_id IS NULL AND r.code='MEMBER' ON CONFLICT DO NOTHING;
INSERT INTO role_permissions(role_id, permission_id)
SELECT r.id,p.id FROM roles r JOIN permissions p ON p.code IN ('project.read','task.read','production.read','document.read','view.read') WHERE r.workspace_id IS NULL AND r.code='VIEWER' ON CONFLICT DO NOTHING;

-- Backfill current single-workspace users into memberships using their legacy role.
INSERT INTO workspace_members(workspace_id,user_id,role_id,status)
SELECT u.workspace_id,u.id, r.id, CASE WHEN u.is_active THEN 'ACTIVE' ELSE 'DEACTIVATED' END
FROM users u JOIN roles r ON r.workspace_id IS NULL AND r.code = CASE WHEN u.role IN ('ADMIN','MANAGER','VIEWER') THEN u.role ELSE 'MEMBER' END
ON CONFLICT (workspace_id,user_id) DO NOTHING;

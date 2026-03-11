-- V011: Workspace-scoped data architecture
-- Makes workspaces the top-level scope for all data and analysis.
-- Workspaces become shared (any member can access), datasets belong to workspaces,
-- interactions track per-user within a workspace.

-- ============================================================================
-- 1. Workspace Members (shared access — replaces user_id ownership)
-- ============================================================================

CREATE TABLE sentinel.workspace_members (
    workspace_id    UUID NOT NULL REFERENCES sentinel.workspaces(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES sentinel.users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL DEFAULT 'member',  -- 'owner' | 'member'
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, user_id)
);

-- Migrate existing workspace ownership into members table (as owner)
INSERT INTO sentinel.workspace_members (workspace_id, user_id, role)
SELECT id, user_id, 'owner'
FROM sentinel.workspaces
WHERE user_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- Replace user_id with created_by (audit trail, not access control)
ALTER TABLE sentinel.workspaces ADD COLUMN created_by UUID REFERENCES sentinel.users(id);
UPDATE sentinel.workspaces SET created_by = user_id;
ALTER TABLE sentinel.workspaces DROP COLUMN user_id;

-- ============================================================================
-- 2. Datasets scoped to workspace (not user)
-- ============================================================================

ALTER TABLE sentinel.datasets ADD COLUMN workspace_id UUID REFERENCES sentinel.workspaces(id) ON DELETE CASCADE;

-- Backfill: assign each dataset to its owner's first workspace
UPDATE sentinel.datasets d
SET workspace_id = (
    SELECT w.id FROM sentinel.workspaces w
    WHERE w.created_by = d.user_id
    ORDER BY w.created_at
    LIMIT 1
)
WHERE d.workspace_id IS NULL;

-- For any orphaned datasets (user has no workspace), create one
DO $$
DECLARE
    r RECORD;
    ws_id UUID;
BEGIN
    FOR r IN
        SELECT DISTINCT d.user_id
        FROM sentinel.datasets d
        WHERE d.workspace_id IS NULL
          AND d.user_id IS NOT NULL
    LOOP
        INSERT INTO sentinel.workspaces (created_by, name)
        VALUES (r.user_id, 'Migrated Data')
        RETURNING id INTO ws_id;

        INSERT INTO sentinel.workspace_members (workspace_id, user_id, role)
        VALUES (ws_id, r.user_id, 'owner');

        UPDATE sentinel.datasets
        SET workspace_id = ws_id
        WHERE user_id = r.user_id AND workspace_id IS NULL;
    END LOOP;
END $$;

-- Now enforce NOT NULL
ALTER TABLE sentinel.datasets ALTER COLUMN workspace_id SET NOT NULL;

-- Keep user_id as uploaded_by (rename for clarity)
ALTER TABLE sentinel.datasets RENAME COLUMN user_id TO uploaded_by;

CREATE INDEX idx_datasets_workspace ON sentinel.datasets(workspace_id);

-- ============================================================================
-- 3. Dataset links scoped to workspace
-- ============================================================================

ALTER TABLE sentinel.dataset_links ADD COLUMN workspace_id UUID REFERENCES sentinel.workspaces(id) ON DELETE CASCADE;

-- Backfill from dataset_a's workspace
UPDATE sentinel.dataset_links dl
SET workspace_id = (
    SELECT d.workspace_id FROM sentinel.datasets d WHERE d.id = dl.dataset_a_id
)
WHERE dl.workspace_id IS NULL;

-- Drop user_id (workspace is the scope now)
ALTER TABLE sentinel.dataset_links DROP COLUMN user_id;

-- Add unique constraint: one link config per workspace pair
-- (A workspace's join config is defined by its dataset_links rows)

CREATE INDEX idx_dataset_links_workspace ON sentinel.dataset_links(workspace_id);

-- ============================================================================
-- 4. Interactions scoped to user within workspace
-- ============================================================================

ALTER TABLE sentinel.workspace_interactions
    ADD COLUMN user_id UUID REFERENCES sentinel.users(id) ON DELETE CASCADE;

-- Drop and recreate PK to include user_id
ALTER TABLE sentinel.workspace_interactions DROP CONSTRAINT workspace_interactions_pkey;

-- Backfill: assign existing interactions to the workspace owner
UPDATE sentinel.workspace_interactions wi
SET user_id = (
    SELECT wm.user_id FROM sentinel.workspace_members wm
    WHERE wm.workspace_id = wi.workspace_id AND wm.role = 'owner'
    LIMIT 1
)
WHERE wi.user_id IS NULL;

-- For any remaining nulls, use the first member
UPDATE sentinel.workspace_interactions wi
SET user_id = (
    SELECT wm.user_id FROM sentinel.workspace_members wm
    WHERE wm.workspace_id = wi.workspace_id
    LIMIT 1
)
WHERE wi.user_id IS NULL;

ALTER TABLE sentinel.workspace_interactions ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE sentinel.workspace_interactions
    ADD PRIMARY KEY (workspace_id, tile_id, user_id);

-- ============================================================================
-- 5. Drop unused dataset_ids from workspaces (replaced by FK on datasets)
-- ============================================================================

ALTER TABLE sentinel.workspaces DROP COLUMN dataset_ids;

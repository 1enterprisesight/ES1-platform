-- V009: Sentinel application schema
-- Multi-user AI data dashboard — users, datasets, workspaces, and workspace state

-- Create isolated schema for Sentinel
CREATE SCHEMA IF NOT EXISTS sentinel;

-- ============================================================================
-- Users & Auth (Sentinel-owned, separate from platform auth)
-- ============================================================================

CREATE TABLE sentinel.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    display_name    TEXT,
    role            TEXT NOT NULL DEFAULT 'user',     -- 'user' | 'admin'
    status          TEXT NOT NULL DEFAULT 'pending',  -- 'pending' → 'verified' → 'active' → 'disabled'
    email_token     TEXT,
    email_token_expires_at TIMESTAMPTZ,
    reset_token     TEXT,
    reset_token_expires_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sentinel.sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES sentinel.users(id) ON DELETE CASCADE,
    token           TEXT UNIQUE NOT NULL,
    workspace_id    UUID,  -- FK added after workspaces table
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL
);

-- ============================================================================
-- Datasets (CSV uploads and external data sources)
-- ============================================================================

CREATE TABLE sentinel.datasets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES sentinel.users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    filename        TEXT NOT NULL,
    csv_data        BYTEA NOT NULL,
    row_count       INTEGER,
    columns         JSONB,  -- [{name, type, distinct_count, null_count}]
    file_size       INTEGER,
    source_type     TEXT NOT NULL DEFAULT 'upload',  -- 'upload' | 'airflow'
    airflow_conn_id TEXT,                             -- Airflow connection ID (for connector sources)
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sentinel.dataset_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES sentinel.users(id) ON DELETE CASCADE,
    dataset_a_id    UUID NOT NULL REFERENCES sentinel.datasets(id) ON DELETE CASCADE,
    dataset_b_id    UUID NOT NULL REFERENCES sentinel.datasets(id) ON DELETE CASCADE,
    column_a        TEXT NOT NULL,
    column_b        TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- Workspaces
-- ============================================================================

CREATE TABLE sentinel.workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES sentinel.users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    dataset_ids     JSONB NOT NULL DEFAULT '[]',
    settings        JSONB NOT NULL DEFAULT '{}',  -- silo_hints, row_config
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_accessed   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Now add the FK from sessions → workspaces
ALTER TABLE sentinel.sessions
    ADD CONSTRAINT fk_sessions_workspace
    FOREIGN KEY (workspace_id) REFERENCES sentinel.workspaces(id) ON DELETE SET NULL;

-- ============================================================================
-- Workspace State (replaces JSON file persistence)
-- ============================================================================

CREATE TABLE sentinel.workspace_tiles (
    id              BIGINT PRIMARY KEY,
    workspace_id    UUID NOT NULL REFERENCES sentinel.workspaces(id) ON DELETE CASCADE,
    silo            TEXT NOT NULL,
    col             TEXT NOT NULL,
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL,
    detail          TEXT,
    sources         JSONB DEFAULT '[]',
    chart_data      JSONB,
    metric          TEXT,
    metric_sub      TEXT,
    suggested_questions JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workspace_tiles_workspace ON sentinel.workspace_tiles(workspace_id);

CREATE TABLE sentinel.workspace_interactions (
    workspace_id    UUID NOT NULL REFERENCES sentinel.workspaces(id) ON DELETE CASCADE,
    tile_id         BIGINT NOT NULL,
    tile_title      TEXT,
    tile_silo       TEXT,
    tile_summary    TEXT,
    thumbs_up       INTEGER DEFAULT 0,
    thumbs_down     INTEGER DEFAULT 0,
    expanded        BOOLEAN DEFAULT FALSE,
    expand_duration_s REAL DEFAULT 0,
    followup_questions JSONB DEFAULT '[]',
    interest_score  REAL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, tile_id)
);

CREATE TABLE sentinel.workspace_silos (
    workspace_id    UUID NOT NULL REFERENCES sentinel.workspaces(id) ON DELETE CASCADE,
    silo_id         TEXT NOT NULL,
    label           TEXT NOT NULL,
    color           TEXT,
    bg              TEXT,
    border          TEXT,
    PRIMARY KEY (workspace_id, silo_id)
);

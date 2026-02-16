-- V004: Change Sets for gateway configuration management
-- Adds change_sets table and links exposure_changes to change sets

-- Ensure config_versions exists before creating FKs.
-- On fresh installs the db-migrate hook runs before the API pod starts,
-- so the table created by SQLAlchemy create_all() may not exist yet.
-- When the API starts later its CREATE TABLE IF NOT EXISTS is a no-op.
CREATE TABLE IF NOT EXISTS config_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version INTEGER NOT NULL UNIQUE,
    config_snapshot JSONB NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    commit_message TEXT,
    is_active BOOLEAN NOT NULL DEFAULT false,
    deployed_to_gateway_at TIMESTAMP,
    status VARCHAR(50)
);

-- Change sets represent a draft collection of configuration changes
-- that can be previewed, submitted for approval, and deployed as a unit.
CREATE TABLE IF NOT EXISTS change_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    base_version_id UUID REFERENCES config_versions(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft, submitted, approved, rejected, deployed, cancelled
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMP,
    description TEXT,
    config_version_id UUID REFERENCES config_versions(id) ON DELETE SET NULL
);

CREATE INDEX idx_change_sets_status ON change_sets(status);
CREATE INDEX idx_change_sets_created_by ON change_sets(created_by);
CREATE INDEX idx_change_sets_created_at ON change_sets(created_at);

-- Add change_set_id to exposure_changes to link individual changes to a set
ALTER TABLE exposure_changes
    ADD COLUMN IF NOT EXISTS change_set_id UUID REFERENCES change_sets(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_exposure_changes_change_set ON exposure_changes(change_set_id);

-- V004: Change Sets for gateway configuration management
-- Adds change_sets table and links exposure_changes to change sets

-- Ensure dependent tables exist before creating FKs.
-- On fresh installs the db-migrate hook runs before the API pod starts,
-- so tables created by SQLAlchemy create_all() may not exist yet.
-- When the API starts later its CREATE TABLE IF NOT EXISTS is a no-op.

CREATE TABLE IF NOT EXISTS discovered_resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    metadata JSONB NOT NULL,
    discovered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS config_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version INTEGER NOT NULL UNIQUE,
    config_snapshot JSONB NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    commit_message TEXT,
    is_active BOOLEAN NOT NULL DEFAULT false,
    deployed_to_gateway_at TIMESTAMP,
    status VARCHAR(50),
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    rejected_by VARCHAR(255),
    rejected_at TIMESTAMP,
    rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS exposures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_id UUID REFERENCES discovered_resources(id) ON DELETE CASCADE,
    settings JSONB NOT NULL,
    generated_config JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    deployed_in_version_id UUID REFERENCES config_versions(id) ON DELETE SET NULL,
    removed_in_version_id UUID REFERENCES config_versions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS exposure_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exposure_id UUID REFERENCES exposures(id) ON DELETE SET NULL,
    resource_id UUID REFERENCES discovered_resources(id) ON DELETE CASCADE,
    change_type VARCHAR(20) NOT NULL,
    settings_before JSONB,
    settings_after JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    batch_id UUID,
    requested_by VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    submitted_for_approval_at TIMESTAMP,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    rejected_by VARCHAR(255),
    rejected_at TIMESTAMP,
    rejection_reason TEXT,
    deployed_in_version_id UUID REFERENCES config_versions(id) ON DELETE SET NULL,
    deployed_at TIMESTAMP
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

CREATE INDEX IF NOT EXISTS idx_change_sets_status ON change_sets(status);
CREATE INDEX IF NOT EXISTS idx_change_sets_created_by ON change_sets(created_by);
CREATE INDEX IF NOT EXISTS idx_change_sets_created_at ON change_sets(created_at);

-- Add change_set_id to exposure_changes to link individual changes to a set
ALTER TABLE exposure_changes
    ADD COLUMN IF NOT EXISTS change_set_id UUID REFERENCES change_sets(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_exposure_changes_change_set ON exposure_changes(change_set_id);

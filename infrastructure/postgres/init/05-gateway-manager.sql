-- ES1 Gateway Manager Database Schema
-- PostgreSQL 16
-- Migrated from es-core-gw

-- Create gateway_manager database first
CREATE DATABASE gateway_manager;
GRANT ALL PRIVILEGES ON DATABASE gateway_manager TO es1_user;

\c gateway_manager

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Discovered resources from external systems (Airflow DAGs, K8s services, etc.)
CREATE TABLE discovered_resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL,  -- workflow, connection, service, etc.
    source VARCHAR(50) NOT NULL,  -- airflow, kubernetes, langflow, manual
    source_id VARCHAR(255) NOT NULL,  -- ID in source system
    metadata JSONB NOT NULL,  -- Resource-specific data
    discovered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, inactive, deleted
    UNIQUE(source, source_id)
);

CREATE INDEX idx_resources_type ON discovered_resources(type);
CREATE INDEX idx_resources_source ON discovered_resources(source);
CREATE INDEX idx_resources_status ON discovered_resources(status);

-- Configuration versions (audit trail) - Created first for FK references
CREATE TABLE config_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version INT NOT NULL UNIQUE,
    config_snapshot JSONB NOT NULL,  -- Complete gateway config
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    commit_message TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    deployed_to_gateway_at TIMESTAMP,
    rejected_by VARCHAR(255),
    rejected_at TIMESTAMP,
    rejection_reason TEXT
);

CREATE INDEX idx_versions_created ON config_versions(created_at DESC);
CREATE INDEX idx_config_versions_is_active ON config_versions(is_active) WHERE is_active = TRUE;

COMMENT ON COLUMN config_versions.is_active IS 'TRUE if this version is currently running on gateway (only one can be TRUE)';
COMMENT ON COLUMN config_versions.deployed_to_gateway_at IS 'Timestamp when this version was deployed to gateway';
COMMENT ON COLUMN config_versions.rejected_by IS 'User who rejected this config version';
COMMENT ON COLUMN config_versions.rejected_at IS 'Timestamp when this config version was rejected';
COMMENT ON COLUMN config_versions.rejection_reason IS 'Reason provided for rejecting this config version';

-- Exposures (tagged resources with gateway config)
CREATE TABLE exposures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_id UUID NOT NULL REFERENCES discovered_resources(id) ON DELETE CASCADE,
    settings JSONB NOT NULL,  -- User settings (rate limit, access level)
    generated_config JSONB NOT NULL,  -- Auto-generated endpoint config
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, deployed
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    deployed_in_version_id UUID REFERENCES config_versions(id) ON DELETE SET NULL,
    removed_in_version_id UUID REFERENCES config_versions(id) ON DELETE SET NULL,
    UNIQUE(resource_id)  -- One exposure per resource
);

CREATE INDEX idx_exposures_status ON exposures(status);
CREATE INDEX idx_exposures_resource ON exposures(resource_id);
CREATE INDEX idx_exposures_deployed_in_version ON exposures(deployed_in_version_id);
CREATE INDEX idx_exposures_removed_in_version ON exposures(removed_in_version_id);

COMMENT ON COLUMN exposures.deployed_in_version_id IS 'Config version that deployed this exposure to gateway';
COMMENT ON COLUMN exposures.removed_in_version_id IS 'Config version that removed this exposure from gateway';

-- Deployments
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES config_versions(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, in_progress, succeeded, failed, rolled_back
    deployed_by VARCHAR(255) NOT NULL,
    deployed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    health_check_passed BOOLEAN,
    error_message TEXT,
    rollback_from_deployment_id UUID REFERENCES deployments(id)
);

CREATE INDEX idx_deployments_status ON deployments(status);
CREATE INDEX idx_deployments_version ON deployments(version_id);
CREATE INDEX idx_deployments_deployed_at ON deployments(deployed_at DESC);

-- Approval workflow
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exposure_id UUID NOT NULL REFERENCES exposures(id) ON DELETE CASCADE,
    approver VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- approved, rejected, pending
    comments TEXT,
    approved_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approvals_exposure ON approvals(exposure_id);
CREATE INDEX idx_approvals_status ON approvals(status);

-- Event log (for audit trail)
CREATE TABLE event_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    user_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_type ON event_log(event_type);
CREATE INDEX idx_events_entity ON event_log(entity_type, entity_id);
CREATE INDEX idx_events_created ON event_log(created_at DESC);

-- Exposure changes (change management workflow)
CREATE TABLE exposure_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exposure_id UUID REFERENCES exposures(id) ON DELETE SET NULL,  -- NULL for new additions
    resource_id UUID NOT NULL REFERENCES discovered_resources(id) ON DELETE CASCADE,
    change_type VARCHAR(20) NOT NULL CHECK (change_type IN ('add', 'remove', 'modify')),
    settings_before JSONB,  -- For modify: old settings
    settings_after JSONB,   -- For add/modify: new settings
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'pending_approval', 'approved', 'rejected', 'deployed', 'cancelled')),
    batch_id UUID,  -- Group related changes together
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

CREATE INDEX idx_exposure_changes_status ON exposure_changes(status);
CREATE INDEX idx_exposure_changes_batch ON exposure_changes(batch_id);
CREATE INDEX idx_exposure_changes_resource ON exposure_changes(resource_id);

COMMENT ON TABLE exposure_changes IS 'Tracks proposed changes to gateway exposures through draft/approval/deployment workflow';
COMMENT ON COLUMN exposure_changes.change_type IS 'Type of change: add (new exposure), remove (delete exposure), modify (update settings)';
COMMENT ON COLUMN exposure_changes.status IS 'Workflow status: draft -> pending_approval -> approved -> deployed';
COMMENT ON COLUMN exposure_changes.batch_id IS 'Groups related changes submitted together for approval';

-- Branding configuration (white-label support)
CREATE TABLE branding_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    config JSONB NOT NULL,  -- Theme colors, logos, etc.
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_branding_is_active ON branding_config(is_active) WHERE is_active = TRUE;

-- Grant all privileges to es1_user
GRANT ALL ON ALL TABLES IN SCHEMA public TO es1_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO es1_user;

-- V003: Ensure audit schema grants use CURRENT_USER
-- Originally fixed V002's hardcoded username. Now V002 uses CURRENT_USER
-- directly, but this migration is kept for ordering consistency.
-- Phase 5: Credential Externalization & Secrets Management

-- Re-grant schema usage to the current database user
GRANT USAGE ON SCHEMA audit TO CURRENT_USER;

-- Set default privileges for future tables created in audit schema
ALTER DEFAULT PRIVILEGES IN SCHEMA audit
    GRANT ALL PRIVILEGES ON TABLES TO CURRENT_USER;

-- Re-grant on all existing tables (idempotent)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO CURRENT_USER;

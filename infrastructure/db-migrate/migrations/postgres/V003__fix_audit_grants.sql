-- V003: Fix audit schema grants for white-label deployments
-- V002 hardcoded 'es1_user' in GRANT statements. This migration
-- re-grants privileges using CURRENT_USER so any DB username works.
-- Phase 5: Credential Externalization & Secrets Management

-- Re-grant schema usage to the current database user
GRANT USAGE ON SCHEMA audit TO CURRENT_USER;

-- Set default privileges for future tables created in audit schema
ALTER DEFAULT PRIVILEGES IN SCHEMA audit
    GRANT ALL PRIVILEGES ON TABLES TO CURRENT_USER;

-- Re-grant on all existing tables (idempotent)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO CURRENT_USER;

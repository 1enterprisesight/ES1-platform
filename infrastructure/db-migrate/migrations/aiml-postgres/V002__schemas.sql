-- V002: Create schemas for AI/ML concerns
-- Separate schemas for different domains

-- Create schemas for different AI/ML concerns
CREATE SCHEMA IF NOT EXISTS vectors;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS mlops;

-- Grant usage to aiml_user
GRANT USAGE ON SCHEMA vectors TO aiml_user;
GRANT USAGE ON SCHEMA rag TO aiml_user;
GRANT USAGE ON SCHEMA agents TO aiml_user;
GRANT USAGE ON SCHEMA mlops TO aiml_user;

-- Default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA vectors GRANT ALL PRIVILEGES ON TABLES TO aiml_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA rag GRANT ALL PRIVILEGES ON TABLES TO aiml_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA agents GRANT ALL PRIVILEGES ON TABLES TO aiml_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA mlops GRANT ALL PRIVILEGES ON TABLES TO aiml_user;

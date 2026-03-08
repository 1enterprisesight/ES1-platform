-- V010: Add LLM-generated profile to datasets
-- Stores semantic understanding of each dataset: domain, entities, column descriptions,
-- relationships, and suggested analysis angles. Generated once on upload.

ALTER TABLE sentinel.datasets
    ADD COLUMN IF NOT EXISTS profile JSONB;

COMMENT ON COLUMN sentinel.datasets.profile IS
    'LLM-generated semantic profile: domain, description, column_profiles[], relationships[], analysis_angles[]';

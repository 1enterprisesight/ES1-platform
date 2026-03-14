-- V014: Add missing columns to rag.documents
-- Platform Manager's Document schema expects file_path, url, status, error_message
-- but these were not in the original V003 migration.
-- Sentinel knowledge_sync also inserts documents without these fields.

ALTER TABLE rag.documents
    ADD COLUMN IF NOT EXISTS file_path VARCHAR DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS url VARCHAR DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'processed',
    ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL;

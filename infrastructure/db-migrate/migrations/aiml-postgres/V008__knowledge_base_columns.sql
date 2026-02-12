-- V008: Add missing columns to rag.knowledge_bases
-- These columns were added to the Pydantic schema but never migrated.
-- Required for knowledge base listing and management.

ALTER TABLE rag.knowledge_bases ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(255) DEFAULT 'nomic-embed-text';
ALTER TABLE rag.knowledge_bases ADD COLUMN IF NOT EXISTS embedding_dimension INTEGER DEFAULT 768;
ALTER TABLE rag.knowledge_bases ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

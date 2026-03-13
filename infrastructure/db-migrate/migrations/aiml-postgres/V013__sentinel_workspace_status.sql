-- V013: Add status column to sentinel.workspaces
-- Referenced by knowledge_sync.py for RAG document generation

ALTER TABLE sentinel.workspaces
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';

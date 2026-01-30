-- Reference seed: Starter knowledge base for documents
-- This creates a default knowledge base that's always available for document uploads

-- Create default "Documents" knowledge base
INSERT INTO rag.knowledge_bases (
    name,
    description,
    chunking_strategy,
    chunk_size,
    chunk_overlap,
    metadata
)
VALUES (
    'documents',
    'Default knowledge base for uploaded documents. Upload PDFs, Word docs, text files, and more to enable AI-powered search and retrieval.',
    'recursive',
    512,
    50,
    '{"category": "general", "is_default": true, "created_by": "system"}'
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    metadata = rag.knowledge_bases.metadata || EXCLUDED.metadata;

-- Create a file source for local uploads
INSERT INTO rag.sources (
    name,
    source_type,
    uri,
    content_type,
    metadata,
    sync_status
)
VALUES (
    'local-uploads',
    'file',
    '/data/uploads',
    'application/octet-stream',
    '{"description": "Local file upload source", "auto_process": true}',
    'completed'
)
ON CONFLICT DO NOTHING;

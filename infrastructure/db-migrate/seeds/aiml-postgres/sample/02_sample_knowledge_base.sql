-- Sample seed data: Demo knowledge base
-- This creates a sample knowledge base for development/demo purposes

INSERT INTO rag.knowledge_bases (
    name,
    description,
    chunking_strategy,
    chunk_size,
    chunk_overlap,
    metadata
)
VALUES (
    'demo-knowledge-base',
    'A sample knowledge base for platform demonstrations',
    'recursive',
    512,
    50,
    '{"category": "demo", "created_by": "seed-data"}'
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description;

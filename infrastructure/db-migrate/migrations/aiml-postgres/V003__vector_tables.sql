-- V003: Vector embeddings storage
-- Supports multiple embedding models and dimensions

-- Collections group related embeddings
CREATE TABLE IF NOT EXISTS vectors.collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    embedding_model VARCHAR(255) NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    distance_metric VARCHAR(50) DEFAULT 'cosine', -- cosine, l2, inner_product
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings with flexible dimension support
-- Using 1536 as default (OpenAI ada-002), but supports any dimension
CREATE TABLE IF NOT EXISTS vectors.embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID NOT NULL REFERENCES vectors.collections(id) ON DELETE CASCADE,
    content_hash VARCHAR(64), -- For deduplication
    content TEXT, -- Original text content
    embedding vector(1536), -- Default dimension, can create tables with other dimensions
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create HNSW index for fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON vectors.embeddings USING hnsw (embedding vector_cosine_ops);

-- Index for collection queries
CREATE INDEX IF NOT EXISTS idx_embeddings_collection ON vectors.embeddings(collection_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_content_hash ON vectors.embeddings(content_hash);

-- Embeddings with 384 dimensions (for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS vectors.embeddings_384 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID NOT NULL REFERENCES vectors.collections(id) ON DELETE CASCADE,
    content_hash VARCHAR(64),
    content TEXT,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_embeddings_384_hnsw ON vectors.embeddings_384 USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_embeddings_384_collection ON vectors.embeddings_384(collection_id);

-- Embeddings with 768 dimensions (for BERT)
CREATE TABLE IF NOT EXISTS vectors.embeddings_768 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID NOT NULL REFERENCES vectors.collections(id) ON DELETE CASCADE,
    content_hash VARCHAR(64),
    content TEXT,
    embedding vector(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_embeddings_768_hnsw ON vectors.embeddings_768 USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_embeddings_768_collection ON vectors.embeddings_768(collection_id);

-- Embeddings with 4096 dimensions (for larger models)
-- 4096 dimensions exceeds HNSW limit of 2000, use IVFFlat instead
CREATE TABLE IF NOT EXISTS vectors.embeddings_4096 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID NOT NULL REFERENCES vectors.collections(id) ON DELETE CASCADE,
    content_hash VARCHAR(64),
    content TEXT,
    embedding vector(4096),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- IVFFlat index for dimensions > 2000 (requires training data, created separately)
-- CREATE INDEX ON vectors.embeddings_4096 USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_embeddings_4096_collection ON vectors.embeddings_4096(collection_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_4096_content_hash ON vectors.embeddings_4096(content_hash);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA vectors TO aiml_user;

-- RAG (Retrieval-Augmented Generation) tables
-- For document storage, chunking, and knowledge management

-- Document sources (files, URLs, APIs, etc.)
CREATE TABLE rag.sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- file, url, api, database, s3
    uri TEXT, -- Path, URL, or connection string
    content_type VARCHAR(100), -- MIME type
    metadata JSONB DEFAULT '{}',
    last_synced_at TIMESTAMPTZ,
    sync_status VARCHAR(50) DEFAULT 'pending', -- pending, syncing, completed, failed
    sync_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge bases group related documents
CREATE TABLE rag.knowledge_bases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    collection_id UUID, -- Reference to vectors.collections
    embedding_model VARCHAR(255) DEFAULT 'nomic-embed-text',
    embedding_dimension INTEGER DEFAULT 768,
    chunking_strategy VARCHAR(50) DEFAULT 'recursive', -- fixed, recursive, semantic
    chunk_size INTEGER DEFAULT 512,
    chunk_overlap INTEGER DEFAULT 50,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents extracted from sources
CREATE TABLE rag.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES rag.sources(id) ON DELETE SET NULL,
    knowledge_base_id UUID REFERENCES rag.knowledge_bases(id) ON DELETE CASCADE,
    title VARCHAR(500),
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL, -- For change detection
    content_type VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_source ON rag.documents(source_id);
CREATE INDEX idx_documents_kb ON rag.documents(knowledge_base_id);
CREATE INDEX idx_documents_content_hash ON rag.documents(content_hash);

-- Document chunks for embedding
CREATE TABLE rag.chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES rag.documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL, -- Order within document
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    start_char INTEGER, -- Position in original document
    end_char INTEGER,
    token_count INTEGER,
    embedding_id UUID, -- Reference to vectors.embeddings
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON rag.chunks(document_id);
CREATE INDEX idx_chunks_embedding ON rag.chunks(embedding_id);
CREATE INDEX idx_chunks_content_hash ON rag.chunks(content_hash);

-- Link knowledge bases to sources
CREATE TABLE rag.knowledge_base_sources (
    knowledge_base_id UUID NOT NULL REFERENCES rag.knowledge_bases(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES rag.sources(id) ON DELETE CASCADE,
    PRIMARY KEY (knowledge_base_id, source_id)
);

-- Search history for analytics
CREATE TABLE rag.search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id UUID REFERENCES rag.knowledge_bases(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    query_embedding_id UUID,
    results_count INTEGER,
    top_score FLOAT,
    latency_ms INTEGER,
    user_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_history_kb ON rag.search_history(knowledge_base_id);
CREATE INDEX idx_search_history_created ON rag.search_history(created_at);

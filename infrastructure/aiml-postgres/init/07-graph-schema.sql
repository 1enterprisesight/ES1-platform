-- Knowledge Graph schema for entity and relationship storage
-- Extends the RAG capabilities with structured knowledge
-- Phase 6.6a: Knowledge Graph Foundation

CREATE SCHEMA IF NOT EXISTS graph;

-- Grant access
GRANT USAGE ON SCHEMA graph TO aiml_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA graph TO aiml_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA graph GRANT ALL PRIVILEGES ON TABLES TO aiml_user;

-- Entity types catalog (for consistent typing)
CREATE TABLE graph.entity_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_type_id UUID REFERENCES graph.entity_types(id),  -- For type hierarchy
    schema JSONB DEFAULT '{}',              -- Expected properties for this type
    icon VARCHAR(50),                       -- Icon name for UI
    color VARCHAR(20),                      -- Color for UI visualization
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed common entity types
INSERT INTO graph.entity_types (name, description, icon, color) VALUES
    ('person', 'A human individual', 'user', '#3B82F6'),
    ('organization', 'A company, institution, or group', 'building', '#10B981'),
    ('location', 'A physical place or address', 'map-pin', '#F59E0B'),
    ('concept', 'An abstract idea or topic', 'lightbulb', '#8B5CF6'),
    ('event', 'Something that happened at a point in time', 'calendar', '#EC4899'),
    ('product', 'A physical or digital product', 'package', '#06B6D4'),
    ('document', 'A reference to a document or file', 'file-text', '#6B7280'),
    ('technology', 'A technology, tool, or framework', 'cpu', '#EF4444'),
    ('process', 'A business or technical process', 'git-branch', '#84CC16');

-- Relationship types catalog
CREATE TABLE graph.relationship_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    source_entity_types VARCHAR(100)[],     -- Allowed source types (null = any)
    target_entity_types VARCHAR(100)[],     -- Allowed target types (null = any)
    is_directional BOOLEAN DEFAULT true,
    inverse_name VARCHAR(100),              -- Name when traversing in reverse
    schema JSONB DEFAULT '{}',              -- Expected properties
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed common relationship types
INSERT INTO graph.relationship_types (name, description, inverse_name, source_entity_types, target_entity_types) VALUES
    ('works_for', 'Employment relationship', 'employs', ARRAY['person'], ARRAY['organization']),
    ('located_in', 'Physical location relationship', 'contains', NULL, ARRAY['location']),
    ('part_of', 'Membership or component relationship', 'has_part', NULL, NULL),
    ('related_to', 'General relationship', 'related_to', NULL, NULL),
    ('created_by', 'Authorship or creation', 'created', NULL, ARRAY['person', 'organization']),
    ('depends_on', 'Dependency relationship', 'required_by', NULL, NULL),
    ('interacts_with', 'Interaction or communication', 'interacts_with', NULL, NULL),
    ('succeeded_by', 'Temporal succession', 'preceded_by', NULL, NULL),
    ('similar_to', 'Similarity relationship', 'similar_to', NULL, NULL),
    ('references', 'Citation or reference', 'referenced_by', NULL, NULL);

-- Entities extracted from documents
CREATE TABLE graph.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id UUID REFERENCES rag.knowledge_bases(id) ON DELETE CASCADE,
    entity_type VARCHAR(100) NOT NULL REFERENCES graph.entity_types(name),

    -- Identity
    name VARCHAR(500) NOT NULL,
    canonical_name VARCHAR(500),            -- Normalized name for deduplication
    aliases VARCHAR(500)[],                 -- Alternative names

    -- Description and properties
    description TEXT,
    properties JSONB DEFAULT '{}',

    -- Vector embedding for semantic search
    embedding_id UUID,                      -- Link to vectors.embeddings

    -- Provenance
    source_chunk_ids UUID[],                -- Which chunks mentioned this entity
    extraction_method VARCHAR(50),          -- manual, spacy, llm, hybrid
    confidence FLOAT DEFAULT 1.0,

    -- Status
    is_verified BOOLEAN DEFAULT false,      -- Human verified
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique entities within a knowledge base
    UNIQUE(knowledge_base_id, canonical_name, entity_type)
);

CREATE INDEX idx_entities_kb ON graph.entities(knowledge_base_id);
CREATE INDEX idx_entities_type ON graph.entities(entity_type);
CREATE INDEX idx_entities_canonical ON graph.entities(canonical_name);
CREATE INDEX idx_entities_name_trgm ON graph.entities USING gin (name gin_trgm_ops);

-- Relationships between entities
CREATE TABLE graph.relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id UUID REFERENCES rag.knowledge_bases(id) ON DELETE CASCADE,

    -- The relationship
    source_entity_id UUID NOT NULL REFERENCES graph.entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL REFERENCES graph.relationship_types(name),
    target_entity_id UUID NOT NULL REFERENCES graph.entities(id) ON DELETE CASCADE,

    -- Properties
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0,               -- Strength of relationship

    -- Provenance
    source_chunk_ids UUID[],
    extraction_method VARCHAR(50),
    confidence FLOAT DEFAULT 1.0,

    -- Status
    is_verified BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate relationships
    UNIQUE(knowledge_base_id, source_entity_id, relationship_type, target_entity_id)
);

CREATE INDEX idx_relationships_kb ON graph.relationships(knowledge_base_id);
CREATE INDEX idx_relationships_source ON graph.relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON graph.relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON graph.relationships(relationship_type);

-- Entity mentions in chunks (for provenance tracking)
CREATE TABLE graph.entity_mentions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES graph.entities(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES rag.chunks(id) ON DELETE CASCADE,
    mention_text VARCHAR(500) NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    context TEXT,                           -- Surrounding text for context
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(entity_id, chunk_id, start_char)
);

CREATE INDEX idx_entity_mentions_entity ON graph.entity_mentions(entity_id);
CREATE INDEX idx_entity_mentions_chunk ON graph.entity_mentions(chunk_id);

-- Graph queries cache (for expensive traversals)
CREATE TABLE graph.query_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id UUID REFERENCES rag.knowledge_bases(id) ON DELETE CASCADE,
    query_hash VARCHAR(64) NOT NULL,        -- Hash of the query parameters
    query_type VARCHAR(50) NOT NULL,        -- neighbors, paths, subgraph, etc.
    query_params JSONB NOT NULL,
    result JSONB NOT NULL,
    result_count INTEGER,
    computation_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 hour',
    UNIQUE(knowledge_base_id, query_hash)
);

CREATE INDEX idx_query_cache_expires ON graph.query_cache(expires_at);

-- Useful views

-- Entity statistics per knowledge base
CREATE VIEW graph.entity_stats AS
SELECT
    kb.id as knowledge_base_id,
    kb.name as knowledge_base_name,
    e.entity_type,
    COUNT(*) as entity_count,
    COUNT(*) FILTER (WHERE e.is_verified) as verified_count,
    AVG(e.confidence) as avg_confidence
FROM rag.knowledge_bases kb
LEFT JOIN graph.entities e ON e.knowledge_base_id = kb.id AND e.is_active
GROUP BY kb.id, kb.name, e.entity_type;

-- Relationship statistics
CREATE VIEW graph.relationship_stats AS
SELECT
    kb.id as knowledge_base_id,
    kb.name as knowledge_base_name,
    r.relationship_type,
    COUNT(*) as relationship_count,
    AVG(r.confidence) as avg_confidence
FROM rag.knowledge_bases kb
LEFT JOIN graph.relationships r ON r.knowledge_base_id = kb.id AND r.is_active
GROUP BY kb.id, kb.name, r.relationship_type;

-- Functions for graph traversal

-- Get entity neighbors (1-hop)
CREATE OR REPLACE FUNCTION graph.get_neighbors(
    p_entity_id UUID,
    p_relationship_types VARCHAR[] DEFAULT NULL,
    p_direction VARCHAR DEFAULT 'both'  -- 'outgoing', 'incoming', 'both'
)
RETURNS TABLE (
    entity_id UUID,
    entity_name VARCHAR,
    entity_type VARCHAR,
    relationship_type VARCHAR,
    relationship_direction VARCHAR,
    confidence FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        CASE WHEN r.source_entity_id = p_entity_id THEN r.target_entity_id ELSE r.source_entity_id END,
        e.name,
        e.entity_type,
        r.relationship_type,
        CASE WHEN r.source_entity_id = p_entity_id THEN 'outgoing'::VARCHAR ELSE 'incoming'::VARCHAR END,
        r.confidence
    FROM graph.relationships r
    JOIN graph.entities e ON e.id = CASE
        WHEN r.source_entity_id = p_entity_id THEN r.target_entity_id
        ELSE r.source_entity_id
    END
    WHERE r.is_active
      AND e.is_active
      AND (
          (p_direction IN ('outgoing', 'both') AND r.source_entity_id = p_entity_id)
          OR (p_direction IN ('incoming', 'both') AND r.target_entity_id = p_entity_id)
      )
      AND (p_relationship_types IS NULL OR r.relationship_type = ANY(p_relationship_types));
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE graph.entities IS 'Entities extracted from documents in knowledge bases';
COMMENT ON TABLE graph.relationships IS 'Relationships between entities forming the knowledge graph';
COMMENT ON TABLE graph.entity_mentions IS 'Tracks where entities are mentioned in source chunks';
COMMENT ON FUNCTION graph.get_neighbors IS 'Returns neighboring entities connected by relationships';

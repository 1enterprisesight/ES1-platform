"""Pydantic schemas for knowledge management."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


# =============================================================================
# Enums
# =============================================================================


class SourceType(str, Enum):
    """Types of knowledge sources."""
    FILE = "file"
    URL = "url"
    DATABASE = "database"
    API = "api"
    S3 = "s3"


class SourceStatus(str, Enum):
    """Status of a knowledge source."""
    PENDING = "pending"
    INGESTING = "ingesting"
    ACTIVE = "active"
    FAILED = "failed"
    DISABLED = "disabled"


class ChunkingStrategy(str, Enum):
    """Document chunking strategies."""
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"


class EntityType(str, Enum):
    """Types of extracted entities."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    EVENT = "event"
    PRODUCT = "product"
    OTHER = "other"


# =============================================================================
# Knowledge Base Schemas
# =============================================================================


class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a knowledge base."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    embedding_model: str = Field(default="nomic-embed-text")
    embedding_dimension: int = Field(default=768)
    chunking_strategy: ChunkingStrategy = Field(default=ChunkingStrategy.RECURSIVE)
    chunk_size: int = Field(default=512, ge=100, le=4096)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    metadata: Optional[dict] = Field(default_factory=dict)


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating a knowledge base."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    embedding_model: Optional[str] = None
    chunking_strategy: Optional[ChunkingStrategy] = None
    chunk_size: Optional[int] = Field(None, ge=100, le=4096)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500)
    metadata: Optional[dict] = None


class KnowledgeBase(BaseModel):
    """Schema for a knowledge base."""
    id: UUID
    name: str
    description: Optional[str]
    embedding_model: str
    embedding_dimension: int
    chunking_strategy: str
    chunk_size: int
    chunk_overlap: int
    metadata: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0
    chunk_count: Optional[int] = 0
    entity_count: Optional[int] = 0

    class Config:
        from_attributes = True


class KnowledgeBaseList(BaseModel):
    """Schema for list of knowledge bases."""
    knowledge_bases: list[KnowledgeBase]
    total: int


# =============================================================================
# Source Schemas
# =============================================================================


class SourceCreate(BaseModel):
    """Schema for creating a source."""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType
    connection_config: dict = Field(default_factory=dict)
    description: Optional[str] = None
    schedule: Optional[str] = None  # Cron expression for periodic ingestion
    metadata: Optional[dict] = Field(default_factory=dict)


class SourceUpdate(BaseModel):
    """Schema for updating a source."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    connection_config: Optional[dict] = None
    schedule: Optional[str] = None
    status: Optional[SourceStatus] = None
    metadata: Optional[dict] = None


class Source(BaseModel):
    """Schema for a source."""
    id: UUID
    knowledge_base_id: Optional[UUID] = None
    name: str
    source_type: str
    connection_config: Optional[dict] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    status: Optional[str] = "pending"
    last_sync: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None  # Alias for DB column
    sync_status: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SourceList(BaseModel):
    """Schema for list of sources."""
    sources: list[Source]
    total: int


# =============================================================================
# Document Schemas
# =============================================================================


class Document(BaseModel):
    """Schema for a document."""
    id: UUID
    knowledge_base_id: UUID
    source_id: Optional[UUID]
    title: str
    content_hash: str
    content_type: str
    file_path: Optional[str]
    url: Optional[str]
    metadata: dict
    chunk_count: int
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentList(BaseModel):
    """Schema for list of documents."""
    documents: list[Document]
    total: int


class DocumentDetail(Document):
    """Schema for document with chunks."""
    chunks: list["Chunk"] = []


# =============================================================================
# Chunk Schemas
# =============================================================================


class Chunk(BaseModel):
    """Schema for a document chunk."""
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    start_char: int
    end_char: int
    metadata: dict
    has_embedding: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChunkList(BaseModel):
    """Schema for list of chunks."""
    chunks: list[Chunk]
    total: int


# =============================================================================
# Entity Schemas
# =============================================================================


class Entity(BaseModel):
    """Schema for an extracted entity."""
    id: UUID
    knowledge_base_id: UUID
    entity_type: str
    name: str
    canonical_name: Optional[str]
    description: Optional[str]
    properties: dict
    confidence: float
    mention_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EntityList(BaseModel):
    """Schema for list of entities."""
    entities: list[Entity]
    total: int


class EntityDetail(Entity):
    """Schema for entity with relationships."""
    outgoing_relationships: list["Relationship"] = []
    incoming_relationships: list["Relationship"] = []


# =============================================================================
# Relationship Schemas
# =============================================================================


class Relationship(BaseModel):
    """Schema for a relationship between entities."""
    id: UUID
    knowledge_base_id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    properties: dict
    confidence: float
    created_at: datetime

    # Populated when fetching with entity details
    source_entity_name: Optional[str] = None
    target_entity_name: Optional[str] = None

    class Config:
        from_attributes = True


class RelationshipList(BaseModel):
    """Schema for list of relationships."""
    relationships: list[Relationship]
    total: int


# =============================================================================
# Search Schemas
# =============================================================================


class SearchRequest(BaseModel):
    """Schema for semantic search request."""
    query: str = Field(..., min_length=1)
    knowledge_base_id: Optional[UUID] = None
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    include_content: bool = True
    include_metadata: bool = True
    filters: Optional[dict] = None


class SearchResult(BaseModel):
    """Schema for a search result."""
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: Optional[str]
    score: float
    metadata: Optional[dict]
    knowledge_base_id: UUID
    knowledge_base_name: str


class SearchResponse(BaseModel):
    """Schema for search response."""
    results: list[SearchResult]
    query: str
    total: int


# =============================================================================
# Graph Query Schemas
# =============================================================================


class GraphQueryRequest(BaseModel):
    """Schema for graph query request."""
    knowledge_base_id: UUID
    entity_types: Optional[list[str]] = None
    relationship_types: Optional[list[str]] = None
    root_entity_id: Optional[UUID] = None
    depth: int = Field(default=2, ge=1, le=5)
    limit: int = Field(default=100, ge=1, le=1000)


class GraphNode(BaseModel):
    """Schema for a graph node."""
    id: str
    label: str
    type: str
    properties: dict


class GraphEdge(BaseModel):
    """Schema for a graph edge."""
    id: str
    source: str
    target: str
    type: str
    properties: dict


class GraphResponse(BaseModel):
    """Schema for graph query response."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int


# =============================================================================
# Ingestion Schemas
# =============================================================================


class IngestionRequest(BaseModel):
    """Schema for triggering ingestion."""
    source_id: Optional[UUID] = None  # If None, ingest all sources
    force_reprocess: bool = False


class IngestionStatus(BaseModel):
    """Schema for ingestion status."""
    dag_run_id: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    source_id: Optional[UUID]
    knowledge_base_id: UUID
    documents_processed: int
    chunks_created: int
    entities_extracted: int
    errors: list[str]


class IngestionResponse(BaseModel):
    """Schema for ingestion trigger response."""
    message: str
    dag_run_id: Optional[str]
    knowledge_base_id: UUID


# =============================================================================
# Stats Schemas
# =============================================================================


class KnowledgeStats(BaseModel):
    """Schema for knowledge base statistics."""
    total_knowledge_bases: int
    total_sources: int
    total_documents: int
    total_chunks: int
    total_entities: int
    total_relationships: int
    storage_size_mb: Optional[float] = None
    last_ingestion: Optional[datetime] = None


class KnowledgeBaseStats(BaseModel):
    """Schema for individual knowledge base statistics."""
    knowledge_base_id: UUID
    name: str
    document_count: int
    chunk_count: int
    entity_count: int
    relationship_count: int
    source_count: int
    active_sources: int
    last_sync: Optional[datetime] = None
    storage_size_mb: Optional[float] = None


# Update forward references
DocumentDetail.model_rebuild()
EntityDetail.model_rebuild()

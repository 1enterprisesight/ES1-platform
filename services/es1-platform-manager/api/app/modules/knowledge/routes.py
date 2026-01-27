"""API routes for knowledge management."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.client import get_aiml_db, ollama_client
from app.modules.knowledge.services import KnowledgeService
from app.modules.knowledge.schemas import (
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseList,
    Source,
    SourceCreate,
    SourceUpdate,
    SourceList,
    Document,
    DocumentList,
    DocumentDetail,
    Entity,
    EntityList,
    EntityDetail,
    Relationship,
    RelationshipList,
    SearchRequest,
    SearchResponse,
    GraphQueryRequest,
    GraphResponse,
    IngestionRequest,
    IngestionResponse,
    KnowledgeStats,
    KnowledgeBaseStats,
)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Management"])


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health")
async def knowledge_health():
    """Check health of knowledge management services."""
    ollama_healthy = await ollama_client.health_check()

    return {
        "status": "healthy" if ollama_healthy else "degraded",
        "ollama": "connected" if ollama_healthy else "disconnected",
        "embedding_model": ollama_client.model,
    }


# =============================================================================
# Statistics
# =============================================================================


@router.get("/stats", response_model=KnowledgeStats)
async def get_knowledge_stats(db: AsyncSession = Depends(get_aiml_db)):
    """Get overall knowledge statistics."""
    service = KnowledgeService(db)
    stats = await service.get_stats()
    return KnowledgeStats(**stats)


# =============================================================================
# Knowledge Bases
# =============================================================================


@router.get("/bases", response_model=KnowledgeBaseList)
async def list_knowledge_bases(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_aiml_db),
):
    """List all knowledge bases."""
    service = KnowledgeService(db)
    knowledge_bases, total = await service.list_knowledge_bases(offset=offset, limit=limit)
    return KnowledgeBaseList(knowledge_bases=knowledge_bases, total=total)


@router.post("/bases", response_model=KnowledgeBase, status_code=201)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Create a new knowledge base."""
    service = KnowledgeService(db)
    kb = await service.create_knowledge_base(data)
    return KnowledgeBase(**kb)


@router.get("/bases/{kb_id}", response_model=KnowledgeBase)
async def get_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Get a knowledge base by ID."""
    service = KnowledgeService(db)
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return KnowledgeBase(**kb)


@router.patch("/bases/{kb_id}", response_model=KnowledgeBase)
async def update_knowledge_base(
    kb_id: UUID,
    data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Update a knowledge base."""
    service = KnowledgeService(db)
    kb = await service.update_knowledge_base(kb_id, data)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return KnowledgeBase(**kb)


@router.delete("/bases/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Delete a knowledge base and all associated data."""
    service = KnowledgeService(db)
    deleted = await service.delete_knowledge_base(kb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")


@router.get("/bases/{kb_id}/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats(
    kb_id: UUID,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Get statistics for a knowledge base."""
    service = KnowledgeService(db)
    stats = await service.get_knowledge_base_stats(kb_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return KnowledgeBaseStats(**stats)


# =============================================================================
# Sources
# =============================================================================


@router.get("/bases/{kb_id}/sources", response_model=SourceList)
async def list_sources(
    kb_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_aiml_db),
):
    """List sources for a knowledge base."""
    service = KnowledgeService(db)
    sources, total = await service.list_sources(kb_id, offset=offset, limit=limit)
    return SourceList(sources=sources, total=total)


@router.post("/bases/{kb_id}/sources", response_model=Source, status_code=201)
async def create_source(
    kb_id: UUID,
    data: SourceCreate,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Create a new source for a knowledge base."""
    service = KnowledgeService(db)

    # Verify knowledge base exists
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    source = await service.create_source(kb_id, data)
    return Source(**source)


@router.get("/sources/{source_id}", response_model=Source)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Get a source by ID."""
    service = KnowledgeService(db)
    source = await service.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return Source(**source)


@router.patch("/sources/{source_id}", response_model=Source)
async def update_source(
    source_id: UUID,
    data: SourceUpdate,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Update a source."""
    service = KnowledgeService(db)
    source = await service.update_source(source_id, data)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return Source(**source)


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Delete a source."""
    service = KnowledgeService(db)
    deleted = await service.delete_source(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")


# =============================================================================
# Documents
# =============================================================================


@router.get("/bases/{kb_id}/documents", response_model=DocumentList)
async def list_documents(
    kb_id: UUID,
    source_id: Optional[UUID] = None,
    status: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_aiml_db),
):
    """List documents for a knowledge base."""
    service = KnowledgeService(db)
    documents, total = await service.list_documents(
        kb_id, source_id=source_id, status=status, offset=offset, limit=limit
    )
    return DocumentList(documents=documents, total=total)


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
async def get_document(
    doc_id: UUID,
    include_chunks: bool = False,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Get a document by ID."""
    service = KnowledgeService(db)
    doc = await service.get_document(doc_id, include_chunks=include_chunks)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail(**doc)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Delete a document and its chunks."""
    service = KnowledgeService(db)
    deleted = await service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


# =============================================================================
# Entities
# =============================================================================


@router.get("/bases/{kb_id}/entities", response_model=EntityList)
async def list_entities(
    kb_id: UUID,
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_aiml_db),
):
    """List entities for a knowledge base."""
    service = KnowledgeService(db)
    entities, total = await service.list_entities(
        kb_id, entity_type=entity_type, search=search, offset=offset, limit=limit
    )
    return EntityList(entities=entities, total=total)


@router.get("/entities/{entity_id}", response_model=EntityDetail)
async def get_entity(
    entity_id: UUID,
    include_relationships: bool = True,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Get an entity by ID with relationships."""
    service = KnowledgeService(db)
    entity = await service.get_entity(entity_id, include_relationships=include_relationships)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityDetail(**entity)


# =============================================================================
# Relationships
# =============================================================================


@router.get("/bases/{kb_id}/relationships", response_model=RelationshipList)
async def list_relationships(
    kb_id: UUID,
    relationship_type: Optional[str] = None,
    source_entity_id: Optional[UUID] = None,
    target_entity_id: Optional[UUID] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_aiml_db),
):
    """List relationships for a knowledge base."""
    service = KnowledgeService(db)
    relationships, total = await service.list_relationships(
        kb_id,
        relationship_type=relationship_type,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        offset=offset,
        limit=limit,
    )
    return RelationshipList(relationships=relationships, total=total)


# =============================================================================
# Search
# =============================================================================


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Perform semantic search across knowledge bases."""
    service = KnowledgeService(db)
    results = await service.semantic_search(request)
    return SearchResponse(results=results, query=request.query, total=len(results))


# =============================================================================
# Graph Query
# =============================================================================


@router.post("/graph", response_model=GraphResponse)
async def query_graph(
    request: GraphQueryRequest,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Query the knowledge graph for visualization."""
    service = KnowledgeService(db)
    result = await service.query_graph(request)
    return GraphResponse(**result)


# =============================================================================
# Ingestion
# =============================================================================


@router.post("/bases/{kb_id}/ingest", response_model=IngestionResponse)
async def trigger_ingestion(
    kb_id: UUID,
    request: IngestionRequest = None,
    db: AsyncSession = Depends(get_aiml_db),
):
    """Trigger knowledge ingestion via Airflow."""
    service = KnowledgeService(db)

    request = request or IngestionRequest()
    result = await service.trigger_ingestion(
        kb_id,
        source_id=request.source_id,
        force_reprocess=request.force_reprocess,
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to trigger ingestion. Check Airflow connection.",
        )

    return IngestionResponse(**result)

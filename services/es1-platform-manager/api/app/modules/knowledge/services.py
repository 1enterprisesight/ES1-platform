"""Business logic for knowledge management."""
import json
from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func

from app.core.logging import logger
from app.modules.knowledge.client import ollama_client, airflow_client
from app.modules.knowledge.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    SourceCreate,
    SourceUpdate,
    SearchRequest,
    GraphQueryRequest,
)


class KnowledgeService:
    """Service for knowledge base operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Knowledge Base Operations
    # =========================================================================

    async def list_knowledge_bases(
        self,
        offset: int = 0,
        limit: int = 50,
        include_stats: bool = True,
    ) -> tuple[list[dict], int]:
        """List all knowledge bases with optional stats."""
        # Get knowledge bases
        result = await self.db.execute(
            text("""
                SELECT
                    kb.*,
                    COUNT(DISTINCT d.id) as document_count,
                    COUNT(DISTINCT c.id) as chunk_count,
                    COUNT(DISTINCT e.id) as entity_count
                FROM rag.knowledge_bases kb
                LEFT JOIN rag.documents d ON d.knowledge_base_id = kb.id
                LEFT JOIN rag.chunks c ON c.document_id = d.id
                LEFT JOIN graph.entities e ON e.knowledge_base_id = kb.id
                GROUP BY kb.id
                ORDER BY kb.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        )
        rows = result.mappings().all()

        # Get total count
        count_result = await self.db.execute(
            text("SELECT COUNT(*) FROM rag.knowledge_bases")
        )
        total = count_result.scalar()

        return [dict(row) for row in rows], total

    async def get_knowledge_base(self, kb_id: UUID) -> Optional[dict]:
        """Get a knowledge base by ID with stats."""
        result = await self.db.execute(
            text("""
                SELECT
                    kb.*,
                    COUNT(DISTINCT d.id) as document_count,
                    COUNT(DISTINCT c.id) as chunk_count,
                    COUNT(DISTINCT e.id) as entity_count
                FROM rag.knowledge_bases kb
                LEFT JOIN rag.documents d ON d.knowledge_base_id = kb.id
                LEFT JOIN rag.chunks c ON c.document_id = d.id
                LEFT JOIN graph.entities e ON e.knowledge_base_id = kb.id
                WHERE kb.id = :kb_id
                GROUP BY kb.id
            """),
            {"kb_id": str(kb_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_knowledge_base(self, data: KnowledgeBaseCreate) -> dict:
        """Create a new knowledge base."""
        result = await self.db.execute(
            text("""
                INSERT INTO rag.knowledge_bases (
                    name, description, embedding_model, embedding_dimension,
                    chunking_strategy, chunk_size, chunk_overlap, metadata
                )
                VALUES (
                    :name, :description, :embedding_model, :embedding_dimension,
                    :chunking_strategy, :chunk_size, :chunk_overlap, CAST(:metadata AS jsonb)
                )
                RETURNING *
            """),
            {
                "name": data.name,
                "description": data.description,
                "embedding_model": data.embedding_model,
                "embedding_dimension": data.embedding_dimension,
                "chunking_strategy": data.chunking_strategy.value,
                "chunk_size": data.chunk_size,
                "chunk_overlap": data.chunk_overlap,
                "metadata": json.dumps(data.metadata or {}),
            },
        )
        await self.db.commit()
        row = result.mappings().first()
        return dict(row)

    async def update_knowledge_base(
        self, kb_id: UUID, data: KnowledgeBaseUpdate
    ) -> Optional[dict]:
        """Update a knowledge base."""
        # Build update fields
        updates = []
        params = {"kb_id": str(kb_id)}

        if data.name is not None:
            updates.append("name = :name")
            params["name"] = data.name
        if data.description is not None:
            updates.append("description = :description")
            params["description"] = data.description
        if data.embedding_model is not None:
            updates.append("embedding_model = :embedding_model")
            params["embedding_model"] = data.embedding_model
        if data.chunking_strategy is not None:
            updates.append("chunking_strategy = :chunking_strategy")
            params["chunking_strategy"] = data.chunking_strategy.value
        if data.chunk_size is not None:
            updates.append("chunk_size = :chunk_size")
            params["chunk_size"] = data.chunk_size
        if data.chunk_overlap is not None:
            updates.append("chunk_overlap = :chunk_overlap")
            params["chunk_overlap"] = data.chunk_overlap
        if data.metadata is not None:
            updates.append("metadata = CAST(:metadata AS jsonb)")
            params["metadata"] = json.dumps(data.metadata)

        if not updates:
            return await self.get_knowledge_base(kb_id)

        updates.append("updated_at = NOW()")
        query = f"UPDATE rag.knowledge_bases SET {', '.join(updates)} WHERE id = :kb_id RETURNING *"

        result = await self.db.execute(text(query), params)
        await self.db.commit()
        row = result.mappings().first()
        return dict(row) if row else None

    async def delete_knowledge_base(self, kb_id: UUID) -> bool:
        """Delete a knowledge base and all associated data."""
        # Delete cascades through foreign keys
        result = await self.db.execute(
            text("DELETE FROM rag.knowledge_bases WHERE id = :kb_id"),
            {"kb_id": str(kb_id)},
        )
        await self.db.commit()
        return result.rowcount > 0

    # =========================================================================
    # Source Operations
    # =========================================================================

    async def list_sources(
        self,
        kb_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """List sources for a knowledge base."""
        result = await self.db.execute(
            text("""
                SELECT * FROM rag.sources
                WHERE knowledge_base_id = :kb_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"kb_id": str(kb_id), "limit": limit, "offset": offset},
        )
        rows = result.mappings().all()

        count_result = await self.db.execute(
            text("SELECT COUNT(*) FROM rag.sources WHERE knowledge_base_id = :kb_id"),
            {"kb_id": str(kb_id)},
        )
        total = count_result.scalar()

        return [dict(row) for row in rows], total

    async def get_source(self, source_id: UUID) -> Optional[dict]:
        """Get a source by ID."""
        result = await self.db.execute(
            text("SELECT * FROM rag.sources WHERE id = :source_id"),
            {"source_id": str(source_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_source(self, kb_id: UUID, data: SourceCreate) -> dict:
        """Create a new source."""
        result = await self.db.execute(
            text("""
                INSERT INTO rag.sources (
                    knowledge_base_id, name, source_type, connection_config,
                    description, schedule, metadata
                )
                VALUES (
                    CAST(:kb_id AS uuid), :name, :source_type, CAST(:connection_config AS jsonb),
                    :description, :schedule, CAST(:metadata AS jsonb)
                )
                RETURNING *
            """),
            {
                "kb_id": str(kb_id),
                "name": data.name,
                "source_type": data.source_type.value,
                "connection_config": json.dumps(data.connection_config),
                "description": data.description,
                "schedule": data.schedule,
                "metadata": json.dumps(data.metadata or {}),
            },
        )
        await self.db.commit()
        row = result.mappings().first()
        return dict(row)

    async def update_source(
        self, source_id: UUID, data: SourceUpdate
    ) -> Optional[dict]:
        """Update a source."""
        updates = []
        params = {"source_id": str(source_id)}

        if data.name is not None:
            updates.append("name = :name")
            params["name"] = data.name
        if data.description is not None:
            updates.append("description = :description")
            params["description"] = data.description
        if data.connection_config is not None:
            updates.append("connection_config = CAST(:connection_config AS jsonb)")
            params["connection_config"] = json.dumps(data.connection_config)
        if data.schedule is not None:
            updates.append("schedule = :schedule")
            params["schedule"] = data.schedule
        if data.status is not None:
            updates.append("status = :status")
            params["status"] = data.status.value
        if data.metadata is not None:
            updates.append("metadata = CAST(:metadata AS jsonb)")
            params["metadata"] = json.dumps(data.metadata)

        if not updates:
            return await self.get_source(source_id)

        updates.append("updated_at = NOW()")
        query = f"UPDATE rag.sources SET {', '.join(updates)} WHERE id = :source_id RETURNING *"

        result = await self.db.execute(text(query), params)
        await self.db.commit()
        row = result.mappings().first()
        return dict(row) if row else None

    async def delete_source(self, source_id: UUID) -> bool:
        """Delete a source."""
        result = await self.db.execute(
            text("DELETE FROM rag.sources WHERE id = :source_id"),
            {"source_id": str(source_id)},
        )
        await self.db.commit()
        return result.rowcount > 0

    # =========================================================================
    # Document Operations
    # =========================================================================

    async def list_documents(
        self,
        kb_id: UUID,
        source_id: Optional[UUID] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """List documents for a knowledge base."""
        conditions = ["knowledge_base_id = :kb_id"]
        params = {"kb_id": str(kb_id), "limit": limit, "offset": offset}

        if source_id:
            conditions.append("source_id = :source_id")
            params["source_id"] = str(source_id)
        if status:
            conditions.append("status = :status")
            params["status"] = status

        where_clause = " AND ".join(conditions)

        result = await self.db.execute(
            text(f"""
                SELECT d.*, COUNT(c.id) as chunk_count
                FROM rag.documents d
                LEFT JOIN rag.chunks c ON c.document_id = d.id
                WHERE {where_clause}
                GROUP BY d.id
                ORDER BY d.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.mappings().all()

        count_result = await self.db.execute(
            text(f"SELECT COUNT(*) FROM rag.documents WHERE {where_clause}"),
            {k: v for k, v in params.items() if k not in ["limit", "offset"]},
        )
        total = count_result.scalar()

        return [dict(row) for row in rows], total

    async def get_document(self, doc_id: UUID, include_chunks: bool = False) -> Optional[dict]:
        """Get a document by ID."""
        result = await self.db.execute(
            text("""
                SELECT d.*, COUNT(c.id) as chunk_count
                FROM rag.documents d
                LEFT JOIN rag.chunks c ON c.document_id = d.id
                WHERE d.id = :doc_id
                GROUP BY d.id
            """),
            {"doc_id": str(doc_id)},
        )
        row = result.mappings().first()
        if not row:
            return None

        doc = dict(row)

        if include_chunks:
            chunks_result = await self.db.execute(
                text("""
                    SELECT id, chunk_index, content, start_char, end_char,
                           metadata, embedding_id IS NOT NULL as has_embedding, created_at
                    FROM rag.chunks
                    WHERE document_id = :doc_id
                    ORDER BY chunk_index
                """),
                {"doc_id": str(doc_id)},
            )
            doc["chunks"] = [dict(r) for r in chunks_result.mappings().all()]

        return doc

    async def delete_document(self, doc_id: UUID) -> bool:
        """Delete a document and its chunks."""
        result = await self.db.execute(
            text("DELETE FROM rag.documents WHERE id = :doc_id"),
            {"doc_id": str(doc_id)},
        )
        await self.db.commit()
        return result.rowcount > 0

    # =========================================================================
    # Entity Operations
    # =========================================================================

    async def list_entities(
        self,
        kb_id: UUID,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """List entities for a knowledge base."""
        conditions = ["knowledge_base_id = :kb_id"]
        params = {"kb_id": str(kb_id), "limit": limit, "offset": offset}

        if entity_type:
            conditions.append("entity_type = :entity_type")
            params["entity_type"] = entity_type
        if search:
            conditions.append("(name ILIKE :search OR canonical_name ILIKE :search)")
            params["search"] = f"%{search}%"

        where_clause = " AND ".join(conditions)

        result = await self.db.execute(
            text(f"""
                SELECT e.*,
                    (SELECT COUNT(*) FROM graph.relationships r
                     WHERE r.source_entity_id = e.id OR r.target_entity_id = e.id) as mention_count
                FROM graph.entities e
                WHERE {where_clause}
                ORDER BY e.name
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.mappings().all()

        count_result = await self.db.execute(
            text(f"SELECT COUNT(*) FROM graph.entities WHERE {where_clause}"),
            {k: v for k, v in params.items() if k not in ["limit", "offset"]},
        )
        total = count_result.scalar()

        return [dict(row) for row in rows], total

    async def get_entity(self, entity_id: UUID, include_relationships: bool = False) -> Optional[dict]:
        """Get an entity by ID with optional relationships."""
        result = await self.db.execute(
            text("SELECT * FROM graph.entities WHERE id = :entity_id"),
            {"entity_id": str(entity_id)},
        )
        row = result.mappings().first()
        if not row:
            return None

        entity = dict(row)

        if include_relationships:
            # Get outgoing relationships
            outgoing = await self.db.execute(
                text("""
                    SELECT r.*, e.name as target_entity_name
                    FROM graph.relationships r
                    JOIN graph.entities e ON e.id = r.target_entity_id
                    WHERE r.source_entity_id = :entity_id
                """),
                {"entity_id": str(entity_id)},
            )
            entity["outgoing_relationships"] = [dict(r) for r in outgoing.mappings().all()]

            # Get incoming relationships
            incoming = await self.db.execute(
                text("""
                    SELECT r.*, e.name as source_entity_name
                    FROM graph.relationships r
                    JOIN graph.entities e ON e.id = r.source_entity_id
                    WHERE r.target_entity_id = :entity_id
                """),
                {"entity_id": str(entity_id)},
            )
            entity["incoming_relationships"] = [dict(r) for r in incoming.mappings().all()]

        return entity

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    async def list_relationships(
        self,
        kb_id: UUID,
        relationship_type: Optional[str] = None,
        source_entity_id: Optional[UUID] = None,
        target_entity_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """List relationships for a knowledge base."""
        conditions = ["r.knowledge_base_id = :kb_id"]
        params = {"kb_id": str(kb_id), "limit": limit, "offset": offset}

        if relationship_type:
            conditions.append("r.relationship_type = :relationship_type")
            params["relationship_type"] = relationship_type
        if source_entity_id:
            conditions.append("r.source_entity_id = :source_entity_id")
            params["source_entity_id"] = str(source_entity_id)
        if target_entity_id:
            conditions.append("r.target_entity_id = :target_entity_id")
            params["target_entity_id"] = str(target_entity_id)

        where_clause = " AND ".join(conditions)

        result = await self.db.execute(
            text(f"""
                SELECT r.*,
                    se.name as source_entity_name,
                    te.name as target_entity_name
                FROM graph.relationships r
                JOIN graph.entities se ON se.id = r.source_entity_id
                JOIN graph.entities te ON te.id = r.target_entity_id
                WHERE {where_clause}
                ORDER BY r.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.mappings().all()

        count_result = await self.db.execute(
            text(f"SELECT COUNT(*) FROM graph.relationships r WHERE {where_clause}"),
            {k: v for k, v in params.items() if k not in ["limit", "offset"]},
        )
        total = count_result.scalar()

        return [dict(row) for row in rows], total

    # =========================================================================
    # Search Operations
    # =========================================================================

    async def semantic_search(self, request: SearchRequest) -> list[dict]:
        """Perform semantic search using embeddings."""
        # Generate embedding for query
        embedding = await ollama_client.generate_embedding(request.query)
        if not embedding:
            logger.error("Failed to generate embedding for search query")
            return []

        # Build search query
        conditions = []
        params = {
            "embedding": embedding,
            "limit": request.limit,
        }

        if request.knowledge_base_id:
            conditions.append("d.knowledge_base_id = :kb_id")
            params["kb_id"] = str(request.knowledge_base_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Search using cosine similarity
        result = await self.db.execute(
            text(f"""
                SELECT
                    c.id as chunk_id,
                    c.document_id,
                    d.title as document_title,
                    c.content,
                    c.metadata,
                    d.knowledge_base_id,
                    kb.name as knowledge_base_name,
                    1 - (e.embedding <=> :embedding::vector) as score
                FROM rag.chunks c
                JOIN rag.documents d ON d.id = c.document_id
                JOIN rag.knowledge_bases kb ON kb.id = d.knowledge_base_id
                JOIN vectors.embeddings e ON e.id = c.embedding_id
                {where_clause}
                ORDER BY e.embedding <=> :embedding::vector
                LIMIT :limit
            """),
            params,
        )
        rows = result.mappings().all()

        results = []
        for row in rows:
            r = dict(row)
            if r["score"] >= request.min_score:
                if not request.include_content:
                    r.pop("content", None)
                if not request.include_metadata:
                    r.pop("metadata", None)
                results.append(r)

        return results

    # =========================================================================
    # Graph Query Operations
    # =========================================================================

    async def query_graph(self, request: GraphQueryRequest) -> dict:
        """Query the knowledge graph for visualization."""
        params = {"kb_id": str(request.knowledge_base_id), "limit": request.limit}

        # Build entity query
        entity_conditions = ["knowledge_base_id = :kb_id"]
        if request.entity_types:
            entity_conditions.append("entity_type = ANY(:entity_types)")
            params["entity_types"] = request.entity_types
        if request.root_entity_id:
            # For now, just filter. TODO: implement graph traversal
            entity_conditions.append("id = :root_id")
            params["root_id"] = str(request.root_entity_id)

        entity_where = " AND ".join(entity_conditions)

        # Get entities
        entities_result = await self.db.execute(
            text(f"""
                SELECT id, name, entity_type, properties
                FROM graph.entities
                WHERE {entity_where}
                LIMIT :limit
            """),
            params,
        )
        entities = entities_result.mappings().all()
        entity_ids = [str(e["id"]) for e in entities]

        nodes = [
            {
                "id": str(e["id"]),
                "label": e["name"],
                "type": e["entity_type"],
                "properties": e["properties"],
            }
            for e in entities
        ]

        # Get relationships between these entities
        edges = []
        if entity_ids:
            rel_conditions = ["knowledge_base_id = :kb_id"]
            rel_conditions.append("source_entity_id = ANY(:entity_ids)")
            rel_conditions.append("target_entity_id = ANY(:entity_ids)")

            if request.relationship_types:
                rel_conditions.append("relationship_type = ANY(:rel_types)")
                params["rel_types"] = request.relationship_types

            params["entity_ids"] = entity_ids

            rel_where = " AND ".join(rel_conditions)

            rels_result = await self.db.execute(
                text(f"""
                    SELECT id, source_entity_id, target_entity_id,
                           relationship_type, properties
                    FROM graph.relationships
                    WHERE {rel_where}
                """),
                params,
            )
            relationships = rels_result.mappings().all()

            edges = [
                {
                    "id": str(r["id"]),
                    "source": str(r["source_entity_id"]),
                    "target": str(r["target_entity_id"]),
                    "type": r["relationship_type"],
                    "properties": r["properties"],
                }
                for r in relationships
            ]

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    # =========================================================================
    # Ingestion Operations
    # =========================================================================

    async def trigger_ingestion(
        self,
        kb_id: UUID,
        source_id: Optional[UUID] = None,
        force_reprocess: bool = False,
    ) -> Optional[dict]:
        """Trigger knowledge ingestion via Airflow."""
        # Get knowledge base
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return None

        # Build DAG configuration
        conf = {
            "knowledge_base_id": str(kb_id),
            "force_reprocess": force_reprocess,
        }

        if source_id:
            source = await self.get_source(source_id)
            if not source:
                return None
            conf["source_id"] = str(source_id)
            conf["source_type"] = source["source_type"]
            conf["connection_config"] = source["connection_config"]

        # Determine which DAG to trigger
        dag_id = "knowledge_batch_ingestion"  # Default to batch

        # Trigger the DAG
        result = await airflow_client.trigger_dag(dag_id, conf=conf)

        if result:
            return {
                "message": "Ingestion triggered successfully",
                "dag_run_id": result.get("dag_run_id"),
                "knowledge_base_id": kb_id,
            }
        return None

    # =========================================================================
    # Statistics Operations
    # =========================================================================

    async def get_stats(self) -> dict:
        """Get overall knowledge statistics."""
        result = await self.db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM rag.knowledge_bases) as total_knowledge_bases,
                    (SELECT COUNT(*) FROM rag.sources) as total_sources,
                    (SELECT COUNT(*) FROM rag.documents) as total_documents,
                    (SELECT COUNT(*) FROM rag.chunks) as total_chunks,
                    (SELECT COUNT(*) FROM graph.entities) as total_entities,
                    (SELECT COUNT(*) FROM graph.relationships) as total_relationships
            """)
        )
        row = result.mappings().first()
        return dict(row) if row else {}

    async def get_knowledge_base_stats(self, kb_id: UUID) -> Optional[dict]:
        """Get statistics for a specific knowledge base."""
        result = await self.db.execute(
            text("""
                SELECT
                    kb.id as knowledge_base_id,
                    kb.name,
                    COUNT(DISTINCT d.id) as document_count,
                    COUNT(DISTINCT c.id) as chunk_count,
                    COUNT(DISTINCT e.id) as entity_count,
                    COUNT(DISTINCT r.id) as relationship_count,
                    COUNT(DISTINCT s.id) as source_count,
                    COUNT(DISTINCT CASE WHEN s.status = 'active' THEN s.id END) as active_sources,
                    MAX(s.last_sync) as last_sync
                FROM rag.knowledge_bases kb
                LEFT JOIN rag.documents d ON d.knowledge_base_id = kb.id
                LEFT JOIN rag.chunks c ON c.document_id = d.id
                LEFT JOIN graph.entities e ON e.knowledge_base_id = kb.id
                LEFT JOIN graph.relationships r ON r.knowledge_base_id = kb.id
                LEFT JOIN rag.sources s ON s.knowledge_base_id = kb.id
                WHERE kb.id = :kb_id
                GROUP BY kb.id
            """),
            {"kb_id": str(kb_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

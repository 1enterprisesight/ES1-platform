"""
Database connectors for Knowledge Ingestion Pipeline
Handles connections to both AI/ML and Platform databases
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import logging

from knowledge.config import get_config, DatabaseConfig

logger = logging.getLogger(__name__)


class BaseDatabase:
    """Base database connection class"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._conn = None

    @contextmanager
    def connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password,
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @contextmanager
    def cursor(self, dict_cursor: bool = True):
        """Context manager for database cursors"""
        with self.connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()


class AIMLDatabase(BaseDatabase):
    """Database connector for AI/ML database (vectors, rag, agents, graph schemas)"""

    def __init__(self):
        config = get_config()
        super().__init__(config.aiml_db)

    # ==================== Knowledge Base Operations ====================

    def get_or_create_knowledge_base(
        self,
        name: str,
        description: str = None,
        chunking_strategy: str = "recursive",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> str:
        """Get existing or create new knowledge base, returns ID"""
        with self.cursor() as cur:
            # Check if exists
            cur.execute(
                "SELECT id FROM rag.knowledge_bases WHERE name = %s",
                (name,)
            )
            result = cur.fetchone()
            if result:
                return str(result['id'])

            # Create new
            cur.execute(
                """
                INSERT INTO rag.knowledge_bases
                (name, description, chunking_strategy, chunk_size, chunk_overlap)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (name, description, chunking_strategy, chunk_size, chunk_overlap)
            )
            return str(cur.fetchone()['id'])

    # ==================== Source Operations ====================

    def create_source(
        self,
        name: str,
        source_type: str,
        uri: str = None,
        content_type: str = None,
        metadata: Dict = None,
    ) -> str:
        """Create a new data source, returns ID"""
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rag.sources
                (name, source_type, uri, content_type, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (name, source_type, uri, content_type, json.dumps(metadata or {}))
            )
            return str(cur.fetchone()['id'])

    def update_source_status(
        self,
        source_id: str,
        status: str,
        error: str = None
    ):
        """Update source sync status"""
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE rag.sources
                SET sync_status = %s, sync_error = %s,
                    last_synced_at = CASE WHEN %s = 'completed' THEN NOW() ELSE last_synced_at END,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, error, status, source_id)
            )

    def link_source_to_knowledge_base(self, knowledge_base_id: str, source_id: str):
        """Link a source to a knowledge base"""
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rag.knowledge_base_sources (knowledge_base_id, source_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (knowledge_base_id, source_id)
            )

    # ==================== Document Operations ====================

    def create_document(
        self,
        source_id: str,
        title: str,
        content: str,
        content_type: str = None,
        language: str = "en",
        metadata: Dict = None,
    ) -> Tuple[str, bool]:
        """
        Create a new document or return existing if content unchanged.
        Returns (document_id, is_new)
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        with self.cursor() as cur:
            # Check if document with same hash exists
            cur.execute(
                "SELECT id FROM rag.documents WHERE content_hash = %s AND source_id = %s",
                (content_hash, source_id)
            )
            result = cur.fetchone()
            if result:
                return str(result['id']), False

            # Create new document
            cur.execute(
                """
                INSERT INTO rag.documents
                (source_id, title, content, content_hash, content_type, language, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (source_id, title, content, content_hash, content_type, language,
                 json.dumps(metadata or {}))
            )
            return str(cur.fetchone()['id']), True

    # ==================== Chunk Operations ====================

    def create_chunks(
        self,
        document_id: str,
        chunks: List[Dict],
    ) -> List[str]:
        """
        Bulk create chunks for a document.
        Each chunk dict should have: content, chunk_index, start_char, end_char, token_count
        Returns list of chunk IDs
        """
        if not chunks:
            return []

        with self.cursor() as cur:
            # Prepare data
            values = []
            for chunk in chunks:
                content_hash = hashlib.sha256(chunk['content'].encode()).hexdigest()
                values.append((
                    document_id,
                    chunk['chunk_index'],
                    chunk['content'],
                    content_hash,
                    chunk.get('start_char'),
                    chunk.get('end_char'),
                    chunk.get('token_count'),
                    json.dumps(chunk.get('metadata', {})),
                ))

            # Bulk insert
            result = execute_values(
                cur,
                """
                INSERT INTO rag.chunks
                (document_id, chunk_index, content, content_hash, start_char, end_char, token_count, metadata)
                VALUES %s
                RETURNING id
                """,
                values,
                fetch=True
            )
            return [str(row[0]) for row in result]

    def update_chunk_embedding(self, chunk_id: str, embedding_id: str):
        """Link a chunk to its embedding"""
        with self.cursor() as cur:
            cur.execute(
                "UPDATE rag.chunks SET embedding_id = %s WHERE id = %s",
                (embedding_id, chunk_id)
            )

    # ==================== Embedding Operations ====================

    def get_or_create_collection(
        self,
        name: str,
        embedding_model: str,
        embedding_dimension: int,
        description: str = None,
    ) -> str:
        """Get or create an embedding collection"""
        with self.cursor() as cur:
            cur.execute(
                "SELECT id FROM vectors.collections WHERE name = %s",
                (name,)
            )
            result = cur.fetchone()
            if result:
                return str(result['id'])

            cur.execute(
                """
                INSERT INTO vectors.collections
                (name, description, embedding_model, embedding_dimension)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (name, description, embedding_model, embedding_dimension)
            )
            return str(cur.fetchone()['id'])

    def store_embeddings(
        self,
        collection_id: str,
        embeddings: List[Dict],
        dimension: int = 1536,
    ) -> List[str]:
        """
        Store embeddings in the appropriate table based on dimension.
        Each embedding dict should have: content, embedding (list of floats), metadata
        Returns list of embedding IDs
        """
        if not embeddings:
            return []

        # Select table based on dimension
        table_map = {
            384: "vectors.embeddings_384",
            768: "vectors.embeddings_768",
            1536: "vectors.embeddings",
            4096: "vectors.embeddings_4096",
        }
        table = table_map.get(dimension, "vectors.embeddings")

        with self.cursor() as cur:
            values = []
            for emb in embeddings:
                content_hash = hashlib.sha256(emb['content'].encode()).hexdigest()
                # Convert embedding list to PostgreSQL vector format
                embedding_str = '[' + ','.join(map(str, emb['embedding'])) + ']'
                values.append((
                    collection_id,
                    content_hash,
                    emb['content'],
                    embedding_str,
                    json.dumps(emb.get('metadata', {})),
                ))

            result = execute_values(
                cur,
                f"""
                INSERT INTO {table}
                (collection_id, content_hash, content, embedding, metadata)
                VALUES %s
                RETURNING id
                """,
                values,
                fetch=True
            )
            return [str(row[0]) for row in result]

    # ==================== Entity Operations ====================

    def create_entity(
        self,
        knowledge_base_id: str,
        entity_type: str,
        name: str,
        canonical_name: str = None,
        description: str = None,
        properties: Dict = None,
        source_chunk_ids: List[str] = None,
        extraction_method: str = "llm",
        confidence: float = 1.0,
    ) -> Tuple[str, bool]:
        """
        Create an entity or return existing if same canonical name exists.
        Returns (entity_id, is_new)
        """
        canonical = canonical_name or name.lower().strip()

        with self.cursor() as cur:
            # Check if exists
            cur.execute(
                """
                SELECT id FROM graph.entities
                WHERE knowledge_base_id = %s AND canonical_name = %s AND entity_type = %s
                """,
                (knowledge_base_id, canonical, entity_type)
            )
            result = cur.fetchone()
            if result:
                # Update source_chunk_ids if provided
                if source_chunk_ids:
                    cur.execute(
                        """
                        UPDATE graph.entities
                        SET source_chunk_ids = array_cat(
                            COALESCE(source_chunk_ids, ARRAY[]::uuid[]),
                            %s::uuid[]
                        ),
                        updated_at = NOW()
                        WHERE id = %s
                        """,
                        (source_chunk_ids, result['id'])
                    )
                return str(result['id']), False

            # Create new
            cur.execute(
                """
                INSERT INTO graph.entities
                (knowledge_base_id, entity_type, name, canonical_name, description,
                 properties, source_chunk_ids, extraction_method, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (knowledge_base_id, entity_type, name, canonical, description,
                 json.dumps(properties or {}), source_chunk_ids, extraction_method, confidence)
            )
            return str(cur.fetchone()['id']), True

    def create_relationship(
        self,
        knowledge_base_id: str,
        source_entity_id: str,
        relationship_type: str,
        target_entity_id: str,
        properties: Dict = None,
        source_chunk_ids: List[str] = None,
        confidence: float = 1.0,
    ) -> Tuple[str, bool]:
        """
        Create a relationship or return existing.
        Returns (relationship_id, is_new)
        """
        with self.cursor() as cur:
            # Check if exists
            cur.execute(
                """
                SELECT id FROM graph.relationships
                WHERE knowledge_base_id = %s
                  AND source_entity_id = %s
                  AND relationship_type = %s
                  AND target_entity_id = %s
                """,
                (knowledge_base_id, source_entity_id, relationship_type, target_entity_id)
            )
            result = cur.fetchone()
            if result:
                return str(result['id']), False

            cur.execute(
                """
                INSERT INTO graph.relationships
                (knowledge_base_id, source_entity_id, relationship_type, target_entity_id,
                 properties, source_chunk_ids, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (knowledge_base_id, source_entity_id, relationship_type, target_entity_id,
                 json.dumps(properties or {}), source_chunk_ids, confidence)
            )
            return str(cur.fetchone()['id']), True


class PlatformDatabase(BaseDatabase):
    """Database connector for Platform database (audit schema)"""

    def __init__(self):
        config = get_config()
        super().__init__(config.platform_db)

    def log_api_request(
        self,
        request_id: str,
        source_service: str,
        destination_service: str,
        method: str,
        path: str,
        response_status: int,
        latency_ms: int,
        metadata: Dict = None,
    ):
        """Log an API request to the audit table"""
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit.api_requests
                (request_id, source_service, destination_service, method, path,
                 response_status, latency_ms, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (request_id, source_service, destination_service, method, path,
                 response_status, latency_ms, json.dumps(metadata or {}))
            )

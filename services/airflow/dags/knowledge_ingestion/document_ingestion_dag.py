"""
Document Ingestion DAG
Processes documents from various sources into the knowledge graph
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import logging

logger = logging.getLogger(__name__)

# DAG Configuration
default_args = {
    'owner': 'es1-platform',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'knowledge_document_ingestion',
    default_args=default_args,
    description='Ingest documents into the ES1 knowledge graph',
    schedule_interval=None,  # Triggered via API
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['knowledge', 'ingestion', 'rag'],
    params={
        'knowledge_base_name': 'default',
        'source_type': 'file',  # file, url, s3, database
        'source_uri': '',
        'content_type': 'auto',
        'chunking_strategy': 'recursive',
        'chunk_size': 512,
        'chunk_overlap': 50,
        'extract_entities': True,
        'generate_embeddings': True,
    },
) as dag:

    @task(task_id='setup_ingestion')
    def setup_ingestion(**context):
        """
        Initialize ingestion job and create/get knowledge base
        """
        from knowledge import AIMLDatabase, get_config

        params = context['params']
        db = AIMLDatabase()

        # Create or get knowledge base
        kb_id = db.get_or_create_knowledge_base(
            name=params['knowledge_base_name'],
            description=f"Knowledge base: {params['knowledge_base_name']}",
            chunking_strategy=params['chunking_strategy'],
            chunk_size=params['chunk_size'],
            chunk_overlap=params['chunk_overlap'],
        )

        # Create source record
        source_id = db.create_source(
            name=f"{params['source_type']}:{params['source_uri']}",
            source_type=params['source_type'],
            uri=params['source_uri'],
            content_type=params['content_type'],
            metadata={
                'dag_run_id': context['dag_run'].run_id,
                'started_at': datetime.utcnow().isoformat(),
            }
        )

        # Link source to knowledge base
        db.link_source_to_knowledge_base(kb_id, source_id)

        logger.info(f"Setup complete: kb_id={kb_id}, source_id={source_id}")

        return {
            'knowledge_base_id': kb_id,
            'source_id': source_id,
            'params': params,
        }

    @task(task_id='fetch_content')
    def fetch_content(setup_data: dict, **context):
        """
        Fetch content from the source
        """
        import requests
        from pathlib import Path

        params = setup_data['params']
        source_type = params['source_type']
        source_uri = params['source_uri']

        content = None
        content_type = params['content_type']
        filename = None

        if source_type == 'file':
            path = Path(source_uri)
            if path.exists():
                content = path.read_bytes()
                filename = path.name
                if content_type == 'auto':
                    content_type = _detect_content_type(filename)
            else:
                raise FileNotFoundError(f"File not found: {source_uri}")

        elif source_type == 'url':
            response = requests.get(source_uri, timeout=60)
            response.raise_for_status()
            content = response.content
            content_type = response.headers.get('Content-Type', 'text/html').split(';')[0]
            filename = source_uri.split('/')[-1] or 'document'

        elif source_type == 's3':
            # S3 fetching would be implemented here
            raise NotImplementedError("S3 source not yet implemented")

        else:
            raise ValueError(f"Unknown source type: {source_type}")

        logger.info(f"Fetched content: {len(content)} bytes, type={content_type}")

        return {
            **setup_data,
            'content': content.decode('utf-8', errors='replace') if isinstance(content, bytes) else content,
            'content_bytes': len(content) if content else 0,
            'content_type': content_type,
            'filename': filename,
        }

    @task(task_id='process_document')
    def process_document(fetch_data: dict, **context):
        """
        Parse and chunk the document
        """
        from knowledge import DocumentProcessor, FileParser, ChunkingStrategy

        params = fetch_data['params']

        # Parse file if needed
        parser = FileParser()
        text, file_metadata = parser.parse(
            fetch_data['content'].encode('utf-8'),
            fetch_data['content_type'],
            fetch_data['filename'],
        )

        # Process and chunk
        processor = DocumentProcessor(
            chunk_size=params['chunk_size'],
            chunk_overlap=params['chunk_overlap'],
            strategy=ChunkingStrategy(params['chunking_strategy']),
        )

        processed = processor.process(
            content=text,
            title=fetch_data['filename'],
            content_type=fetch_data['content_type'],
            metadata=file_metadata,
        )

        chunks = processor.chunks_to_dicts(processed.chunks)

        logger.info(f"Processed document: {len(text)} chars, {len(chunks)} chunks")

        return {
            **fetch_data,
            'title': processed.title,
            'processed_content': processed.content,
            'chunks': chunks,
            'chunk_count': len(chunks),
            'file_metadata': file_metadata,
        }

    @task(task_id='store_document')
    def store_document(process_data: dict, **context):
        """
        Store document and chunks in the database
        """
        from knowledge import AIMLDatabase

        db = AIMLDatabase()

        # Create document
        doc_id, is_new = db.create_document(
            source_id=process_data['source_id'],
            title=process_data['title'],
            content=process_data['processed_content'],
            content_type=process_data['content_type'],
            metadata=process_data.get('file_metadata', {}),
        )

        if not is_new:
            logger.info(f"Document already exists: {doc_id}")
            return {
                **process_data,
                'document_id': doc_id,
                'document_is_new': False,
                'chunk_ids': [],
            }

        # Create chunks
        chunk_ids = db.create_chunks(doc_id, process_data['chunks'])

        # Add chunk IDs to chunk data for later use
        for chunk, chunk_id in zip(process_data['chunks'], chunk_ids):
            chunk['id'] = chunk_id

        logger.info(f"Stored document: {doc_id} with {len(chunk_ids)} chunks")

        return {
            **process_data,
            'document_id': doc_id,
            'document_is_new': True,
            'chunk_ids': chunk_ids,
        }

    @task(task_id='generate_embeddings')
    def generate_embeddings(store_data: dict, **context):
        """
        Generate embeddings for chunks using Ollama
        """
        from knowledge import AIMLDatabase, OllamaEmbeddings

        if not store_data['params'].get('generate_embeddings', True):
            logger.info("Embedding generation skipped")
            return store_data

        if not store_data.get('document_is_new', True):
            logger.info("Document unchanged, skipping embeddings")
            return store_data

        db = AIMLDatabase()
        embeddings = OllamaEmbeddings()

        # Ensure model is available
        embeddings._ensure_model_available()

        # Get or create collection
        collection_id = db.get_or_create_collection(
            name=f"kb_{store_data['knowledge_base_id']}",
            embedding_model=embeddings.model,
            embedding_dimension=embeddings.dimension,
            description=f"Embeddings for {store_data['params']['knowledge_base_name']}",
        )

        # Generate embeddings for chunks
        chunks_with_embeddings = embeddings.embed_chunks(store_data['chunks'])

        # Store embeddings
        embedding_data = [
            {
                'content': chunk['content'],
                'embedding': chunk['embedding'],
                'metadata': {
                    'chunk_id': chunk['id'],
                    'document_id': store_data['document_id'],
                    'chunk_index': chunk['chunk_index'],
                },
            }
            for chunk in chunks_with_embeddings
            if chunk['embedding']  # Skip failed embeddings
        ]

        embedding_ids = db.store_embeddings(
            collection_id=collection_id,
            embeddings=embedding_data,
            dimension=embeddings.dimension,
        )

        # Update chunks with embedding IDs
        for chunk, emb_id in zip(chunks_with_embeddings, embedding_ids):
            if chunk.get('id'):
                db.update_chunk_embedding(chunk['id'], emb_id)

        logger.info(f"Generated {len(embedding_ids)} embeddings")

        return {
            **store_data,
            'collection_id': collection_id,
            'embedding_count': len(embedding_ids),
        }

    @task(task_id='extract_entities')
    def extract_entities(embed_data: dict, **context):
        """
        Extract entities and relationships from chunks
        """
        from knowledge import AIMLDatabase, EntityExtractor, entities_to_dicts, relationships_to_dicts

        if not embed_data['params'].get('extract_entities', True):
            logger.info("Entity extraction skipped")
            return embed_data

        if not embed_data.get('document_is_new', True):
            logger.info("Document unchanged, skipping extraction")
            return embed_data

        db = AIMLDatabase()
        extractor = EntityExtractor()

        # Extract from chunks
        entities, relationships, entity_chunk_map = extractor.extract_from_chunks(
            embed_data['chunks']
        )

        logger.info(f"Extracted {len(entities)} entities, {len(relationships)} relationships")

        # Store entities
        entity_id_map = {}  # canonical_name -> entity_id
        for entity in entities:
            chunk_ids = entity_chunk_map.get(entity.canonical_name, [])
            entity_id, is_new = db.create_entity(
                knowledge_base_id=embed_data['knowledge_base_id'],
                entity_type=entity.entity_type,
                name=entity.name,
                canonical_name=entity.canonical_name,
                description=entity.description,
                properties=entity.properties,
                source_chunk_ids=chunk_ids,
                extraction_method=entity.source,
                confidence=entity.confidence,
            )
            entity_id_map[entity.canonical_name] = entity_id

        # Store relationships
        relationship_count = 0
        for rel in relationships:
            source_id = entity_id_map.get(rel.source_entity)
            target_id = entity_id_map.get(rel.target_entity)
            if source_id and target_id:
                db.create_relationship(
                    knowledge_base_id=embed_data['knowledge_base_id'],
                    source_entity_id=source_id,
                    relationship_type=rel.relationship_type,
                    target_entity_id=target_id,
                    properties=rel.properties,
                    confidence=rel.confidence,
                )
                relationship_count += 1

        logger.info(f"Stored {len(entity_id_map)} entities, {relationship_count} relationships")

        return {
            **embed_data,
            'entity_count': len(entity_id_map),
            'relationship_count': relationship_count,
        }

    @task(task_id='finalize_ingestion')
    def finalize_ingestion(extract_data: dict, **context):
        """
        Update source status and log completion
        """
        from knowledge import AIMLDatabase

        db = AIMLDatabase()

        # Update source status
        db.update_source_status(
            source_id=extract_data['source_id'],
            status='completed',
        )

        # Summary
        summary = {
            'knowledge_base_id': extract_data['knowledge_base_id'],
            'source_id': extract_data['source_id'],
            'document_id': extract_data.get('document_id'),
            'chunk_count': extract_data.get('chunk_count', 0),
            'embedding_count': extract_data.get('embedding_count', 0),
            'entity_count': extract_data.get('entity_count', 0),
            'relationship_count': extract_data.get('relationship_count', 0),
            'document_is_new': extract_data.get('document_is_new', False),
        }

        logger.info(f"Ingestion complete: {summary}")
        return summary


    def _detect_content_type(filename: str) -> str:
        """Detect content type from filename"""
        ext_map = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.csv': 'text/csv',
        }
        ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext_map.get(ext, 'text/plain')


    # Define task dependencies
    setup = setup_ingestion()
    fetched = fetch_content(setup)
    processed = process_document(fetched)
    stored = store_document(processed)
    embedded = generate_embeddings(stored)
    extracted = extract_entities(embedded)
    final = finalize_ingestion(extracted)

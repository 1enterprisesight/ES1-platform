"""
Batch Document Ingestion DAG
Processes multiple documents from a directory or list of URLs
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import PythonOperator
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'es1-platform',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    'knowledge_batch_ingestion',
    default_args=default_args,
    description='Batch ingest multiple documents into the knowledge graph',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['knowledge', 'ingestion', 'batch', 'rag'],
    params={
        'knowledge_base_name': 'default',
        'source_type': 'directory',  # directory, url_list
        'source_path': '',  # directory path or JSON list of URLs
        'file_pattern': '*.txt',  # glob pattern for directory
        'chunking_strategy': 'recursive',
        'chunk_size': 512,
        'chunk_overlap': 50,
        'extract_entities': True,
        'generate_embeddings': True,
        'max_files': 100,
        'parallel_workers': 4,
    },
) as dag:

    @task(task_id='discover_documents')
    def discover_documents(**context):
        """
        Discover documents to process based on source type
        """
        import json
        from pathlib import Path
        import fnmatch

        params = context['params']
        source_type = params['source_type']
        source_path = params['source_path']

        documents = []

        if source_type == 'directory':
            base_path = Path(source_path)
            if not base_path.exists():
                raise FileNotFoundError(f"Directory not found: {source_path}")

            pattern = params.get('file_pattern', '*')
            for file_path in base_path.rglob(pattern):
                if file_path.is_file():
                    documents.append({
                        'source_type': 'file',
                        'source_uri': str(file_path),
                        'filename': file_path.name,
                    })

        elif source_type == 'url_list':
            # source_path should be a JSON array of URLs or a file containing them
            if source_path.startswith('['):
                urls = json.loads(source_path)
            else:
                path = Path(source_path)
                if path.exists():
                    urls = json.loads(path.read_text())
                else:
                    urls = source_path.split(',')

            for url in urls:
                url = url.strip()
                if url:
                    documents.append({
                        'source_type': 'url',
                        'source_uri': url,
                        'filename': url.split('/')[-1] or 'document',
                    })

        else:
            raise ValueError(f"Unknown source type: {source_type}")

        # Limit number of files
        max_files = params.get('max_files', 100)
        if len(documents) > max_files:
            logger.warning(f"Limiting to {max_files} documents (found {len(documents)})")
            documents = documents[:max_files]

        logger.info(f"Discovered {len(documents)} documents to process")

        return {
            'documents': documents,
            'total_count': len(documents),
            'params': params,
        }

    @task(task_id='setup_batch')
    def setup_batch(discover_data: dict, **context):
        """
        Create knowledge base and batch source record
        """
        from knowledge import AIMLDatabase

        params = discover_data['params']
        db = AIMLDatabase()

        # Create or get knowledge base
        kb_id = db.get_or_create_knowledge_base(
            name=params['knowledge_base_name'],
            description=f"Batch ingested knowledge base: {params['knowledge_base_name']}",
            chunking_strategy=params['chunking_strategy'],
            chunk_size=params['chunk_size'],
            chunk_overlap=params['chunk_overlap'],
        )

        # Create batch source
        source_id = db.create_source(
            name=f"batch:{params['source_type']}",
            source_type='batch',
            uri=params['source_path'],
            metadata={
                'document_count': discover_data['total_count'],
                'dag_run_id': context['dag_run'].run_id,
            }
        )

        db.link_source_to_knowledge_base(kb_id, source_id)

        logger.info(f"Batch setup: kb_id={kb_id}, source_id={source_id}")

        return {
            **discover_data,
            'knowledge_base_id': kb_id,
            'batch_source_id': source_id,
        }

    @task(task_id='process_documents')
    def process_documents(setup_data: dict, **context):
        """
        Process all documents in parallel
        """
        from knowledge import (
            AIMLDatabase, OllamaEmbeddings, DocumentProcessor,
            FileParser, EntityExtractor, ChunkingStrategy
        )
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import requests
        from pathlib import Path

        params = setup_data['params']
        documents = setup_data['documents']
        kb_id = setup_data['knowledge_base_id']

        db = AIMLDatabase()
        processor = DocumentProcessor(
            chunk_size=params['chunk_size'],
            chunk_overlap=params['chunk_overlap'],
            strategy=ChunkingStrategy(params['chunking_strategy']),
        )
        parser = FileParser()
        embeddings = OllamaEmbeddings() if params.get('generate_embeddings', True) else None
        extractor = EntityExtractor() if params.get('extract_entities', True) else None

        # Ensure embedding model is available
        if embeddings:
            embeddings._ensure_model_available()
            collection_id = db.get_or_create_collection(
                name=f"kb_{kb_id}",
                embedding_model=embeddings.model,
                embedding_dimension=embeddings.dimension,
            )
        else:
            collection_id = None

        results = {
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'total_chunks': 0,
            'total_embeddings': 0,
            'total_entities': 0,
            'errors': [],
        }

        def process_single_document(doc_info):
            """Process a single document"""
            try:
                # Fetch content
                if doc_info['source_type'] == 'file':
                    path = Path(doc_info['source_uri'])
                    content = path.read_bytes()
                    content_type = _detect_content_type(path.name)
                elif doc_info['source_type'] == 'url':
                    response = requests.get(doc_info['source_uri'], timeout=60)
                    response.raise_for_status()
                    content = response.content
                    content_type = response.headers.get('Content-Type', 'text/html').split(';')[0]
                else:
                    return {'status': 'failed', 'error': 'Unknown source type'}

                # Parse content
                text, file_metadata = parser.parse(content, content_type, doc_info['filename'])
                if not text.strip():
                    return {'status': 'skipped', 'reason': 'Empty content'}

                # Process and chunk
                processed = processor.process(
                    content=text,
                    title=doc_info['filename'],
                    content_type=content_type,
                    metadata=file_metadata,
                )
                chunks = processor.chunks_to_dicts(processed.chunks)

                # Create document-level source
                source_id = db.create_source(
                    name=doc_info['filename'],
                    source_type=doc_info['source_type'],
                    uri=doc_info['source_uri'],
                    content_type=content_type,
                )
                db.link_source_to_knowledge_base(kb_id, source_id)

                # Store document
                doc_id, is_new = db.create_document(
                    source_id=source_id,
                    title=processed.title,
                    content=processed.content,
                    content_type=content_type,
                    metadata=file_metadata,
                )

                if not is_new:
                    db.update_source_status(source_id, 'completed')
                    return {'status': 'skipped', 'reason': 'Already exists'}

                # Store chunks
                chunk_ids = db.create_chunks(doc_id, chunks)
                for chunk, chunk_id in zip(chunks, chunk_ids):
                    chunk['id'] = chunk_id

                chunk_count = len(chunk_ids)
                embedding_count = 0
                entity_count = 0

                # Generate embeddings
                if embeddings and collection_id:
                    chunks_with_emb = embeddings.embed_chunks(chunks)
                    emb_data = [
                        {
                            'content': c['content'],
                            'embedding': c['embedding'],
                            'metadata': {'chunk_id': c['id'], 'document_id': doc_id},
                        }
                        for c in chunks_with_emb if c['embedding']
                    ]
                    if emb_data:
                        emb_ids = db.store_embeddings(collection_id, emb_data, embeddings.dimension)
                        for c, eid in zip(chunks_with_emb, emb_ids):
                            db.update_chunk_embedding(c['id'], eid)
                        embedding_count = len(emb_ids)

                # Extract entities
                if extractor:
                    entities, relationships, entity_map = extractor.extract_from_chunks(chunks)
                    entity_id_map = {}
                    for entity in entities:
                        eid, _ = db.create_entity(
                            knowledge_base_id=kb_id,
                            entity_type=entity.entity_type,
                            name=entity.name,
                            canonical_name=entity.canonical_name,
                            description=entity.description,
                            properties=entity.properties,
                            source_chunk_ids=entity_map.get(entity.canonical_name, []),
                            extraction_method=entity.source,
                            confidence=entity.confidence,
                        )
                        entity_id_map[entity.canonical_name] = eid

                    for rel in relationships:
                        src_id = entity_id_map.get(rel.source_entity)
                        tgt_id = entity_id_map.get(rel.target_entity)
                        if src_id and tgt_id:
                            db.create_relationship(
                                knowledge_base_id=kb_id,
                                source_entity_id=src_id,
                                relationship_type=rel.relationship_type,
                                target_entity_id=tgt_id,
                                confidence=rel.confidence,
                            )

                    entity_count = len(entity_id_map)

                db.update_source_status(source_id, 'completed')

                return {
                    'status': 'processed',
                    'chunks': chunk_count,
                    'embeddings': embedding_count,
                    'entities': entity_count,
                }

            except Exception as e:
                logger.error(f"Error processing {doc_info.get('filename', 'unknown')}: {e}")
                return {'status': 'failed', 'error': str(e)}

        # Process documents in parallel
        max_workers = params.get('parallel_workers', 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_single_document, doc): doc
                for doc in documents
            }

            for future in as_completed(futures):
                doc = futures[future]
                try:
                    result = future.result()
                    if result['status'] == 'processed':
                        results['processed'] += 1
                        results['total_chunks'] += result.get('chunks', 0)
                        results['total_embeddings'] += result.get('embeddings', 0)
                        results['total_entities'] += result.get('entities', 0)
                    elif result['status'] == 'skipped':
                        results['skipped'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'document': doc.get('filename'),
                            'error': result.get('error'),
                        })
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'document': doc.get('filename'),
                        'error': str(e),
                    })

        logger.info(f"Batch processing complete: {results}")
        return {**setup_data, 'results': results}

    @task(task_id='finalize_batch')
    def finalize_batch(process_data: dict, **context):
        """
        Update batch source status and return summary
        """
        from knowledge import AIMLDatabase

        db = AIMLDatabase()
        results = process_data['results']

        # Determine status
        if results['failed'] > 0 and results['processed'] == 0:
            status = 'failed'
        elif results['failed'] > 0:
            status = 'partial'
        else:
            status = 'completed'

        db.update_source_status(
            source_id=process_data['batch_source_id'],
            status=status,
            error=str(results['errors'][:5]) if results['errors'] else None,
        )

        summary = {
            'knowledge_base_id': process_data['knowledge_base_id'],
            'batch_source_id': process_data['batch_source_id'],
            'status': status,
            'documents_processed': results['processed'],
            'documents_skipped': results['skipped'],
            'documents_failed': results['failed'],
            'total_chunks': results['total_chunks'],
            'total_embeddings': results['total_embeddings'],
            'total_entities': results['total_entities'],
        }

        logger.info(f"Batch ingestion complete: {summary}")
        return summary


    def _detect_content_type(filename: str) -> str:
        """Detect content type from filename"""
        ext_map = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.csv': 'text/csv',
        }
        ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext_map.get(ext, 'text/plain')


    # Task dependencies
    discovered = discover_documents()
    setup = setup_batch(discovered)
    processed = process_documents(setup)
    final = finalize_batch(processed)

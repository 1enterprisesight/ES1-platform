"""
Web Scraper DAG
Crawls websites and ingests content into the knowledge graph
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'es1-platform',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'knowledge_web_scraper',
    default_args=default_args,
    description='Crawl websites and ingest into knowledge graph',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['knowledge', 'ingestion', 'web', 'scraper'],
    params={
        'knowledge_base_name': 'web_content',
        'start_url': '',
        'max_pages': 50,
        'max_depth': 2,
        'same_domain_only': True,
        'allowed_paths': [],  # List of path prefixes to include
        'excluded_paths': ['/login', '/logout', '/admin', '/api'],
        'chunking_strategy': 'recursive',
        'chunk_size': 512,
        'chunk_overlap': 50,
        'extract_entities': True,
        'generate_embeddings': True,
        'request_delay': 1.0,  # Seconds between requests
    },
) as dag:

    @task(task_id='crawl_website')
    def crawl_website(**context):
        """
        Crawl website starting from start_url
        """
        import requests
        from urllib.parse import urljoin, urlparse
        from collections import deque
        import time
        import re

        params = context['params']
        start_url = params['start_url']
        max_pages = params.get('max_pages', 50)
        max_depth = params.get('max_depth', 2)
        same_domain_only = params.get('same_domain_only', True)
        allowed_paths = params.get('allowed_paths', [])
        excluded_paths = params.get('excluded_paths', [])
        request_delay = params.get('request_delay', 1.0)

        if not start_url:
            raise ValueError("start_url parameter is required")

        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc

        # BFS crawl
        visited = set()
        pages = []
        queue = deque([(start_url, 0)])  # (url, depth)

        headers = {
            'User-Agent': 'ES1-Platform-Knowledge-Bot/1.0 (Knowledge Ingestion)',
        }

        while queue and len(pages) < max_pages:
            url, depth = queue.popleft()

            if url in visited:
                continue

            if depth > max_depth:
                continue

            parsed_url = urlparse(url)

            # Check domain
            if same_domain_only and parsed_url.netloc != base_domain:
                continue

            # Check allowed/excluded paths
            path = parsed_url.path
            if allowed_paths and not any(path.startswith(p) for p in allowed_paths):
                continue
            if any(path.startswith(p) for p in excluded_paths):
                continue

            visited.add(url)

            try:
                time.sleep(request_delay)
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()

                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    continue

                html = response.text

                # Extract title
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else url

                pages.append({
                    'url': url,
                    'title': title,
                    'content': html,
                    'content_type': 'text/html',
                    'depth': depth,
                })

                logger.info(f"Crawled: {url} (depth={depth}, pages={len(pages)})")

                # Extract links for further crawling
                if depth < max_depth:
                    link_pattern = r'href=["\']([^"\']+)["\']'
                    links = re.findall(link_pattern, html)

                    for link in links:
                        # Skip non-page links
                        if link.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                            continue

                        # Resolve relative URLs
                        full_url = urljoin(url, link)

                        # Clean up URL (remove fragments)
                        parsed = urlparse(full_url)
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        if parsed.query:
                            clean_url += f"?{parsed.query}"

                        if clean_url not in visited:
                            queue.append((clean_url, depth + 1))

            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to crawl {url}: {e}")
                continue

        logger.info(f"Crawl complete: {len(pages)} pages collected")

        return {
            'pages': pages,
            'total_pages': len(pages),
            'base_domain': base_domain,
            'params': params,
        }

    @task(task_id='setup_knowledge_base')
    def setup_knowledge_base(crawl_data: dict, **context):
        """
        Create knowledge base and batch source for the crawl
        """
        from knowledge import AIMLDatabase

        params = crawl_data['params']
        db = AIMLDatabase()

        kb_id = db.get_or_create_knowledge_base(
            name=params['knowledge_base_name'],
            description=f"Web content from {crawl_data['base_domain']}",
            chunking_strategy=params['chunking_strategy'],
            chunk_size=params['chunk_size'],
            chunk_overlap=params['chunk_overlap'],
        )

        source_id = db.create_source(
            name=f"web_crawl:{crawl_data['base_domain']}",
            source_type='web_crawl',
            uri=params['start_url'],
            metadata={
                'pages_crawled': crawl_data['total_pages'],
                'max_depth': params.get('max_depth', 2),
                'dag_run_id': context['dag_run'].run_id,
            }
        )

        db.link_source_to_knowledge_base(kb_id, source_id)

        return {
            **crawl_data,
            'knowledge_base_id': kb_id,
            'crawl_source_id': source_id,
        }

    @task(task_id='process_pages')
    def process_pages(setup_data: dict, **context):
        """
        Process all crawled pages: parse, chunk, embed, extract
        """
        from knowledge import (
            AIMLDatabase, OllamaEmbeddings, DocumentProcessor,
            FileParser, EntityExtractor, ChunkingStrategy
        )

        params = setup_data['params']
        pages = setup_data['pages']
        kb_id = setup_data['knowledge_base_id']

        db = AIMLDatabase()
        processor = DocumentProcessor(
            chunk_size=params['chunk_size'],
            chunk_overlap=params['chunk_overlap'],
            strategy=ChunkingStrategy(params['chunking_strategy']),
        )
        parser = FileParser()

        embeddings = None
        collection_id = None
        if params.get('generate_embeddings', True):
            embeddings = OllamaEmbeddings()
            embeddings._ensure_model_available()
            collection_id = db.get_or_create_collection(
                name=f"kb_{kb_id}",
                embedding_model=embeddings.model,
                embedding_dimension=embeddings.dimension,
            )

        extractor = EntityExtractor() if params.get('extract_entities', True) else None

        results = {
            'processed': 0,
            'failed': 0,
            'total_chunks': 0,
            'total_embeddings': 0,
            'total_entities': 0,
        }

        for page in pages:
            try:
                # Parse HTML
                text, metadata = parser.parse_html(page['content'].encode('utf-8'))
                if not text.strip():
                    continue

                # Process and chunk
                processed = processor.process(
                    content=text,
                    title=page['title'],
                    content_type='text/html',
                    metadata={'url': page['url'], 'depth': page['depth'], **metadata},
                )
                chunks = processor.chunks_to_dicts(processed.chunks)

                # Create source for this page
                page_source_id = db.create_source(
                    name=page['title'][:255],
                    source_type='webpage',
                    uri=page['url'],
                    content_type='text/html',
                )
                db.link_source_to_knowledge_base(kb_id, page_source_id)

                # Store document
                doc_id, is_new = db.create_document(
                    source_id=page_source_id,
                    title=page['title'],
                    content=processed.content,
                    content_type='text/html',
                    metadata={'url': page['url']},
                )

                if not is_new:
                    db.update_source_status(page_source_id, 'completed')
                    continue

                # Store chunks
                chunk_ids = db.create_chunks(doc_id, chunks)
                for chunk, cid in zip(chunks, chunk_ids):
                    chunk['id'] = cid

                results['total_chunks'] += len(chunk_ids)

                # Generate embeddings
                if embeddings and collection_id:
                    chunks_with_emb = embeddings.embed_chunks(chunks)
                    emb_data = [
                        {
                            'content': c['content'],
                            'embedding': c['embedding'],
                            'metadata': {'chunk_id': c['id'], 'document_id': doc_id, 'url': page['url']},
                        }
                        for c in chunks_with_emb if c['embedding']
                    ]
                    if emb_data:
                        emb_ids = db.store_embeddings(collection_id, emb_data, embeddings.dimension)
                        for c, eid in zip(chunks_with_emb, emb_ids):
                            if c.get('id'):
                                db.update_chunk_embedding(c['id'], eid)
                        results['total_embeddings'] += len(emb_ids)

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
                            properties={'source_url': page['url'], **entity.properties},
                            source_chunk_ids=entity_map.get(entity.canonical_name, []),
                            extraction_method=entity.source,
                            confidence=entity.confidence,
                        )
                        entity_id_map[entity.canonical_name] = eid

                    for rel in relationships:
                        src = entity_id_map.get(rel.source_entity)
                        tgt = entity_id_map.get(rel.target_entity)
                        if src and tgt:
                            db.create_relationship(
                                knowledge_base_id=kb_id,
                                source_entity_id=src,
                                relationship_type=rel.relationship_type,
                                target_entity_id=tgt,
                                confidence=rel.confidence,
                            )

                    results['total_entities'] += len(entity_id_map)

                db.update_source_status(page_source_id, 'completed')
                results['processed'] += 1

            except Exception as e:
                logger.error(f"Failed to process page {page.get('url')}: {e}")
                results['failed'] += 1

        logger.info(f"Page processing complete: {results}")

        return {**setup_data, 'results': results}

    @task(task_id='finalize_crawl')
    def finalize_crawl(process_data: dict, **context):
        """
        Update crawl source status and return summary
        """
        from knowledge import AIMLDatabase

        db = AIMLDatabase()
        results = process_data['results']

        status = 'completed' if results['failed'] == 0 else 'partial'
        db.update_source_status(
            source_id=process_data['crawl_source_id'],
            status=status,
        )

        summary = {
            'knowledge_base_id': process_data['knowledge_base_id'],
            'crawl_source_id': process_data['crawl_source_id'],
            'base_domain': process_data['base_domain'],
            'pages_crawled': process_data['total_pages'],
            'pages_processed': results['processed'],
            'pages_failed': results['failed'],
            'total_chunks': results['total_chunks'],
            'total_embeddings': results['total_embeddings'],
            'total_entities': results['total_entities'],
        }

        logger.info(f"Web crawl complete: {summary}")
        return summary


    # Task dependencies
    crawled = crawl_website()
    setup = setup_knowledge_base(crawled)
    processed = process_pages(setup)
    final = finalize_crawl(processed)

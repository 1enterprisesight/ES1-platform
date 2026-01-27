# Knowledge Ingestion Plugin for Airflow
# Provides utilities for document processing, embedding generation, and knowledge graph operations

from knowledge.config import KnowledgeConfig, get_config
from knowledge.database import AIMLDatabase, PlatformDatabase
from knowledge.embeddings import OllamaEmbeddings, EmbeddingResult
from knowledge.processors import (
    DocumentProcessor,
    ChunkingStrategy,
    FileParser,
    TextCleaner,
    ProcessedDocument,
    Chunk,
)
from knowledge.extractors import (
    EntityExtractor,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionResult,
    entities_to_dicts,
    relationships_to_dicts,
)

__all__ = [
    # Config
    'KnowledgeConfig',
    'get_config',
    # Database
    'AIMLDatabase',
    'PlatformDatabase',
    # Embeddings
    'OllamaEmbeddings',
    'EmbeddingResult',
    # Processors
    'DocumentProcessor',
    'ChunkingStrategy',
    'FileParser',
    'TextCleaner',
    'ProcessedDocument',
    'Chunk',
    # Extractors
    'EntityExtractor',
    'ExtractedEntity',
    'ExtractedRelationship',
    'ExtractionResult',
    'entities_to_dicts',
    'relationships_to_dicts',
]

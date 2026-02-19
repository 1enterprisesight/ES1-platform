"""
Configuration for Knowledge Ingestion Pipeline
Environment variables and default settings
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class OllamaConfig:
    """Ollama API configuration"""
    base_url: str = "http://ollama:11434"
    embedding_model: str = "nomic-embed-text"
    timeout: int = 300


@dataclass
class ChunkingConfig:
    """Document chunking configuration"""
    chunk_size: int = 512
    chunk_overlap: int = 50
    strategy: str = "recursive"  # fixed, recursive, semantic


@dataclass
class ExtractionConfig:
    """Entity extraction configuration"""
    use_spacy: bool = True
    use_llm: bool = True
    spacy_model: str = "en_core_web_sm"
    llm_model: str = "llama3.2:3b"
    confidence_threshold: float = 0.7


@dataclass
class KnowledgeConfig:
    """Main configuration class for knowledge ingestion"""

    # Database connections
    aiml_db: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(
        host=os.getenv("AIML_DB_HOST", "aiml-postgres"),
        port=int(os.getenv("AIML_DB_PORT", "5432")),
        database=os.getenv("AIML_DB_NAME", "aiml"),
        user=os.getenv("AIML_DB_USER", "aiml_user"),
        password=os.getenv("AIML_DB_PASSWORD", "aiml_dev_password"),
    ))

    platform_db: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(
        host=os.getenv("PLATFORM_DB_HOST", "postgres"),
        port=int(os.getenv("PLATFORM_DB_PORT", "5432")),
        database=os.getenv("PLATFORM_DB_NAME", "engine_platform"),
        user=os.getenv("PLATFORM_DB_USER", "engine_user"),
        password=os.getenv("PLATFORM_DB_PASSWORD", "engine_dev_password"),
    ))

    # Ollama configuration
    ollama: OllamaConfig = field(default_factory=OllamaConfig)

    # Processing configuration
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)

    # Processing limits
    max_document_size_mb: int = 50
    max_chunks_per_document: int = 1000
    batch_size: int = 100

    @classmethod
    def from_env(cls) -> "KnowledgeConfig":
        """Create configuration from environment variables"""
        return cls()


# Singleton instance
_config: Optional[KnowledgeConfig] = None


def get_config() -> KnowledgeConfig:
    """Get or create the configuration singleton"""
    global _config
    if _config is None:
        _config = KnowledgeConfig.from_env()
    return _config

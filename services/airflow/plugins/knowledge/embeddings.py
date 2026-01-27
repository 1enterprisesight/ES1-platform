"""
Ollama Embeddings Client for Knowledge Ingestion Pipeline
Generates embeddings for document chunks using Ollama
"""

import requests
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from knowledge.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of an embedding operation"""
    content: str
    embedding: List[float]
    model: str
    dimension: int


class OllamaEmbeddings:
    """Client for generating embeddings using Ollama"""

    # Known model dimensions
    MODEL_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "snowflake-arctic-embed": 1024,
    }

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int = None,
    ):
        config = get_config()
        self.base_url = base_url or config.ollama.base_url
        self.model = model or config.ollama.embedding_model
        self.timeout = timeout or config.ollama.timeout
        self._dimension: Optional[int] = None

    @property
    def dimension(self) -> int:
        """Get the embedding dimension for the current model"""
        if self._dimension is None:
            # Try known dimensions first
            for model_prefix, dim in self.MODEL_DIMENSIONS.items():
                if model_prefix in self.model.lower():
                    self._dimension = dim
                    break

            # If unknown, generate a test embedding to find out
            if self._dimension is None:
                test_result = self.embed("test")
                self._dimension = len(test_result.embedding)

        return self._dimension

    def _ensure_model_available(self) -> bool:
        """Check if model is available, pull if not"""
        try:
            # Check if model exists
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=30
            )
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if our model is in the list
            if any(self.model in name for name in model_names):
                return True

            # Model not found, try to pull it
            logger.info(f"Pulling embedding model: {self.model}")
            pull_response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                timeout=600,  # 10 minutes for model download
                stream=True
            )

            # Stream the response to show progress
            for line in pull_response.iter_lines():
                if line:
                    logger.debug(f"Pull progress: {line.decode()}")

            return True

        except Exception as e:
            logger.error(f"Failed to ensure model availability: {e}")
            return False

    def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text"""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text,
                },
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding", [])

            return EmbeddingResult(
                content=text,
                embedding=embedding,
                model=self.model,
                dimension=len(embedding),
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 10,
        show_progress: bool = True,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.
        Note: Ollama doesn't have native batch embedding, so we process sequentially.
        """
        results = []
        total = len(texts)

        for i, text in enumerate(texts):
            if show_progress and (i + 1) % 10 == 0:
                logger.info(f"Embedding progress: {i + 1}/{total}")

            try:
                result = self.embed(text)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to embed text {i}: {e}")
                # Create a placeholder with empty embedding
                results.append(EmbeddingResult(
                    content=text,
                    embedding=[],
                    model=self.model,
                    dimension=0,
                ))

        return results

    def embed_chunks(
        self,
        chunks: List[Dict],
        content_key: str = "content",
    ) -> List[Dict]:
        """
        Generate embeddings for a list of chunk dictionaries.
        Adds 'embedding' key to each chunk.
        """
        texts = [chunk[content_key] for chunk in chunks]
        embeddings = self.embed_batch(texts)

        for chunk, emb_result in zip(chunks, embeddings):
            chunk['embedding'] = emb_result.embedding
            chunk['embedding_model'] = emb_result.model
            chunk['embedding_dimension'] = emb_result.dimension

        return chunks

    def health_check(self) -> bool:
        """Check if Ollama is healthy and model is available"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False


def ensure_embedding_model(model: str = None) -> bool:
    """
    Ensure the embedding model is available in Ollama.
    Call this at DAG start to avoid failures during processing.
    """
    client = OllamaEmbeddings(model=model)
    return client._ensure_model_available()

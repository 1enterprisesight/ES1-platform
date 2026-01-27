"""AI/ML database client for knowledge management."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import httpx

from app.core.config import settings
from app.core.logging import logger


# Create async engine for AI/ML database
aiml_engine = create_async_engine(
    settings.aiml_database_url,
    echo=False,
    future=True,
)

# Create async session factory
AIMLSessionLocal = async_sessionmaker(
    aiml_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_aiml_db() -> AsyncSession:
    """Dependency for getting async AI/ML database sessions."""
    async with AIMLSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class OllamaClient:
    """Client for generating embeddings via Ollama."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.OLLAMA_EMBEDDING_MODEL

    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding for text using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding")
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


class AirflowClient:
    """Client for triggering Airflow DAGs."""

    def __init__(self, base_url: str = None, username: str = None, password: str = None):
        self.base_url = base_url or settings.AIRFLOW_API_URL
        self.auth = (
            username or settings.AIRFLOW_USERNAME,
            password or settings.AIRFLOW_PASSWORD,
        )

    async def trigger_dag(
        self,
        dag_id: str,
        conf: dict = None,
        logical_date: str = None,
    ) -> Optional[dict]:
        """Trigger an Airflow DAG run."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"conf": conf or {}}
                if logical_date:
                    payload["logical_date"] = logical_date

                response = await client.post(
                    f"{self.base_url}/dags/{dag_id}/dagRuns",
                    json=payload,
                    auth=self.auth,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to trigger DAG {dag_id}: {e}")
            return None

    async def get_dag_runs(self, dag_id: str, limit: int = 10) -> list[dict]:
        """Get recent DAG runs."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/dags/{dag_id}/dagRuns",
                    params={"limit": limit, "order_by": "-execution_date"},
                    auth=self.auth,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("dag_runs", [])
        except Exception as e:
            logger.error(f"Failed to get DAG runs for {dag_id}: {e}")
            return []


# Singleton instances
ollama_client = OllamaClient()
airflow_client = AirflowClient()

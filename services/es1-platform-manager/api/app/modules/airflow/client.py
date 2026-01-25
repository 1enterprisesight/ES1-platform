"""Airflow API client for interacting with Apache Airflow."""
import httpx
from typing import Any
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AirflowClient:
    """
    Client for interacting with Apache Airflow REST API.

    Supports:
    - Listing DAGs
    - Getting DAG details
    - Triggering DAG runs
    - Getting DAG run status
    - Listing tasks and task instances
    """

    def __init__(self):
        """Initialize Airflow client."""
        self.base_url = settings.AIRFLOW_API_URL
        self.username = settings.AIRFLOW_USERNAME
        self.password = settings.AIRFLOW_PASSWORD
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=(self.username, self.password),
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> dict[str, Any]:
        """Check Airflow health status."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            if response.status_code == 200:
                return {"status": "healthy", "data": response.json()}
            return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_dags(
        self,
        limit: int = 100,
        offset: int = 0,
        only_active: bool = True,
    ) -> dict[str, Any]:
        """
        List all DAGs.

        Args:
            limit: Maximum number of DAGs to return
            offset: Number of DAGs to skip
            only_active: Only return active DAGs

        Returns:
            dict with 'dags' list and 'total_entries' count
        """
        try:
            client = await self._get_client()
            params = {
                "limit": limit,
                "offset": offset,
                "only_active": str(only_active).lower(),
            }
            response = await client.get("/dags", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list DAGs: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing DAGs: {e}")
            raise

    async def get_dag(self, dag_id: str) -> dict[str, Any]:
        """
        Get details of a specific DAG.

        Args:
            dag_id: The DAG identifier

        Returns:
            DAG details dict
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/dags/{dag_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get DAG {dag_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting DAG {dag_id}: {e}")
            raise

    async def trigger_dag(
        self,
        dag_id: str,
        conf: dict[str, Any] | None = None,
        logical_date: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """
        Trigger a DAG run.

        Args:
            dag_id: The DAG identifier
            conf: Configuration to pass to the DAG run
            logical_date: The logical date for the DAG run
            note: A note for the DAG run

        Returns:
            DAG run details
        """
        try:
            client = await self._get_client()
            payload: dict[str, Any] = {}
            if conf:
                payload["conf"] = conf
            if logical_date:
                payload["logical_date"] = logical_date
            if note:
                payload["note"] = note

            response = await client.post(f"/dags/{dag_id}/dagRuns", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to trigger DAG {dag_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error triggering DAG {dag_id}: {e}")
            raise

    async def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 25,
        offset: int = 0,
        state: str | None = None,
    ) -> dict[str, Any]:
        """
        List DAG runs for a specific DAG.

        Args:
            dag_id: The DAG identifier
            limit: Maximum number of runs to return
            offset: Number of runs to skip
            state: Filter by state (running, success, failed, etc.)

        Returns:
            dict with 'dag_runs' list and 'total_entries' count
        """
        try:
            client = await self._get_client()
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            if state:
                params["state"] = state

            response = await client.get(f"/dags/{dag_id}/dagRuns", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get DAG runs for {dag_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting DAG runs for {dag_id}: {e}")
            raise

    async def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict[str, Any]:
        """
        Get details of a specific DAG run.

        Args:
            dag_id: The DAG identifier
            dag_run_id: The DAG run identifier

        Returns:
            DAG run details
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/dags/{dag_id}/dagRuns/{dag_run_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get DAG run {dag_run_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting DAG run {dag_run_id}: {e}")
            raise

    async def get_task_instances(
        self,
        dag_id: str,
        dag_run_id: str,
    ) -> dict[str, Any]:
        """
        Get task instances for a DAG run.

        Args:
            dag_id: The DAG identifier
            dag_run_id: The DAG run identifier

        Returns:
            dict with 'task_instances' list
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task instances: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting task instances: {e}")
            raise

    async def pause_dag(self, dag_id: str, is_paused: bool = True) -> dict[str, Any]:
        """
        Pause or unpause a DAG.

        Args:
            dag_id: The DAG identifier
            is_paused: True to pause, False to unpause

        Returns:
            Updated DAG details
        """
        try:
            client = await self._get_client()
            response = await client.patch(
                f"/dags/{dag_id}",
                json={"is_paused": is_paused},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to pause/unpause DAG {dag_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error pausing/unpausing DAG {dag_id}: {e}")
            raise

    async def get_connections(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """
        List Airflow connections.

        Args:
            limit: Maximum number of connections to return
            offset: Number of connections to skip

        Returns:
            dict with 'connections' list and 'total_entries' count
        """
        try:
            client = await self._get_client()
            params = {"limit": limit, "offset": offset}
            response = await client.get("/connections", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list connections: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing connections: {e}")
            raise

    async def get_variables(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """
        List Airflow variables.

        Args:
            limit: Maximum number of variables to return
            offset: Number of variables to skip

        Returns:
            dict with 'variables' list and 'total_entries' count
        """
        try:
            client = await self._get_client()
            params = {"limit": limit, "offset": offset}
            response = await client.get("/variables", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list variables: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing variables: {e}")
            raise


# Singleton instance
airflow_client = AirflowClient()

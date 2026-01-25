"""Langflow API client for interacting with Langflow."""
import httpx
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LangflowClient:
    """
    Client for interacting with Langflow REST API.

    Supports:
    - Listing flows
    - Getting flow details
    - Running flows
    - Managing components
    """

    def __init__(self):
        """Initialize Langflow client."""
        self.base_url = settings.LANGFLOW_API_URL
        self.enabled = settings.LANGFLOW_ENABLED
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=60.0,  # Longer timeout for LLM operations
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> dict[str, Any]:
        """Check Langflow health status."""
        if not self.enabled:
            return {"status": "disabled", "message": "Langflow integration is disabled"}

        try:
            # Health endpoint is at root, not API path
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.LANGFLOW_URL}/health")
                if response.status_code == 200:
                    data = response.json()
                    # Langflow returns {"status": "ok"} when healthy
                    status = data.get("status", "unknown")
                    if status in ("ok", "healthy"):
                        return {"status": "healthy", "data": data}
                    return {"status": "unhealthy", "error": f"Status: {status}"}
                return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_flows(self) -> list[dict[str, Any]]:
        """
        List all flows.

        Returns:
            List of flow objects
        """
        if not self.enabled:
            return []

        try:
            client = await self._get_client()
            response = await client.get("/flows/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list flows: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing flows: {e}")
            raise

    async def get_flow(self, flow_id: str) -> dict[str, Any]:
        """
        Get details of a specific flow.

        Args:
            flow_id: The flow identifier

        Returns:
            Flow details dict
        """
        if not self.enabled:
            raise ValueError("Langflow integration is disabled")

        try:
            client = await self._get_client()
            response = await client.get(f"/flows/{flow_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get flow {flow_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting flow {flow_id}: {e}")
            raise

    async def run_flow(
        self,
        flow_id: str,
        input_value: str,
        input_type: str = "chat",
        output_type: str = "chat",
        tweaks: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Run a flow with input.

        Args:
            flow_id: The flow identifier
            input_value: The input value to process
            input_type: Type of input (chat, text, etc.)
            output_type: Type of output expected
            tweaks: Optional component tweaks
            session_id: Optional session ID for conversation context

        Returns:
            Flow execution result
        """
        if not self.enabled:
            raise ValueError("Langflow integration is disabled")

        try:
            client = await self._get_client()
            payload = {
                "input_value": input_value,
                "input_type": input_type,
                "output_type": output_type,
            }
            if tweaks:
                payload["tweaks"] = tweaks
            if session_id:
                payload["session_id"] = session_id

            response = await client.post(f"/run/{flow_id}", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to run flow {flow_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error running flow {flow_id}: {e}")
            raise

    async def create_flow(
        self,
        name: str,
        description: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new flow.

        Args:
            name: Flow name
            description: Optional description
            data: Optional flow data/graph

        Returns:
            Created flow details
        """
        if not self.enabled:
            raise ValueError("Langflow integration is disabled")

        try:
            client = await self._get_client()
            payload = {
                "name": name,
                "description": description or "",
                "data": data or {},
            }
            response = await client.post("/flows/", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create flow: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating flow: {e}")
            raise

    async def delete_flow(self, flow_id: str) -> bool:
        """
        Delete a flow.

        Args:
            flow_id: The flow identifier

        Returns:
            True if deleted successfully
        """
        if not self.enabled:
            raise ValueError("Langflow integration is disabled")

        try:
            client = await self._get_client()
            response = await client.delete(f"/flows/{flow_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete flow {flow_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deleting flow {flow_id}: {e}")
            raise

    async def get_components(self) -> dict[str, Any]:
        """
        Get available components/nodes.

        Returns:
            Dict of component categories and components
        """
        if not self.enabled:
            return {}

        try:
            client = await self._get_client()
            response = await client.get("/components/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get components: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting components: {e}")
            raise


# Singleton instance
langflow_client = LangflowClient()

"""Langflow API client for flow discovery and management."""
import httpx
from typing import Any, List, Optional

from app.core.config import settings


class LangflowClient:
    """
    Client for interacting with Langflow API.

    Langflow provides a visual LLM pipeline builder with:
    - Flow creation and editing
    - Component library
    - API endpoints for flow execution
    """

    def __init__(self, base_url: str | None = None):
        """
        Initialize Langflow client.

        Args:
            base_url: Langflow API base URL. Defaults to settings.LANGFLOW_API_URL
        """
        self.base_url = base_url or settings.LANGFLOW_API_URL

    async def health_check(self) -> bool:
        """
        Check if Langflow is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.LANGFLOW_URL}/health")
                return response.status_code == 200
        except Exception:
            return False

    async def list_flows(self) -> List[dict[str, Any]]:
        """
        Fetch all flows from Langflow.

        Returns:
            List of flow dictionaries
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/flows")
            response.raise_for_status()
            return response.json()

    async def get_flow(self, flow_id: str) -> dict[str, Any]:
        """
        Get a specific flow by ID.

        Args:
            flow_id: The flow UUID

        Returns:
            Flow details dictionary
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/flows/{flow_id}")
            response.raise_for_status()
            return response.json()

    async def run_flow(
        self,
        flow_id: str,
        input_value: str,
        input_type: str = "chat",
        output_type: str = "chat",
        tweaks: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Run a flow with input.

        Args:
            flow_id: The flow UUID
            input_value: Input text/value
            input_type: Type of input (default: "chat")
            output_type: Type of output (default: "chat")
            tweaks: Optional component tweaks

        Returns:
            Flow execution result
        """
        payload = {
            "input_value": input_value,
            "input_type": input_type,
            "output_type": output_type,
        }
        if tweaks:
            payload["tweaks"] = tweaks

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/run/{flow_id}",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def get_flow_components(self, flow_id: str) -> List[dict[str, Any]]:
        """
        Get components/nodes in a flow.

        Args:
            flow_id: The flow UUID

        Returns:
            List of component dictionaries
        """
        flow = await self.get_flow(flow_id)
        return flow.get("data", {}).get("nodes", [])

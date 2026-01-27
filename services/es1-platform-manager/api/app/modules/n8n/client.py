"""n8n API client for interacting with n8n workflow automation."""
import httpx
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class N8NAPIKeyMissingError(Exception):
    """Raised when n8n API key is not configured."""

    pass


class N8NClient:
    """
    Client for interacting with n8n REST API.

    Supports:
    - Listing workflows
    - Getting workflow details
    - Executing workflows
    - Managing credentials
    - Webhook management
    """

    def __init__(self):
        """Initialize n8n client."""
        self.base_url = settings.N8N_API_URL
        self.enabled = settings.N8N_ENABLED
        self.api_key = settings.N8N_API_KEY
        self._client: httpx.AsyncClient | None = None

    def _check_api_key(self):
        """Check if API key is configured."""
        if not self.api_key:
            raise N8NAPIKeyMissingError(
                "n8n API key not configured. Generate one in n8n Settings > API and set N8N_API_KEY"
            )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with API key authentication."""
        self._check_api_key()

        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-N8N-API-KEY": self.api_key,
                },
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def is_configured(self) -> bool:
        """Check if n8n is enabled and API key is configured."""
        return self.enabled and bool(self.api_key)

    async def health_check(self) -> dict[str, Any]:
        """Check n8n health status."""
        if not self.enabled:
            return {"status": "disabled", "message": "n8n integration is disabled"}

        try:
            # n8n health endpoint doesn't require auth
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.N8N_URL}/healthz")
                if response.status_code == 200:
                    # Check if API key is configured
                    if not self.api_key:
                        return {
                            "status": "setup_required",
                            "message": "n8n is running but API key not configured",
                            "setup_url": "http://localhost:5678",
                        }
                    return {"status": "healthy", "data": {"message": "n8n is running"}}
                return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except httpx.ConnectError:
            return {"status": "unhealthy", "error": "Connection refused - n8n not running"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_workflows(self, active: bool | None = None) -> dict[str, Any]:
        """
        List all workflows.

        Args:
            active: Filter by active status

        Returns:
            dict with 'data' list of workflows
        """
        if not self.enabled:
            return {"data": []}

        try:
            client = await self._get_client()
            params = {}
            if active is not None:
                params["active"] = str(active).lower()

            response = await client.get("/workflows", params=params)
            response.raise_for_status()
            return response.json()
        except N8NAPIKeyMissingError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list workflows: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            raise

    async def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        """
        Get details of a specific workflow.

        Args:
            workflow_id: The workflow identifier

        Returns:
            Workflow details dict
        """
        if not self.enabled:
            raise ValueError("n8n integration is disabled")

        try:
            client = await self._get_client()
            response = await client.get(f"/workflows/{workflow_id}")
            response.raise_for_status()
            return response.json()
        except N8NAPIKeyMissingError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting workflow {workflow_id}: {e}")
            raise

    async def execute_workflow(
        self,
        workflow_id: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a workflow.

        Args:
            workflow_id: The workflow identifier
            data: Input data for the workflow

        Returns:
            Execution result
        """
        if not self.enabled:
            raise ValueError("n8n integration is disabled")

        try:
            client = await self._get_client()
            payload = data or {}

            response = await client.post(
                f"/workflows/{workflow_id}/execute",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except N8NAPIKeyMissingError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {e}")
            raise

    async def activate_workflow(self, workflow_id: str, active: bool = True) -> dict[str, Any]:
        """
        Activate or deactivate a workflow.

        Args:
            workflow_id: The workflow identifier
            active: True to activate, False to deactivate

        Returns:
            Updated workflow details
        """
        if not self.enabled:
            raise ValueError("n8n integration is disabled")

        try:
            client = await self._get_client()
            endpoint = f"/workflows/{workflow_id}/activate" if active else f"/workflows/{workflow_id}/deactivate"

            response = await client.post(endpoint)
            response.raise_for_status()
            return response.json()
        except N8NAPIKeyMissingError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to {'activate' if active else 'deactivate'} workflow {workflow_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error {'activating' if active else 'deactivating'} workflow {workflow_id}: {e}")
            raise

    async def list_executions(
        self,
        workflow_id: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        List workflow executions.

        Args:
            workflow_id: Optional workflow ID to filter by
            limit: Maximum number of executions to return

        Returns:
            dict with 'data' list of executions
        """
        if not self.enabled:
            return {"data": []}

        try:
            client = await self._get_client()
            params: dict[str, Any] = {"limit": limit}
            if workflow_id:
                params["workflowId"] = workflow_id

            response = await client.get("/executions", params=params)
            response.raise_for_status()
            return response.json()
        except N8NAPIKeyMissingError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list executions: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing executions: {e}")
            raise

    async def get_execution(self, execution_id: str) -> dict[str, Any]:
        """
        Get details of a specific execution.

        Args:
            execution_id: The execution identifier

        Returns:
            Execution details dict
        """
        if not self.enabled:
            raise ValueError("n8n integration is disabled")

        try:
            client = await self._get_client()
            response = await client.get(f"/executions/{execution_id}")
            response.raise_for_status()
            return response.json()
        except N8NAPIKeyMissingError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get execution {execution_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting execution {execution_id}: {e}")
            raise

    async def list_credentials(self) -> dict[str, Any]:
        """
        List all credentials.

        Returns:
            dict with 'data' list of credentials
        """
        if not self.enabled:
            return {"data": []}

        try:
            client = await self._get_client()
            response = await client.get("/credentials")
            response.raise_for_status()
            return response.json()
        except N8NAPIKeyMissingError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list credentials: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing credentials: {e}")
            raise


# Singleton instance
n8n_client = N8NClient()

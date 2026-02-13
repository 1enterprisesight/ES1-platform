"""Langfuse API client for observability."""
import httpx
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LangfuseClient:
    """
    Client for interacting with Langfuse API.

    Supports:
    - Health checks
    - Trace listing and retrieval
    - Session management
    - Score/evaluation data
    """

    def __init__(self):
        """Initialize Langfuse client."""
        self.base_url = settings.LANGFUSE_API_URL
        self.enabled = settings.LANGFUSE_ENABLED
        self.public_key = settings.LANGFUSE_PUBLIC_KEY
        self.secret_key = settings.LANGFUSE_SECRET_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            auth = None
            if self.public_key and self.secret_key:
                auth = (self.public_key, self.secret_key)

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=auth,
                timeout=30.0,
                headers=headers,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> dict[str, Any]:
        """Check Langfuse health status."""
        if not self.enabled:
            return {"status": "disabled", "message": "Langfuse integration is disabled"}

        try:
            client = await self._get_client()
            response = await client.get("/public/health")
            if response.status_code == 200:
                # Check if API keys are configured
                if not self._is_authenticated():
                    return {
                        "status": "setup_required",
                        "message": "Langfuse is running but API keys not configured. Create API keys in Langfuse UI.",
                        "setup_url": f"{settings.LANGFUSE_URL}/project/default/settings/api-keys",
                    }
                return {"status": "healthy", "data": response.json()}
            return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def _is_authenticated(self) -> bool:
        """Check if API keys are configured."""
        return bool(self.public_key and self.secret_key)

    async def list_traces(
        self,
        page: int = 1,
        limit: int = 50,
        user_id: str | None = None,
        session_id: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """
        List traces.

        Args:
            page: Page number
            limit: Items per page
            user_id: Filter by user ID
            session_id: Filter by session ID
            name: Filter by trace name

        Returns:
            Dict with 'data' list and pagination info
        """
        if not self.enabled or not self._is_authenticated():
            return {"data": [], "meta": {"totalItems": 0, "page": page, "limit": limit}}

        try:
            client = await self._get_client()
            params: dict[str, Any] = {"page": page, "limit": limit}
            if user_id:
                params["userId"] = user_id
            if session_id:
                params["sessionId"] = session_id
            if name:
                params["name"] = name

            response = await client.get("/public/traces", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list traces: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing traces: {e}")
            raise

    async def get_trace(self, trace_id: str) -> dict[str, Any]:
        """
        Get details of a specific trace.

        Args:
            trace_id: The trace identifier

        Returns:
            Trace details dict
        """
        if not self.enabled or not self._is_authenticated():
            raise ValueError("Langfuse integration is disabled or not configured")

        try:
            client = await self._get_client()
            response = await client.get(f"/public/traces/{trace_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get trace {trace_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting trace {trace_id}: {e}")
            raise

    async def list_sessions(
        self,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        List sessions.

        Args:
            page: Page number
            limit: Items per page

        Returns:
            Dict with 'data' list and pagination info
        """
        if not self.enabled or not self._is_authenticated():
            return {"data": [], "meta": {"totalItems": 0, "page": page, "limit": limit}}

        try:
            client = await self._get_client()
            params = {"page": page, "limit": limit}
            response = await client.get("/public/sessions", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list sessions: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            raise

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """
        Get details of a specific session.

        Args:
            session_id: The session identifier

        Returns:
            Session details dict
        """
        if not self.enabled or not self._is_authenticated():
            raise ValueError("Langfuse integration is disabled or not configured")

        try:
            client = await self._get_client()
            response = await client.get(f"/public/sessions/{session_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise

    async def list_observations(
        self,
        page: int = 1,
        limit: int = 50,
        trace_id: str | None = None,
        type: str | None = None,
    ) -> dict[str, Any]:
        """
        List observations (spans, generations, events).

        Args:
            page: Page number
            limit: Items per page
            trace_id: Filter by trace ID
            type: Filter by type (SPAN, GENERATION, EVENT)

        Returns:
            Dict with 'data' list and pagination info
        """
        if not self.enabled or not self._is_authenticated():
            return {"data": [], "meta": {"totalItems": 0, "page": page, "limit": limit}}

        try:
            client = await self._get_client()
            params: dict[str, Any] = {"page": page, "limit": limit}
            if trace_id:
                params["traceId"] = trace_id
            if type:
                params["type"] = type

            response = await client.get("/public/observations", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list observations: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing observations: {e}")
            raise

    async def get_metrics(self) -> dict[str, Any]:
        """
        Get aggregated metrics.

        Returns:
            Dict with metrics data
        """
        if not self.enabled:
            return {}

        try:
            client = await self._get_client()
            # Get trace counts by day
            response = await client.get("/public/metrics/daily")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}


# Singleton instance
langfuse_client = LangfuseClient()

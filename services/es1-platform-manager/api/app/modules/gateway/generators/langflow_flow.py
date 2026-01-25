"""Langflow flow endpoint generator."""
from typing import Any
from .base import ConfigGenerator, EndpointConfig
from app.core.config import settings as app_settings


class LangflowFlowGenerator(ConfigGenerator):
    """Generate API endpoints for Langflow flows."""

    def supports(self, resource_type: str, resource_metadata: dict[str, Any]) -> bool:
        """Check if this generator supports the resource type."""
        return resource_type == "flow"

    def generate(
        self,
        resource_id: str,
        resource_type: str,
        resource_metadata: dict[str, Any],
        settings: dict[str, Any],
    ) -> EndpointConfig:
        """
        Generate endpoint configuration for Langflow flow execution.

        Creates an endpoint that proxies to Langflow's /run/{flow_id} endpoint.
        """
        flow_id = resource_metadata.get("flow_id", resource_id)
        endpoint_name = resource_metadata.get("endpoint_name") or resource_metadata.get("name") or flow_id

        # Sanitize endpoint name for URL
        endpoint_name = endpoint_name.replace(" ", "-").lower()

        # Get Langflow URL from settings or exposure settings override
        langflow_url = settings.get("langflow_url", app_settings.LANGFLOW_URL)

        config = EndpointConfig(
            endpoint=f"/gateway/v1/flows/{endpoint_name}",
            method="POST",
            backend=[
                {
                    "url_pattern": f"/api/v1/run/{flow_id}",
                    "host": [langflow_url],
                    "timeout": self._get_timeout(settings, default=120),  # LLM flows can be slow
                    "encoding": "json",
                }
            ],
            extra_config={
                "qos/ratelimit/router": {
                    "maxRate": self._get_rate_limit(settings, default=50),  # Lower default for LLM
                    "clientMaxRate": self._get_rate_limit(settings, default=10),
                },
            },
            input_headers=["Content-Type", "Authorization", "X-Session-ID"],
            input_query_strings=["*"],
        )

        # Add auth configuration if specified
        auth_config = self._get_auth_config(settings)
        if auth_config and config.extra_config:
            config.extra_config.update(auth_config)

        return config

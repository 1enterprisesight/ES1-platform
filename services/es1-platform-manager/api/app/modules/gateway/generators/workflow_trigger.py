"""Workflow trigger endpoint generator for Airflow DAGs."""
from typing import Any
from .base import ConfigGenerator, EndpointConfig
from app.core.config import settings as app_settings


class WorkflowTriggerGenerator(ConfigGenerator):
    """Generate trigger endpoints for workflow orchestration (Airflow DAGs)."""

    def supports(self, resource_type: str, resource_metadata: dict[str, Any]) -> bool:
        """Check if this generator supports the resource type."""
        return resource_type == "workflow"

    def generate(
        self,
        resource_id: str,
        resource_type: str,
        resource_metadata: dict[str, Any],
        settings: dict[str, Any],
    ) -> EndpointConfig:
        """Generate endpoint configuration for workflow trigger."""
        dag_id = resource_metadata.get("dag_id", resource_metadata.get("name", resource_id))

        # Get Airflow backend host from app settings or exposure settings override
        airflow_host = settings.get("airflow_host", app_settings.AIRFLOW_BACKEND_HOST)

        # Build the KrakenD endpoint configuration
        config = EndpointConfig(
            endpoint=f"/gateway/v1/workflows/trigger/{dag_id}",
            method="POST",
            backend=[
                {
                    "url_pattern": f"/api/v1/dags/{dag_id}/dagRuns",
                    "host": [airflow_host],
                    "timeout": self._get_timeout(settings),
                    "encoding": "json",
                }
            ],
            extra_config={
                "qos/ratelimit/router": {
                    "maxRate": self._get_rate_limit(settings),
                    "clientMaxRate": self._get_rate_limit(settings),
                }
            },
        )

        # Add auth configuration if specified
        auth_config = self._get_auth_config(settings)
        if auth_config and config.extra_config:
            config.extra_config.update(auth_config)

        return config

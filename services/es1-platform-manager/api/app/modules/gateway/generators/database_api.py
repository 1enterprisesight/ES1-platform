"""Database API wrapper endpoint generator."""
from typing import Any
from .base import ConfigGenerator, EndpointConfig
from app.core.config import settings as app_settings


class DatabaseAPIGenerator(ConfigGenerator):
    """Generate API wrapper endpoints for database connections."""

    def supports(self, resource_type: str, resource_metadata: dict[str, Any]) -> bool:
        """Check if this generator supports the resource type."""
        if resource_type != "connection":
            return False

        # Check if it's a database connection
        conn_type = resource_metadata.get("conn_type", "")
        return conn_type.lower() in ["postgres", "postgresql", "mysql", "mongodb", "redis"]

    def generate(
        self,
        resource_id: str,
        resource_type: str,
        resource_metadata: dict[str, Any],
        settings: dict[str, Any],
    ) -> EndpointConfig:
        """Generate endpoint configuration for database API wrapper."""
        conn_id = resource_metadata.get("conn_id", resource_id)
        db_type = resource_metadata.get("conn_type", "postgres").lower()

        # Normalize database type names
        db_type_map = {
            "postgresql": "postgres",
            "mysql": "mysql",
            "mongodb": "mongo",
            "redis": "redis",
        }
        normalized_db_type = db_type_map.get(db_type, db_type)

        # Build backend service URL using configurable pattern
        # Pattern: "http://db-api-{db_type}:8080" with {db_type} replaced
        backend_service = app_settings.DB_API_HOST_PATTERN.replace("{db_type}", normalized_db_type)

        config = EndpointConfig(
            endpoint=f"/gateway/v1/data/{conn_id}/{{operation}}",
            method="POST",
            backend=[
                {
                    "url_pattern": "/query",
                    "host": [backend_service],
                    "timeout": self._get_timeout(settings),
                    "encoding": "json",
                }
            ],
            extra_config={
                "qos/ratelimit/router": {
                    "maxRate": self._get_rate_limit(settings),
                },
            },
            input_headers=["Content-Type", "Authorization"],
            input_query_strings=["*"],
        )

        # Add auth configuration if specified
        auth_config = self._get_auth_config(settings)
        if auth_config and config.extra_config:
            config.extra_config.update(auth_config)

        return config

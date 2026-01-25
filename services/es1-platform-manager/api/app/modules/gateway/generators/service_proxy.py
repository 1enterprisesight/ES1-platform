"""Service proxy endpoint generator for HTTP services."""
from typing import Any
from .base import ConfigGenerator, EndpointConfig


class ServiceProxyGenerator(ConfigGenerator):
    """Generate proxy endpoints for HTTP services."""

    def supports(self, resource_type: str, resource_metadata: dict[str, Any]) -> bool:
        """Check if this generator supports the resource type."""
        if resource_type != "service":
            return False

        # Check if it's an HTTP service
        service_type = resource_metadata.get("type", "")
        return service_type.lower() in ["http", "https", "rest", "api"]

    def generate(
        self,
        resource_id: str,
        resource_type: str,
        resource_metadata: dict[str, Any],
        settings: dict[str, Any],
    ) -> EndpointConfig:
        """Generate endpoint configuration for service proxy."""
        service_name = resource_metadata.get("name", resource_id)
        host = resource_metadata.get("host", "")
        port = resource_metadata.get("port", 443)
        schema = resource_metadata.get("schema", "https")
        base_path = resource_metadata.get("base_path", "")

        # Build backend URL
        backend_host = f"{schema}://{host}:{port}"
        url_pattern = f"{base_path}/{{path}}" if base_path else "/{path}"

        config = EndpointConfig(
            endpoint=f"/gateway/v1/services/{service_name}/{{path}}",
            method=["GET", "POST", "PUT", "PATCH", "DELETE"],
            backend=[
                {
                    "url_pattern": url_pattern,
                    "host": [backend_host],
                    "timeout": self._get_timeout(settings),
                }
            ],
            extra_config={
                "qos/ratelimit/router": {
                    "maxRate": self._get_rate_limit(settings),
                },
                "qos/circuit-breaker": {
                    "interval": 60,
                    "timeout": 10,
                    "maxErrors": 5,
                },
            },
        )

        # Add auth configuration if specified
        auth_config = self._get_auth_config(settings)
        if auth_config and config.extra_config:
            config.extra_config.update(auth_config)

        return config

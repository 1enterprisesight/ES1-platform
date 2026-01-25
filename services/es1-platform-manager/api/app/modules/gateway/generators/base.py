"""Base configuration generator interface."""
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class EndpointConfig(BaseModel):
    """KrakenD endpoint configuration."""

    endpoint: str
    method: str | list[str]
    backend: list[dict[str, Any]]
    extra_config: dict[str, Any] | None = None
    input_headers: list[str] | None = None
    input_query_strings: list[str] | None = None


class ValidationResult(BaseModel):
    """Validation result for generated configuration."""

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class ConfigGenerator(ABC):
    """Abstract base class for configuration generators."""

    @abstractmethod
    def supports(self, resource_type: str, resource_metadata: dict[str, Any]) -> bool:
        """Check if this generator supports the resource type."""
        pass

    @abstractmethod
    def generate(
        self,
        resource_id: str,
        resource_type: str,
        resource_metadata: dict[str, Any],
        settings: dict[str, Any],
    ) -> EndpointConfig:
        """Generate endpoint configuration for the resource."""
        pass

    def validate(self, config: EndpointConfig) -> ValidationResult:
        """Validate generated configuration."""
        errors = []
        warnings = []

        # Basic validation
        if not config.endpoint:
            errors.append("Endpoint path is required")

        if not config.endpoint.startswith("/"):
            errors.append("Endpoint must start with /")

        if not config.method:
            errors.append("HTTP method is required")

        if not config.backend or len(config.backend) == 0:
            errors.append("At least one backend is required")

        for idx, backend in enumerate(config.backend):
            if "url_pattern" not in backend:
                errors.append(f"Backend {idx}: url_pattern is required")
            if "host" not in backend:
                errors.append(f"Backend {idx}: host is required")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _get_rate_limit(self, settings: dict[str, Any], default: int = 100) -> int:
        """Get rate limit from settings with default."""
        return settings.get("rate_limit", default)

    def _get_timeout(self, settings: dict[str, Any], default: int = 30) -> str:
        """Get timeout from settings with default."""
        timeout = settings.get("timeout", default)
        return f"{timeout}s" if isinstance(timeout, int) else timeout

    def _get_auth_config(self, settings: dict[str, Any]) -> dict[str, Any] | None:
        """Get auth configuration from settings."""
        auth_type = settings.get("auth_type")
        if not auth_type or auth_type == "none":
            return None

        if auth_type == "api_key":
            return {
                "auth/api-keys": {
                    "roles": settings.get("roles", ["user"])
                }
            }

        return None

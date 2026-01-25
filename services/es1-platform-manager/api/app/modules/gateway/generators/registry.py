"""Generator registry for managing configuration generators."""
from typing import Any
from .base import ConfigGenerator, EndpointConfig
from .workflow_trigger import WorkflowTriggerGenerator
from .service_proxy import ServiceProxyGenerator
from .database_api import DatabaseAPIGenerator
from .langflow_flow import LangflowFlowGenerator


class NoGeneratorFoundError(Exception):
    """Raised when no suitable generator is found for a resource."""
    pass


class GeneratorRegistry:
    """Registry for managing and selecting configuration generators."""

    def __init__(self):
        """Initialize registry with built-in generators."""
        self.generators: list[ConfigGenerator] = []
        self._register_builtin_generators()

    def _register_builtin_generators(self):
        """Register built-in generators."""
        self.register(WorkflowTriggerGenerator())
        self.register(ServiceProxyGenerator())
        self.register(DatabaseAPIGenerator())
        self.register(LangflowFlowGenerator())

    def register(self, generator: ConfigGenerator):
        """Register a new generator."""
        self.generators.append(generator)

    def get_generator(
        self, resource_type: str, resource_metadata: dict[str, Any]
    ) -> ConfigGenerator | None:
        """Get the first generator that supports the resource."""
        for generator in self.generators:
            if generator.supports(resource_type, resource_metadata):
                return generator
        return None

    def generate_config(
        self,
        resource_id: str,
        resource_type: str,
        resource_metadata: dict[str, Any],
        settings: dict[str, Any],
    ) -> EndpointConfig:
        """Generate configuration for a resource using the appropriate generator."""
        generator = self.get_generator(resource_type, resource_metadata)

        if not generator:
            raise NoGeneratorFoundError(
                f"No generator found for resource type: {resource_type} with metadata: {resource_metadata}"
            )

        return generator.generate(resource_id, resource_type, resource_metadata, settings)

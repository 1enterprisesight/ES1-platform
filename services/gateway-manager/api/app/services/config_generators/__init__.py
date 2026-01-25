"""KrakenD configuration generators."""
from .base import ConfigGenerator, EndpointConfig, ValidationResult
from .workflow_trigger import WorkflowTriggerGenerator
from .service_proxy import ServiceProxyGenerator
from .database_api import DatabaseAPIGenerator
from .registry import GeneratorRegistry

__all__ = [
    "ConfigGenerator",
    "EndpointConfig",
    "ValidationResult",
    "WorkflowTriggerGenerator",
    "ServiceProxyGenerator",
    "DatabaseAPIGenerator",
    "GeneratorRegistry",
]

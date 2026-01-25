"""Runtime environment detection for dual-mode operation."""
import os
from enum import Enum


class RuntimeMode(Enum):
    """Runtime environment modes."""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


def detect_runtime() -> RuntimeMode:
    """
    Detect whether running in Kubernetes or Docker Compose.

    Detection logic:
    1. Check RUNTIME_MODE env var for explicit override
    2. Check for KUBERNETES_SERVICE_HOST (set automatically in K8s pods)
    3. Default to Docker mode

    Returns:
        RuntimeMode: The detected runtime environment
    """
    # Allow explicit override via environment variable
    explicit_mode = os.environ.get("RUNTIME_MODE", "").lower()
    if explicit_mode == "kubernetes":
        return RuntimeMode.KUBERNETES
    elif explicit_mode == "docker":
        return RuntimeMode.DOCKER

    # Auto-detect based on Kubernetes service account injection
    # Kubernetes automatically sets KUBERNETES_SERVICE_HOST in pods
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return RuntimeMode.KUBERNETES

    # Default to Docker mode (local development)
    return RuntimeMode.DOCKER


def is_kubernetes() -> bool:
    """Check if running in Kubernetes mode."""
    return RUNTIME_MODE == RuntimeMode.KUBERNETES


def is_docker() -> bool:
    """Check if running in Docker mode."""
    return RUNTIME_MODE == RuntimeMode.DOCKER


# Detect mode at module load time
RUNTIME_MODE = detect_runtime()

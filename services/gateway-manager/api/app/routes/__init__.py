"""API routes."""
from .resources import router as resources_router
from .exposures import router as exposures_router
from .exposure_changes import router as exposure_changes_router
from .deployments import router as deployments_router
from .integrations import router as integrations_router
from .metrics import router as metrics_router
from .events import router as events_router
from .gateway import router as gateway_router
from .config_versions import router as config_versions_router
from .branding import router as branding_router

__all__ = [
    "resources_router",
    "exposures_router",
    "exposure_changes_router",
    "deployments_router",
    "integrations_router",
    "metrics_router",
    "events_router",
    "gateway_router",
    "config_versions_router",
    "branding_router",
]

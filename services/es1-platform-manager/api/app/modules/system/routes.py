"""System and scheduler routes."""
import os
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.core.scheduler import discovery_scheduler


router = APIRouter(prefix="/system", tags=["System"])


class SchedulerStatusResponse(BaseModel):
    """Scheduler status response."""
    running: bool
    discovery_enabled: bool
    interval_seconds: int
    last_discovery: dict[str, str | None]


class DiscoveryRequest(BaseModel):
    """Manual discovery request."""
    services: list[str] | None = None


class DiscoveryResponse(BaseModel):
    """Discovery result response."""
    results: dict[str, Any]
    message: str


class SystemStatusResponse(BaseModel):
    """System status response."""
    name: str
    version: str
    runtime_mode: str
    scheduler: SchedulerStatusResponse
    integrations: dict[str, bool]


class VersionResponse(BaseModel):
    """Version information response."""
    platform_version: str
    api_version: str
    runtime_mode: str
    auth_mode: str
    services: dict[str, bool]


@router.get("/version", response_model=VersionResponse)
async def get_version():
    """Get platform version and service configuration."""
    return VersionResponse(
        platform_version=settings.PLATFORM_VERSION,
        api_version=settings.API_V1_PREFIX,
        runtime_mode=settings.RUNTIME_MODE,
        auth_mode=settings.AUTH_MODE,
        services={
            "airflow": settings.AIRFLOW_ENABLED,
            "langflow": settings.LANGFLOW_ENABLED,
            "langfuse": settings.LANGFUSE_ENABLED,
            "n8n": settings.N8N_ENABLED,
            "mlflow": settings.MLFLOW_ENABLED,
        },
    )


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get overall system status."""
    last_discovery = {}
    for key, value in discovery_scheduler.last_discovery.items():
        last_discovery[key] = value.isoformat() if value else None

    return SystemStatusResponse(
        name=settings.PROJECT_NAME,
        version=settings.PLATFORM_VERSION,
        runtime_mode=settings.RUNTIME_MODE,
        scheduler=SchedulerStatusResponse(
            running=discovery_scheduler.is_running,
            discovery_enabled=settings.DISCOVERY_ENABLED,
            interval_seconds=settings.DISCOVERY_INTERVAL_SECONDS,
            last_discovery=last_discovery,
        ),
        integrations={
            "airflow": settings.AIRFLOW_ENABLED,
            "langflow": settings.LANGFLOW_ENABLED,
            "langfuse": settings.LANGFUSE_ENABLED,
            "n8n": settings.N8N_ENABLED,
        },
    )


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """Get scheduler status."""
    last_discovery = {}
    for key, value in discovery_scheduler.last_discovery.items():
        last_discovery[key] = value.isoformat() if value else None

    return SchedulerStatusResponse(
        running=discovery_scheduler.is_running,
        discovery_enabled=settings.DISCOVERY_ENABLED,
        interval_seconds=settings.DISCOVERY_INTERVAL_SECONDS,
        last_discovery=last_discovery,
    )


@router.post("/scheduler/start")
async def start_scheduler():
    """Start the discovery scheduler."""
    if discovery_scheduler.is_running:
        return {"message": "Scheduler already running"}

    await discovery_scheduler.start()
    return {"message": "Scheduler started"}


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the discovery scheduler."""
    if not discovery_scheduler.is_running:
        return {"message": "Scheduler not running"}

    await discovery_scheduler.stop()
    return {"message": "Scheduler stopped"}


@router.post("/discovery/run", response_model=DiscoveryResponse)
async def run_discovery(request: DiscoveryRequest | None = None):
    """
    Run discovery manually.

    Optionally specify which services to discover.
    If not specified, discovers all enabled services.
    """
    services = request.services if request else None
    results = await discovery_scheduler.run_discovery_now(services)

    return DiscoveryResponse(
        results=results,
        message="Discovery completed",
    )


@router.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    return {
        "runtime_mode": settings.RUNTIME_MODE,
        "api_prefix": settings.API_V1_PREFIX,
        "discovery": {
            "enabled": settings.DISCOVERY_ENABLED,
            "interval_seconds": settings.DISCOVERY_INTERVAL_SECONDS,
        },
        "krakend": {
            "url": settings.KRAKEND_URL,
            "config_path": settings.KRAKEND_CONFIG_PATH,
        },
        "airflow": {
            "enabled": settings.AIRFLOW_ENABLED,
            "url": settings.AIRFLOW_API_URL,
        },
        "langflow": {
            "enabled": settings.LANGFLOW_ENABLED,
            "url": settings.LANGFLOW_API_URL,
        },
        "langfuse": {
            "enabled": settings.LANGFUSE_ENABLED,
            "url": settings.LANGFUSE_API_URL,
        },
        "n8n": {
            "enabled": settings.N8N_ENABLED,
            "url": settings.N8N_API_URL,
        },
    }

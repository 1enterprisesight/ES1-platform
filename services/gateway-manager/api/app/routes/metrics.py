"""Metrics API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Exposure, Deployment, DiscoveredResource
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


class DashboardMetrics(BaseModel):
    """Dashboard metrics response."""

    total_endpoints: int
    active_endpoints: int
    pending_approvals: int
    failed_deployments: int
    total_resources: int
    active_resources: int


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated metrics for the dashboard."""

    # Count total exposures (endpoints)
    total_exposures_query = select(func.count()).select_from(Exposure)
    total_exposures_result = await db.execute(total_exposures_query)
    total_endpoints = total_exposures_result.scalar() or 0

    # Count active/deployed endpoints
    active_exposures_query = select(func.count()).select_from(Exposure).where(
        Exposure.status == "deployed"
    )
    active_exposures_result = await db.execute(active_exposures_query)
    active_endpoints = active_exposures_result.scalar() or 0

    # Count pending approvals
    pending_query = select(func.count()).select_from(Exposure).where(
        Exposure.status == "pending"
    )
    pending_result = await db.execute(pending_query)
    pending_approvals = pending_result.scalar() or 0

    # Count failed deployments
    failed_deployments_query = select(func.count()).select_from(Deployment).where(
        Deployment.status == "failed"
    )
    failed_deployments_result = await db.execute(failed_deployments_query)
    failed_deployments = failed_deployments_result.scalar() or 0

    # Count total resources
    total_resources_query = select(func.count()).select_from(DiscoveredResource)
    total_resources_result = await db.execute(total_resources_query)
    total_resources = total_resources_result.scalar() or 0

    # Count active resources
    active_resources_query = select(func.count()).select_from(DiscoveredResource).where(
        DiscoveredResource.status == "active"
    )
    active_resources_result = await db.execute(active_resources_query)
    active_resources = active_resources_result.scalar() or 0

    return DashboardMetrics(
        total_endpoints=total_endpoints,
        active_endpoints=active_endpoints,
        pending_approvals=pending_approvals,
        failed_deployments=failed_deployments,
        total_resources=total_resources,
        active_resources=active_resources,
    )


class GatewayHealthResponse(BaseModel):
    """Gateway health response schema."""

    status: str
    uptime_available: bool | None = None
    goroutines: int | None = None
    memory_bytes: int | None = None
    total_requests: int | None = None
    metrics_count: int | None = None
    error: str | None = None


class RequestMetricsResponse(BaseModel):
    """Request metrics response schema."""

    total_requests: int | None = None
    by_status_code: dict[str, int] | None = None
    success_rate: float | None = None
    error: str | None = None


class EndpointMetric(BaseModel):
    """Individual endpoint metric."""

    endpoint: str
    total_requests: int
    success_requests: int
    error_requests: int
    error_rate: float


class TopEndpointsResponse(BaseModel):
    """Top endpoints response schema."""

    endpoints: list[EndpointMetric]
    total_endpoints: int
    error: str | None = None


@router.get("/gateway/health", response_model=GatewayHealthResponse)
async def get_gateway_health():
    """
    Get basic KrakenD gateway health metrics.

    Returns current snapshot of gateway health including:
    - Status (healthy/unhealthy)
    - Goroutines count
    - Memory usage
    - Total requests since restart

    Note: These are real-time metrics from KrakenD, not historical data.
    """
    metrics_service = MetricsService()
    health_data = metrics_service.get_gateway_health()
    return GatewayHealthResponse(**health_data)


@router.get("/gateway/requests", response_model=RequestMetricsResponse)
async def get_request_metrics():
    """
    Get KrakenD request metrics.

    Returns:
    - Total request count
    - Requests by status code
    - Success rate percentage

    Note: These are cumulative since gateway restart, not rates over time.
    """
    metrics_service = MetricsService()
    request_data = metrics_service.get_request_metrics()
    return RequestMetricsResponse(**request_data)


@router.get("/endpoints/top", response_model=TopEndpointsResponse)
async def get_top_endpoints(limit: int = 10):
    """
    Get top endpoints by request count.

    Returns endpoint metrics including:
    - Total requests per endpoint
    - Success vs error counts
    - Error rate percentage

    Args:
        limit: Number of top endpoints to return (default 10)
    """
    metrics_service = MetricsService()
    endpoints_data = metrics_service.get_top_endpoints(limit)
    return TopEndpointsResponse(**endpoints_data)

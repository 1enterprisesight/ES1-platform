"""Gateway health and management API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Deployment
from app.services.deployment_engine import DeploymentEngine

router = APIRouter(prefix="/gateway", tags=["gateway"])


class GatewayHealthResponse(BaseModel):
    """Gateway health response."""

    status: str  # healthy, degraded, unhealthy
    pod_count: int
    running_pods: int
    last_deploy: str | None
    failed_health_checks: int


@router.get("/health", response_model=GatewayHealthResponse)
async def get_gateway_health(
    db: AsyncSession = Depends(get_db),
):
    """Get KrakenD gateway health status from Kubernetes."""

    # Get health details from deployment engine
    engine = DeploymentEngine()
    health_details = await engine.get_health_details()

    # Get last successful deployment from database
    last_deploy_query = (
        select(Deployment)
        .where(Deployment.status == "succeeded")
        .order_by(Deployment.deployed_at.desc())
        .limit(1)
    )
    result = await db.execute(last_deploy_query)
    last_deployment = result.scalar_one_or_none()

    last_deploy = (
        last_deployment.deployed_at.isoformat() + 'Z' if last_deployment else None
    )

    return GatewayHealthResponse(
        status=health_details["status"],
        pod_count=health_details["pod_count"],
        running_pods=health_details["running_pods"],
        last_deploy=last_deploy,
        failed_health_checks=health_details["failed_health_checks"],
    )

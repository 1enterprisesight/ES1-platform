"""Deployments API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Deployment
from app.services.deployment_engine import DeploymentEngine

router = APIRouter(prefix="/deployments", tags=["deployments"])


class DeploymentTriggerRequest(BaseModel):
    """Request to trigger a new deployment."""

    deployed_by: str = "admin"  # TODO: Get from auth
    commit_message: str | None = None


class DeploymentTriggerResponse(BaseModel):
    """Response from triggering a deployment."""

    success: bool
    message: str
    deployment_id: str | None = None


class DeploymentResponse(BaseModel):
    """Deployment response schema."""

    id: UUID
    version_id: UUID
    status: str
    deployed_by: str
    deployed_at: str
    completed_at: str | None = None
    health_check_passed: bool | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True


@router.post("/trigger", response_model=DeploymentTriggerResponse)
async def trigger_deployment(
    request: DeploymentTriggerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new deployment to KrakenD gateway."""
    engine = DeploymentEngine()

    success, message, deployment_id = await engine.deploy(
        db=db, deployed_by=request.deployed_by, commit_message=request.commit_message
    )

    return DeploymentTriggerResponse(
        success=success, message=message, deployment_id=deployment_id
    )


@router.post("/deploy-changes", response_model=DeploymentTriggerResponse)
async def deploy_approved_changes(
    request: DeploymentTriggerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Deploy all approved exposure changes (change management workflow)."""
    engine = DeploymentEngine()

    success, message, deployment_id = await engine.deploy_changes(
        db=db, deployed_by=request.deployed_by, commit_message=request.commit_message
    )

    return DeploymentTriggerResponse(
        success=success, message=message, deployment_id=deployment_id
    )


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get deployment status by ID."""
    query = select(Deployment).where(Deployment.id == deployment_id)
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return DeploymentResponse(
        id=deployment.id,
        version_id=deployment.version_id,
        status=deployment.status,
        deployed_by=deployment.deployed_by,
        deployed_at=deployment.deployed_at.isoformat() + 'Z',
        completed_at=deployment.completed_at.isoformat() + 'Z' if deployment.completed_at else None,
        health_check_passed=deployment.health_check_passed,
        error_message=deployment.error_message,
    )


@router.get("", response_model=list[DeploymentResponse])
async def list_deployments(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List recent deployments."""
    query = (
        select(Deployment).order_by(Deployment.deployed_at.desc()).limit(limit)
    )
    result = await db.execute(query)
    deployments = result.scalars().all()

    return [
        DeploymentResponse(
            id=d.id,
            version_id=d.version_id,
            status=d.status,
            deployed_by=d.deployed_by,
            deployed_at=d.deployed_at.isoformat() + 'Z',
            completed_at=d.completed_at.isoformat() + 'Z' if d.completed_at else None,
            health_check_passed=d.health_check_passed,
            error_message=d.error_message,
        )
        for d in deployments
    ]


@router.post("/redeploy/{version_id}", response_model=DeploymentTriggerResponse)
async def redeploy_config_version(
    version_id: UUID,
    request: DeploymentTriggerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Redeploy an existing configuration version."""
    from app.models import ConfigVersion
    from datetime import datetime

    # Get the config version
    config_version = await db.get(ConfigVersion, version_id)
    if not config_version:
        raise HTTPException(status_code=404, detail="Configuration version not found")

    deployment_id = None

    try:
        engine = DeploymentEngine()

        # Create deployment record
        deployment = Deployment(
            version_id=config_version.id,
            status="in_progress",
            deployed_by=request.deployed_by,
        )
        db.add(deployment)
        await db.commit()
        await db.refresh(deployment)
        deployment_id = str(deployment.id)

        # Deploy the existing config snapshot
        if not await engine.update_configmap(config_version.config_snapshot):
            deployment.status = "failed"
            deployment.error_message = "Failed to update ConfigMap"
            await db.commit()
            return DeploymentTriggerResponse(
                success=False, message="Failed to update ConfigMap", deployment_id=deployment_id
            )

        # Trigger rolling restart
        if not await engine.rolling_restart():
            deployment.status = "failed"
            deployment.error_message = "Failed to restart deployment"
            await db.commit()
            return DeploymentTriggerResponse(
                success=False, message="Failed to restart KrakenD deployment", deployment_id=deployment_id
            )

        # Wait for rollout
        if not await engine.wait_for_rollout():
            deployment.status = "failed"
            deployment.error_message = "Deployment rollout timeout"
            await db.commit()
            return DeploymentTriggerResponse(
                success=False, message="Deployment rollout timeout", deployment_id=deployment_id
            )

        # Health check
        if not await engine.health_check():
            deployment.status = "failed"
            deployment.error_message = "Health check failed"
            deployment.health_check_passed = False
            await db.commit()
            return DeploymentTriggerResponse(
                success=False, message="Health check failed", deployment_id=deployment_id
            )

        # Mark deployment as successful
        deployment.status = "succeeded"
        deployment.health_check_passed = True
        deployment.completed_at = datetime.utcnow()

        # Mark old config versions as inactive
        old_versions_query = select(ConfigVersion).where(ConfigVersion.is_active == True)
        old_versions_result = await db.execute(old_versions_query)
        for old_version in old_versions_result.scalars().all():
            old_version.is_active = False

        # Mark this config version as active
        config_version.is_active = True
        config_version.deployed_to_gateway_at = datetime.utcnow()

        await db.commit()

        return DeploymentTriggerResponse(
            success=True,
            message=f"Successfully redeployed configuration version {config_version.version}",
            deployment_id=deployment_id,
        )

    except Exception as e:
        # Mark deployment as failed if we have a deployment record
        if deployment_id:
            deployment_query = select(Deployment).where(Deployment.id == deployment_id)
            result = await db.execute(deployment_query)
            deployment = result.scalar_one_or_none()
            if deployment:
                deployment.status = "failed"
                deployment.error_message = str(e)
                await db.commit()

        return DeploymentTriggerResponse(
            success=False, message=f"Redeployment failed: {str(e)}", deployment_id=deployment_id
        )

"""API routes for the gateway module."""
from uuid import UUID
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.events import event_bus, EventType
from app.modules.gateway.models import (
    DiscoveredResource,
    Exposure,
    ExposureChange,
    ConfigVersion,
    Deployment,
    EventLog,
)
from app.modules.gateway.schemas import (
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    ResourceListResponse,
    ExposureCreate,
    ExposureUpdate,
    ExposureResponse,
    ExposureWithResourceResponse,
    ExposureListResponse,
    ExposureChangeCreate,
    ExposureChangeResponse,
    ExposureChangeListResponse,
    ConfigVersionResponse,
    ConfigVersionListResponse,
    DeploymentCreate,
    DeploymentResponse,
    DeploymentListResponse,
    GatewayHealthResponse,
    ApproveRequest,
    RejectRequest,
    RollbackRequest,
    ResourceInfo,
    CurrentConfigResponse,
    ConfigFileInfo,
    ConfigDiffRequest,
    ConfigDiffResponse,
)
from app.core.config import settings
from app.core.runtime import RUNTIME_MODE
from app.modules.gateway.services import DeploymentEngine
from app.modules.gateway.generators import GeneratorRegistry

router = APIRouter(tags=["Gateway"])


# =============================================================================
# Resource Routes
# =============================================================================

@router.get("/resources", response_model=ResourceListResponse)
async def list_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = None,
    source: str | None = None,
    status: str = "active",
    db: AsyncSession = Depends(get_db),
):
    """List discovered resources with pagination and filtering."""
    query = select(DiscoveredResource).where(DiscoveredResource.status == status)

    if type:
        query = query.where(DiscoveredResource.type == type)
    if source:
        query = query.where(DiscoveredResource.source == source)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(DiscoveredResource.discovered_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return ResourceListResponse(
        items=[ResourceResponse.model_validate(r) for r in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific resource by ID."""
    resource = await db.get(DiscoveredResource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return ResourceResponse.model_validate(resource)


@router.post("/resources", response_model=ResourceResponse, status_code=201)
async def create_resource(
    data: ResourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new discovered resource."""
    resource = DiscoveredResource(
        type=data.type,
        source=data.source,
        source_id=data.source_id,
        resource_metadata=data.metadata,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    # Emit event
    await event_bus.publish(
        EventType.RESOURCE_DISCOVERED,
        {
            "resource_id": str(resource.id),
            "type": resource.type,
            "source": resource.source,
        },
    )

    return ResourceResponse.model_validate(resource)


@router.patch("/resources/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: UUID,
    data: ResourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a resource."""
    resource = await db.get(DiscoveredResource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if data.metadata is not None:
        resource.resource_metadata = data.metadata
    if data.status is not None:
        resource.status = data.status

    await db.commit()
    await db.refresh(resource)

    await event_bus.publish(
        EventType.RESOURCE_UPDATED,
        {"resource_id": str(resource.id), "type": resource.type},
    )

    return ResourceResponse.model_validate(resource)


@router.delete("/resources/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a resource."""
    resource = await db.get(DiscoveredResource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    resource.status = "deleted"
    await db.commit()

    await event_bus.publish(
        EventType.RESOURCE_DELETED,
        {"resource_id": str(resource_id)},
    )


# =============================================================================
# Exposure Routes
# =============================================================================

@router.get("/exposures", response_model=ExposureListResponse)
async def list_exposures(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List exposures with pagination."""
    query = select(Exposure)

    if status:
        query = query.where(Exposure.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Exposure.created_at.desc())
    result = await db.execute(query)
    exposures = result.scalars().all()

    # Load resource info for each exposure
    items = []
    for exposure in exposures:
        resource = await db.get(DiscoveredResource, exposure.resource_id)
        resource_info = None
        if resource:
            resource_info = ResourceInfo(
                id=resource.id,
                type=resource.type,
                source=resource.source,
                source_id=resource.source_id,
                metadata=resource.resource_metadata,
            )
        item = ExposureWithResourceResponse.model_validate(exposure)
        item.resource = resource_info
        items.append(item)

    return ExposureListResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/exposures/{exposure_id}", response_model=ExposureWithResourceResponse)
async def get_exposure(
    exposure_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific exposure by ID."""
    exposure = await db.get(Exposure, exposure_id)
    if not exposure:
        raise HTTPException(status_code=404, detail="Exposure not found")

    resource = await db.get(DiscoveredResource, exposure.resource_id)
    resource_info = None
    if resource:
        resource_info = ResourceInfo(
            id=resource.id,
            type=resource.type,
            source=resource.source,
            source_id=resource.source_id,
            metadata=resource.resource_metadata,
        )

    result = ExposureWithResourceResponse.model_validate(exposure)
    result.resource = resource_info
    return result


@router.post("/exposures", response_model=ExposureResponse, status_code=201)
async def create_exposure(
    data: ExposureCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new exposure for a resource."""
    # Verify resource exists
    resource = await db.get(DiscoveredResource, data.resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Generate endpoint configuration
    registry = GeneratorRegistry()
    try:
        endpoint_config = registry.generate_config(
            resource_id=str(resource.id),
            resource_type=resource.type,
            resource_metadata=resource.resource_metadata,
            settings=data.settings,
        )
        generated_config = endpoint_config.model_dump(exclude_none=True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to generate configuration: {str(e)}",
        )

    exposure = Exposure(
        resource_id=data.resource_id,
        settings=data.settings,
        generated_config=generated_config,
        created_by=data.created_by,
    )
    db.add(exposure)
    await db.commit()
    await db.refresh(exposure)

    await event_bus.publish(
        EventType.EXPOSURE_CREATED,
        {
            "exposure_id": str(exposure.id),
            "resource_id": str(exposure.resource_id),
            "created_by": exposure.created_by,
        },
    )

    return ExposureResponse.model_validate(exposure)


@router.post("/exposures/{exposure_id}/approve", response_model=ExposureResponse)
async def approve_exposure(
    exposure_id: UUID,
    data: ApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve an exposure for deployment."""
    exposure = await db.get(Exposure, exposure_id)
    if not exposure:
        raise HTTPException(status_code=404, detail="Exposure not found")

    if exposure.status not in ["pending", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve exposure with status: {exposure.status}",
        )

    exposure.status = "approved"
    exposure.approved_by = data.approved_by
    exposure.approved_at = datetime.utcnow()
    exposure.rejection_reason = None

    await db.commit()
    await db.refresh(exposure)

    await event_bus.publish(
        EventType.EXPOSURE_APPROVED,
        {
            "exposure_id": str(exposure.id),
            "approved_by": data.approved_by,
        },
    )

    return ExposureResponse.model_validate(exposure)


@router.post("/exposures/{exposure_id}/reject", response_model=ExposureResponse)
async def reject_exposure(
    exposure_id: UUID,
    data: RejectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject an exposure."""
    exposure = await db.get(Exposure, exposure_id)
    if not exposure:
        raise HTTPException(status_code=404, detail="Exposure not found")

    if exposure.status not in ["pending", "approved"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject exposure with status: {exposure.status}",
        )

    exposure.status = "rejected"
    exposure.rejection_reason = data.reason

    await db.commit()
    await db.refresh(exposure)

    await event_bus.publish(
        EventType.EXPOSURE_REJECTED,
        {
            "exposure_id": str(exposure.id),
            "rejected_by": data.rejected_by,
            "reason": data.reason,
        },
    )

    return ExposureResponse.model_validate(exposure)


# =============================================================================
# Deployment Routes
# =============================================================================

@router.get("/deployments", response_model=DeploymentListResponse)
async def list_deployments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List deployments with pagination."""
    query = select(Deployment)

    if status:
        query = query.where(Deployment.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Deployment.deployed_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return DeploymentListResponse(
        items=[DeploymentResponse.model_validate(d) for d in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific deployment by ID."""
    deployment = await db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return DeploymentResponse.model_validate(deployment)


@router.post("/deployments", response_model=DeploymentResponse, status_code=201)
async def create_deployment(
    data: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Deploy all approved exposures to the gateway.

    This creates a new configuration version and deploys it to KrakenD.
    """
    engine = DeploymentEngine()
    success, message, deployment_id = await engine.deploy(
        db=db,
        deployed_by=data.deployed_by,
        commit_message=data.commit_message,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    deployment = await db.get(Deployment, deployment_id)
    return DeploymentResponse.model_validate(deployment)


@router.post("/deployments/rollback", response_model=DeploymentResponse)
async def rollback_deployment(
    data: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rollback to a previous configuration version."""
    # Find the config version
    query = select(ConfigVersion).where(ConfigVersion.version == data.version)
    result = await db.execute(query)
    config_version = result.scalar_one_or_none()

    if not config_version:
        raise HTTPException(
            status_code=404,
            detail=f"Configuration version {data.version} not found",
        )

    engine = DeploymentEngine()

    # Create deployment record
    deployment = Deployment(
        version_id=config_version.id,
        status="in_progress",
        deployed_by=data.deployed_by,
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)

    # Perform rollback
    try:
        if hasattr(engine._backend, 'rollback_to_version'):
            success = await engine._backend.rollback_to_version(data.version)
        else:
            success = False

        if success:
            deployment.status = "succeeded"
            deployment.health_check_passed = True
            deployment.completed_at = datetime.utcnow()

            # Mark all versions as inactive except this one
            old_query = select(ConfigVersion).where(ConfigVersion.is_active == True)
            old_result = await db.execute(old_query)
            for old in old_result.scalars().all():
                old.is_active = False

            config_version.is_active = True
            config_version.deployed_to_gateway_at = datetime.utcnow()
        else:
            deployment.status = "failed"
            deployment.error_message = "Rollback failed"

        await db.commit()
        await db.refresh(deployment)

        if not success:
            raise HTTPException(status_code=500, detail="Rollback failed")

        await event_bus.publish(
            EventType.DEPLOYMENT_ROLLED_BACK,
            {
                "deployment_id": str(deployment.id),
                "version": data.version,
                "deployed_by": data.deployed_by,
            },
        )

        return DeploymentResponse.model_validate(deployment)

    except Exception as e:
        deployment.status = "failed"
        deployment.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Config Version Routes
# =============================================================================

@router.get("/config-versions", response_model=ConfigVersionListResponse)
async def list_config_versions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List configuration versions with pagination."""
    query = select(ConfigVersion)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(ConfigVersion.version.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return ConfigVersionListResponse(
        items=[ConfigVersionResponse.model_validate(v) for v in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/config-versions/{version}", response_model=ConfigVersionResponse)
async def get_config_version(
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific configuration version."""
    query = select(ConfigVersion).where(ConfigVersion.version == version)
    result = await db.execute(query)
    config_version = result.scalar_one_or_none()

    if not config_version:
        raise HTTPException(status_code=404, detail="Config version not found")

    return ConfigVersionResponse.model_validate(config_version)


@router.get("/config-versions/active/current", response_model=ConfigVersionResponse)
async def get_active_config_version(
    db: AsyncSession = Depends(get_db),
):
    """Get the currently active configuration version."""
    query = select(ConfigVersion).where(ConfigVersion.is_active == True)
    result = await db.execute(query)
    config_version = result.scalar_one_or_none()

    if not config_version:
        raise HTTPException(status_code=404, detail="No active config version")

    return ConfigVersionResponse.model_validate(config_version)


# =============================================================================
# Gateway Health Routes
# =============================================================================

@router.get("/gateway/health", response_model=GatewayHealthResponse)
async def get_gateway_health():
    """Get the health status of the KrakenD gateway."""
    engine = DeploymentEngine()
    health = await engine.get_health_details()
    return GatewayHealthResponse(**health)


@router.get("/gateway/status")
async def get_gateway_status(db: AsyncSession = Depends(get_db)):
    """Get comprehensive gateway status including config and health."""
    engine = DeploymentEngine()
    health = await engine.get_health_details()

    # Get active config version
    query = select(ConfigVersion).where(ConfigVersion.is_active == True)
    result = await db.execute(query)
    active_version = result.scalar_one_or_none()

    # Get pending approvals count
    pending_query = select(func.count()).select_from(
        select(Exposure).where(Exposure.status == "pending").subquery()
    )
    pending_count = await db.scalar(pending_query)

    # Get approved count (ready to deploy)
    approved_query = select(func.count()).select_from(
        select(Exposure).where(Exposure.status == "approved").subquery()
    )
    approved_count = await db.scalar(approved_query)

    return {
        "health": health,
        "active_version": active_version.version if active_version else None,
        "pending_approvals": pending_count or 0,
        "ready_to_deploy": approved_count or 0,
    }


# =============================================================================
# Current Config Routes
# =============================================================================

@router.get("/gateway/config/current", response_model=CurrentConfigResponse)
async def get_current_gateway_config():
    """
    Get the currently deployed KrakenD configuration.

    This returns the actual configuration file that is currently
    being used by the KrakenD gateway.
    """
    engine = DeploymentEngine()
    config = await engine.get_current_config()

    endpoint_count = 0
    if config and "endpoints" in config:
        endpoint_count = len(config.get("endpoints", []))

    return CurrentConfigResponse(
        config=config,
        config_path=settings.KRAKEND_CONFIG_PATH,
        mode=RUNTIME_MODE.value,
        has_config=config is not None,
        endpoint_count=endpoint_count,
    )


@router.get("/gateway/config/files", response_model=list[ConfigFileInfo])
async def list_config_files():
    """
    List available configuration version files.

    In Docker mode, this returns the backup files stored on disk.
    In Kubernetes mode, this returns ConfigMap revisions.
    """
    engine = DeploymentEngine()
    files = await engine.list_config_files()
    return [ConfigFileInfo(**f) for f in files]


@router.post("/gateway/config/diff", response_model=ConfigDiffResponse)
async def diff_config_versions(
    data: ConfigDiffRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two configuration versions and return the differences.

    Useful for reviewing what changed between deployments.
    """
    # Get version A
    query_a = select(ConfigVersion).where(ConfigVersion.version == data.version_a)
    result_a = await db.execute(query_a)
    version_a = result_a.scalar_one_or_none()

    if not version_a:
        raise HTTPException(status_code=404, detail=f"Version {data.version_a} not found")

    # Get version B
    query_b = select(ConfigVersion).where(ConfigVersion.version == data.version_b)
    result_b = await db.execute(query_b)
    version_b = result_b.scalar_one_or_none()

    if not version_b:
        raise HTTPException(status_code=404, detail=f"Version {data.version_b} not found")

    # Compare endpoints
    endpoints_a = {e.get("endpoint", ""): e for e in version_a.config_snapshot.get("endpoints", [])}
    endpoints_b = {e.get("endpoint", ""): e for e in version_b.config_snapshot.get("endpoints", [])}

    added = list(set(endpoints_b.keys()) - set(endpoints_a.keys()))
    removed = list(set(endpoints_a.keys()) - set(endpoints_b.keys()))

    # Find modified endpoints
    modified = []
    common = set(endpoints_a.keys()) & set(endpoints_b.keys())
    for endpoint in common:
        if endpoints_a[endpoint] != endpoints_b[endpoint]:
            modified.append(endpoint)

    # Build detailed diff
    diff = []
    for endpoint in added:
        diff.append({"type": "added", "endpoint": endpoint, "config": endpoints_b[endpoint]})
    for endpoint in removed:
        diff.append({"type": "removed", "endpoint": endpoint, "config": endpoints_a[endpoint]})
    for endpoint in modified:
        diff.append({
            "type": "modified",
            "endpoint": endpoint,
            "before": endpoints_a[endpoint],
            "after": endpoints_b[endpoint],
        })

    return ConfigDiffResponse(
        version_a=data.version_a,
        version_b=data.version_b,
        diff=diff,
        added_endpoints=added,
        removed_endpoints=removed,
        modified_endpoints=modified,
    )

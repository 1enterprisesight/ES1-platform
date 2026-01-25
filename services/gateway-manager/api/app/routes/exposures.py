"""Exposures API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from uuid import UUID
from app.core.database import get_db
from app.models import Exposure, DiscoveredResource
from app.schemas import (
    ExposureCreate,
    ExposureUpdate,
    ExposureResponse,
    ExposureWithResourceResponse,
    ExposureListResponse,
    ResourceInfo,
)

router = APIRouter(prefix="/exposures", tags=["exposures"])


@router.get("", response_model=ExposureListResponse)
async def list_exposures(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all exposures with pagination and filtering."""
    # Build query with join to discovered_resources
    query = (
        select(Exposure, DiscoveredResource)
        .join(DiscoveredResource, Exposure.resource_id == DiscoveredResource.id)
    )

    # Apply filters
    if status:
        query = query.where(Exposure.status == status)

    # Get total count
    count_query = select(func.count()).select_from(Exposure)
    if status:
        count_query = count_query.where(Exposure.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Exposure.created_at.desc())

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Format responses with resource info
    items = []
    for exposure, resource in rows:
        resource_info = ResourceInfo(
            id=resource.id,
            type=resource.type,
            source=resource.source,
            source_id=resource.source_id,
            name=resource.resource_metadata.get("name", resource.source_id),
            metadata=resource.resource_metadata,
        )

        items.append(
            ExposureWithResourceResponse(
                id=exposure.id,
                resource_id=exposure.resource_id,
                settings=exposure.settings,
                generated_config=exposure.generated_config,
                status=exposure.status,
                created_by=exposure.created_by,
                created_at=exposure.created_at,
                approved_by=exposure.approved_by,
                approved_at=exposure.approved_at,
                rejection_reason=exposure.rejection_reason,
                resource=resource_info,
            )
        )

    return ExposureListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{exposure_id}", response_model=ExposureWithResourceResponse)
async def get_exposure(
    exposure_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific exposure by ID."""
    query = (
        select(Exposure, DiscoveredResource)
        .join(DiscoveredResource, Exposure.resource_id == DiscoveredResource.id)
        .where(Exposure.id == exposure_id)
    )
    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Exposure not found")

    exposure, resource = row

    resource_info = ResourceInfo(
        id=resource.id,
        type=resource.type,
        source=resource.source,
        source_id=resource.source_id,
        name=resource.resource_metadata.get("name", resource.source_id),
        metadata=resource.resource_metadata,
    )

    return ExposureWithResourceResponse(
        id=exposure.id,
        resource_id=exposure.resource_id,
        settings=exposure.settings,
        generated_config=exposure.generated_config,
        status=exposure.status,
        created_by=exposure.created_by,
        created_at=exposure.created_at,
        approved_by=exposure.approved_by,
        approved_at=exposure.approved_at,
        rejection_reason=exposure.rejection_reason,
        resource=resource_info,
    )


@router.post("", response_model=ExposureResponse, status_code=201)
async def create_exposure(
    exposure: ExposureCreate,
    created_by: str = "system",  # TODO: Get from auth
    db: AsyncSession = Depends(get_db),
):
    """Create a new exposure."""
    # Generate config (simplified for now, will be enhanced later)
    generated_config = {
        "endpoint": f"/api/{exposure.resource_id}",
        "method": "GET",
        "backend": "internal",
    }

    db_exposure = Exposure(
        resource_id=exposure.resource_id,
        settings=exposure.settings,
        generated_config=generated_config,
        created_by=created_by,
    )

    db.add(db_exposure)
    await db.commit()
    await db.refresh(db_exposure)
    return db_exposure


@router.patch("/{exposure_id}", response_model=ExposureResponse)
async def update_exposure(
    exposure_id: UUID,
    exposure_update: ExposureUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an exposure."""
    query = select(Exposure).where(Exposure.id == exposure_id)
    result = await db.execute(query)
    db_exposure = result.scalar_one_or_none()

    if not db_exposure:
        raise HTTPException(status_code=404, detail="Exposure not found")

    # Update fields
    update_data = exposure_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_exposure, field, value)

    await db.commit()
    await db.refresh(db_exposure)
    return db_exposure


@router.post("/{exposure_id}/approve", response_model=ExposureWithResourceResponse)
async def approve_exposure(
    exposure_id: UUID,
    approver: str = "admin",  # TODO: Get from auth
    db: AsyncSession = Depends(get_db),
):
    """Approve an exposure."""
    query = select(Exposure).where(Exposure.id == exposure_id)
    result = await db.execute(query)
    db_exposure = result.scalar_one_or_none()

    if not db_exposure:
        raise HTTPException(status_code=404, detail="Exposure not found")

    if db_exposure.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve exposure with status: {db_exposure.status}",
        )

    db_exposure.status = "approved"
    db_exposure.approved_by = approver
    from datetime import datetime

    db_exposure.approved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(db_exposure)

    # Fetch resource info for response
    resource_query = select(DiscoveredResource).where(
        DiscoveredResource.id == db_exposure.resource_id
    )
    resource_result = await db.execute(resource_query)
    resource = resource_result.scalar_one_or_none()

    if resource:
        resource_info = ResourceInfo(
            id=resource.id,
            type=resource.type,
            source=resource.source,
            source_id=resource.source_id,
            name=resource.resource_metadata.get("name", resource.source_id),
            metadata=resource.resource_metadata,
        )
    else:
        resource_info = None

    return ExposureWithResourceResponse(
        id=db_exposure.id,
        resource_id=db_exposure.resource_id,
        settings=db_exposure.settings,
        generated_config=db_exposure.generated_config,
        status=db_exposure.status,
        created_by=db_exposure.created_by,
        created_at=db_exposure.created_at,
        approved_by=db_exposure.approved_by,
        approved_at=db_exposure.approved_at,
        rejection_reason=db_exposure.rejection_reason,
        resource=resource_info,
    )


@router.post("/{exposure_id}/reject", response_model=ExposureWithResourceResponse)
async def reject_exposure(
    exposure_id: UUID,
    reason: str,
    approver: str = "admin",  # TODO: Get from auth
    db: AsyncSession = Depends(get_db),
):
    """Reject an exposure."""
    query = select(Exposure).where(Exposure.id == exposure_id)
    result = await db.execute(query)
    db_exposure = result.scalar_one_or_none()

    if not db_exposure:
        raise HTTPException(status_code=404, detail="Exposure not found")

    if db_exposure.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject exposure with status: {db_exposure.status}",
        )

    db_exposure.status = "rejected"
    db_exposure.rejection_reason = reason

    await db.commit()
    await db.refresh(db_exposure)

    # Fetch resource info for response
    resource_query = select(DiscoveredResource).where(
        DiscoveredResource.id == db_exposure.resource_id
    )
    resource_result = await db.execute(resource_query)
    resource = resource_result.scalar_one_or_none()

    if resource:
        resource_info = ResourceInfo(
            id=resource.id,
            type=resource.type,
            source=resource.source,
            source_id=resource.source_id,
            name=resource.resource_metadata.get("name", resource.source_id),
            metadata=resource.resource_metadata,
        )
    else:
        resource_info = None

    return ExposureWithResourceResponse(
        id=db_exposure.id,
        resource_id=db_exposure.resource_id,
        settings=db_exposure.settings,
        generated_config=db_exposure.generated_config,
        status=db_exposure.status,
        created_by=db_exposure.created_by,
        created_at=db_exposure.created_at,
        approved_by=db_exposure.approved_by,
        approved_at=db_exposure.approved_at,
        rejection_reason=db_exposure.rejection_reason,
        resource=resource_info,
    )

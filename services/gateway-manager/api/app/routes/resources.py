"""Resources API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from app.core.database import get_db
from app.models import DiscoveredResource
from app.schemas import (
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    ResourceListResponse,
)

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    type: str | None = Query(None),
    source: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all resources with pagination and filtering."""
    # Build query
    query = select(DiscoveredResource)

    # Apply filters
    if type:
        query = query.where(DiscoveredResource.type == type)
    if source:
        query = query.where(DiscoveredResource.source == source)
    if status:
        query = query.where(DiscoveredResource.status == status)

    # Get total count
    count_query = select(func.count()).select_from(DiscoveredResource)
    if type:
        count_query = count_query.where(DiscoveredResource.type == type)
    if source:
        count_query = count_query.where(DiscoveredResource.source == source)
    if status:
        count_query = count_query.where(DiscoveredResource.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(DiscoveredResource.discovered_at.desc())

    # Execute query
    result = await db.execute(query)
    resources = result.scalars().all()

    return ResourceListResponse(
        items=resources,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific resource by ID."""
    query = select(DiscoveredResource).where(DiscoveredResource.id == resource_id)
    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    return resource


@router.post("", response_model=ResourceResponse, status_code=201)
async def create_resource(
    resource: ResourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new resource."""
    db_resource = DiscoveredResource(**resource.model_dump())
    db.add(db_resource)
    await db.commit()
    await db.refresh(db_resource)
    return db_resource


@router.patch("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: UUID,
    resource_update: ResourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a resource."""
    query = select(DiscoveredResource).where(DiscoveredResource.id == resource_id)
    result = await db.execute(query)
    db_resource = result.scalar_one_or_none()

    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Update fields
    update_data = resource_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_resource, field, value)

    await db.commit()
    await db.refresh(db_resource)
    return db_resource


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a resource (soft delete by setting status to 'deleted')."""
    query = select(DiscoveredResource).where(DiscoveredResource.id == resource_id)
    result = await db.execute(query)
    db_resource = result.scalar_one_or_none()

    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    db_resource.status = "deleted"
    await db.commit()

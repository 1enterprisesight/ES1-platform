"""Exposure changes API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel
from app.core.database import get_db
from app.models import ExposureChange, EventLog, DiscoveredResource
from app.schemas import (
    ExposureChangeCreate,
    ExposureChangeUpdate,
    ExposureChangeResponse,
    ExposureChangeListResponse,
)

router = APIRouter(prefix="/exposure-changes", tags=["exposure-changes"])


@router.get("", response_model=ExposureChangeListResponse)
async def list_exposure_changes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: str | None = Query(None),
    batch_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all exposure changes with pagination and filtering."""
    # Build query
    query = select(ExposureChange)

    # Apply filters
    if status:
        query = query.where(ExposureChange.status == status)
    if batch_id:
        query = query.where(ExposureChange.batch_id == batch_id)

    # Get total count
    count_query = select(func.count()).select_from(ExposureChange)
    if status:
        count_query = count_query.where(ExposureChange.status == status)
    if batch_id:
        count_query = count_query.where(ExposureChange.batch_id == batch_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(ExposureChange.requested_at.desc())

    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()

    return ExposureChangeListResponse(
        items=[ExposureChangeResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{change_id}", response_model=ExposureChangeResponse)
async def get_exposure_change(
    change_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific exposure change by ID."""
    query = select(ExposureChange).where(ExposureChange.id == change_id)
    result = await db.execute(query)
    db_change = result.scalar_one_or_none()

    if not db_change:
        raise HTTPException(status_code=404, detail="Exposure change not found")

    return ExposureChangeResponse.model_validate(db_change)


@router.post("", response_model=ExposureChangeResponse, status_code=201)
async def create_exposure_change(
    change: ExposureChangeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new exposure change (draft)."""
    # Check if a draft change already exists for this resource
    existing_query = select(ExposureChange).where(
        ExposureChange.resource_id == change.resource_id,
        ExposureChange.status == "draft"
    )
    existing_result = await db.execute(existing_query)
    existing_change = existing_result.scalar_one_or_none()

    if existing_change:
        raise HTTPException(
            status_code=409,
            detail=f"A draft change already exists for this resource (ID: {existing_change.id}). Please edit or delete the existing draft instead of creating a new one."
        )

    db_change = ExposureChange(
        resource_id=change.resource_id,
        change_type=change.change_type,
        exposure_id=change.exposure_id,
        settings_before=change.settings_before,
        settings_after=change.settings_after,
        status="draft",  # Always start as draft
        requested_by=change.requested_by,
    )

    db.add(db_change)
    await db.commit()
    await db.refresh(db_change)

    # Get resource details for event logging
    resource_query = select(DiscoveredResource).where(DiscoveredResource.id == change.resource_id)
    resource_result = await db.execute(resource_query)
    resource = resource_result.scalar_one_or_none()

    if resource:
        # Log resource pushed event
        event = EventLog(
            event_type="resource_pushed",
            entity_type="exposure_change",
            entity_id=db_change.id,
            user_id=change.requested_by,
            event_metadata={
                "resource_id": str(change.resource_id),
                "resource_type": resource.type,
                "resource_name": resource.source_id,
                "change_type": change.change_type
            }
        )
        db.add(event)
        await db.commit()

    return ExposureChangeResponse.model_validate(db_change)


@router.patch("/{change_id}", response_model=ExposureChangeResponse)
async def update_exposure_change(
    change_id: UUID,
    change_update: ExposureChangeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an exposure change (only drafts can be edited)."""
    query = select(ExposureChange).where(ExposureChange.id == change_id)
    result = await db.execute(query)
    db_change = result.scalar_one_or_none()

    if not db_change:
        raise HTTPException(status_code=404, detail="Exposure change not found")

    # Only allow editing drafts
    if db_change.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit exposure change with status: {db_change.status}. Only drafts can be edited.",
        )

    # Update fields
    update_data = change_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_change, field, value)

    await db.commit()
    await db.refresh(db_change)
    return ExposureChangeResponse.model_validate(db_change)


@router.delete("/{change_id}", status_code=204)
async def delete_exposure_change(
    change_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete an exposure change (only drafts can be deleted)."""
    query = select(ExposureChange).where(ExposureChange.id == change_id)
    result = await db.execute(query)
    db_change = result.scalar_one_or_none()

    if not db_change:
        raise HTTPException(status_code=404, detail="Exposure change not found")

    # Only allow deleting drafts
    if db_change.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete exposure change with status: {db_change.status}. Only drafts can be deleted.",
        )

    await db.delete(db_change)
    await db.commit()
    return None


class SubmitBatchRequest(BaseModel):
    """Request body for submitting a batch of changes."""

    change_ids: list[UUID]


class SubmitBatchResponse(BaseModel):
    """Response for batch submission."""

    batch_id: UUID
    changes_count: int
    submitted_at: datetime


@router.post("/submit-batch", response_model=SubmitBatchResponse)
async def submit_batch_for_approval(
    request: SubmitBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a batch of draft changes for approval."""
    if not request.change_ids:
        raise HTTPException(status_code=400, detail="No change IDs provided")

    # Fetch all changes
    query = select(ExposureChange).where(ExposureChange.id.in_(request.change_ids))
    result = await db.execute(query)
    changes = result.scalars().all()

    if not changes:
        raise HTTPException(status_code=404, detail="No changes found with provided IDs")

    if len(changes) != len(request.change_ids):
        raise HTTPException(
            status_code=404,
            detail=f"Found {len(changes)} changes but {len(request.change_ids)} IDs provided",
        )

    # Verify all changes are drafts
    non_draft_changes = [c for c in changes if c.status != "draft"]
    if non_draft_changes:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit non-draft changes. Found {len(non_draft_changes)} changes with status != 'draft'",
        )

    # Generate batch ID and timestamp
    batch_id = uuid4()
    submitted_at = datetime.utcnow()

    # Update all changes
    for change in changes:
        change.status = "pending_approval"
        change.batch_id = batch_id
        change.submitted_for_approval_at = submitted_at

    # Log batch submission event
    event = EventLog(
        event_type="batch_submitted",
        entity_type="batch",
        entity_id=batch_id,
        user_id=changes[0].requested_by if changes else "unknown",
        event_metadata={
            "changes_count": len(changes),
            "change_ids": [str(c.id) for c in changes],
        },
    )
    db.add(event)

    await db.commit()

    return SubmitBatchResponse(
        batch_id=batch_id,
        changes_count=len(changes),
        submitted_at=submitted_at,
    )


class ApproveBatchRequest(BaseModel):
    """Request body for approving a batch of changes."""

    approved_by: str


class ApproveBatchResponse(BaseModel):
    """Response for batch approval."""

    batch_id: UUID
    changes_approved: int
    approved_at: datetime


@router.post("/batch/{batch_id}/approve", response_model=ApproveBatchResponse)
async def approve_batch(
    batch_id: UUID,
    request: ApproveBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve a batch of pending changes."""
    # Fetch all changes in the batch
    query = select(ExposureChange).where(ExposureChange.batch_id == batch_id)
    result = await db.execute(query)
    changes = result.scalars().all()

    if not changes:
        raise HTTPException(
            status_code=404,
            detail=f"No changes found with batch_id: {batch_id}"
        )

    # Verify all changes are pending approval
    non_pending = [c for c in changes if c.status != "pending_approval"]
    if non_pending:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve batch with non-pending changes. Found {len(non_pending)} changes with status != 'pending_approval'",
        )

    # Approve all changes
    approved_at = datetime.utcnow()
    for change in changes:
        change.status = "approved"
        change.approved_by = request.approved_by
        change.approved_at = approved_at

    # Log approval event
    event = EventLog(
        event_type="batch_approved",
        entity_type="batch",
        entity_id=batch_id,
        user_id=request.approved_by,
        event_metadata={
            "changes_count": len(changes),
            "change_ids": [str(c.id) for c in changes],
        },
    )
    db.add(event)

    await db.commit()

    return ApproveBatchResponse(
        batch_id=batch_id,
        changes_approved=len(changes),
        approved_at=approved_at,
    )


class RejectBatchRequest(BaseModel):
    """Request body for rejecting a batch of changes."""

    rejected_by: str
    reason: str


class RejectBatchResponse(BaseModel):
    """Response for batch rejection."""

    batch_id: UUID
    changes_rejected: int
    rejected_at: datetime
    reason: str


@router.post("/batch/{batch_id}/reject", response_model=RejectBatchResponse)
async def reject_batch(
    batch_id: UUID,
    request: RejectBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject a batch of pending changes."""
    if not request.reason or not request.reason.strip():
        raise HTTPException(
            status_code=400,
            detail="Rejection reason is required"
        )

    # Fetch all changes in the batch
    query = select(ExposureChange).where(ExposureChange.batch_id == batch_id)
    result = await db.execute(query)
    changes = result.scalars().all()

    if not changes:
        raise HTTPException(
            status_code=404,
            detail=f"No changes found with batch_id: {batch_id}"
        )

    # Verify all changes are pending approval
    non_pending = [c for c in changes if c.status != "pending_approval"]
    if non_pending:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject batch with non-pending changes. Found {len(non_pending)} changes with status != 'pending_approval'",
        )

    # Reject all changes
    rejected_at = datetime.utcnow()
    for change in changes:
        change.status = "rejected"
        change.rejected_by = request.rejected_by
        change.rejected_at = rejected_at
        change.rejection_reason = request.reason

    # Log rejection event
    event = EventLog(
        event_type="batch_rejected",
        entity_type="batch",
        entity_id=batch_id,
        user_id=request.rejected_by,
        event_metadata={
            "changes_count": len(changes),
            "change_ids": [str(c.id) for c in changes],
            "reason": request.reason,
        },
    )
    db.add(event)

    await db.commit()

    return RejectBatchResponse(
        batch_id=batch_id,
        changes_rejected=len(changes),
        rejected_at=rejected_at,
        reason=request.reason,
    )


class PreviewBatchResponse(BaseModel):
    """Response for batch config preview."""

    batch_id: UUID
    config_snapshot: dict
    summary: dict


@router.post("/batch/{batch_id}/preview", response_model=PreviewBatchResponse)
async def preview_batch_config(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate complete KrakenD config preview for a pending batch.

    This shows exactly what will be deployed if the batch is approved and deployed.
    Does not actually deploy anything.
    """
    from app.models import Exposure, DiscoveredResource
    from app.services.deployment_engine import DeploymentEngine

    # Fetch all changes in the batch
    query = select(ExposureChange).where(ExposureChange.batch_id == batch_id)
    result = await db.execute(query)
    changes = result.scalars().all()

    if not changes:
        raise HTTPException(
            status_code=404,
            detail=f"No changes found with batch_id: {batch_id}"
        )

    # Get current deployed exposures
    current_query = (
        select(Exposure)
        .where(Exposure.status == "deployed")
        .where(Exposure.removed_in_version_id == None)
    )
    current_result = await db.execute(current_query)
    exposures_preview = list(current_result.scalars().all())

    # Count changes by type
    adds = 0
    removes = 0
    modifies = 0

    # Apply changes to preview list (same logic as deploy_changes but without persisting)
    engine = DeploymentEngine()

    for change in changes:
        if change.change_type == "add":
            adds += 1
            # Get the resource to generate config
            resource_query = select(DiscoveredResource).where(
                DiscoveredResource.id == change.resource_id
            )
            resource_result = await db.execute(resource_query)
            resource = resource_result.scalar_one_or_none()

            if resource:
                # Generate endpoint config
                endpoint_config = engine.generator_registry.generate_config(
                    resource_id=str(resource.id),
                    resource_type=resource.type,
                    resource_metadata=resource.resource_metadata,
                    settings=change.settings_after,
                )

                # Create temporary exposure for preview (not saved to DB)
                temp_exposure = Exposure(
                    resource_id=change.resource_id,
                    settings=change.settings_after,
                    generated_config=endpoint_config.model_dump(exclude_none=True),
                    status="approved",
                    created_by=change.requested_by,
                )
                exposures_preview.append(temp_exposure)

        elif change.change_type == "remove":
            removes += 1
            # Remove from preview list
            exposures_preview = [
                e for e in exposures_preview if e.id != change.exposure_id
            ]

        elif change.change_type == "modify":
            modifies += 1
            # Update settings in preview
            for exp in exposures_preview:
                if exp.id == change.exposure_id:
                    resource_query = select(DiscoveredResource).where(
                        DiscoveredResource.id == exp.resource_id
                    )
                    resource_result = await db.execute(resource_query)
                    resource = resource_result.scalar_one_or_none()

                    if resource:
                        # Regenerate endpoint config with new settings
                        endpoint_config = engine.generator_registry.generate_config(
                            resource_id=str(resource.id),
                            resource_type=resource.type,
                            resource_metadata=resource.resource_metadata,
                            settings=change.settings_after,
                        )
                        exp.settings = change.settings_after
                        exp.generated_config = endpoint_config.model_dump(exclude_none=True)
                    break

    # Generate complete configuration preview
    config_snapshot = await engine.generate_complete_config(exposures_preview, db)

    return PreviewBatchResponse(
        batch_id=batch_id,
        config_snapshot=config_snapshot,
        summary={
            "total_endpoints": len(exposures_preview),
            "changes": {
                "added": adds,
                "removed": removes,
                "modified": modifies,
            },
        },
    )


@router.get("/{change_id}/generate-config")
async def generate_config_for_change(
    change_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate full KrakenD endpoint config for an exposure change.

    This endpoint generates the complete KrakenD configuration that would be
    created if this change were approved and deployed. Useful for draft config building.
    """
    # Get the exposure change
    change_query = select(ExposureChange).where(ExposureChange.id == change_id)
    change_result = await db.execute(change_query)
    change = change_result.scalar_one_or_none()

    if not change:
        raise HTTPException(status_code=404, detail="Exposure change not found")

    # Get the resource
    resource_query = select(DiscoveredResource).where(
        DiscoveredResource.id == change.resource_id
    )
    resource_result = await db.execute(resource_query)
    resource = resource_result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Initialize deployment engine (for access to generator registry)
    from app.services.deployment_engine import DeploymentEngine
    engine = DeploymentEngine()

    # Generate the endpoint config
    try:
        endpoint_config = engine.generator_registry.generate_config(
            resource_id=str(resource.id),
            resource_type=resource.type,
            resource_metadata=resource.resource_metadata,
            settings=change.settings_after or {},
        )

        return endpoint_config.model_dump(exclude_none=True)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate config: {str(e)}"
        )

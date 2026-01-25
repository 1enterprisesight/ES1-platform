"""Config versions API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models import ConfigVersion, EventLog
from app.services.config_validator import get_validator
from app.services.config_diff import compare_configs

router = APIRouter(prefix="/config-versions", tags=["config-versions"])


class ActiveConfigResponse(BaseModel):
    """Active config response schema."""

    version_id: UUID
    version: int
    deployed_at: str
    deployed_by: str
    endpoint_count: int
    config_snapshot: dict

    class Config:
        from_attributes = True


@router.get("/active", response_model=ActiveConfigResponse)
async def get_active_config(
    db: AsyncSession = Depends(get_db),
):
    """Get the currently active configuration version."""
    query = select(ConfigVersion).where(ConfigVersion.is_active == True)
    result = await db.execute(query)
    config_version = result.scalar_one_or_none()

    if not config_version:
        raise HTTPException(status_code=404, detail="No active configuration found")

    # Count endpoints in config snapshot
    endpoint_count = len(config_version.config_snapshot.get("endpoints", []))

    return ActiveConfigResponse(
        version_id=config_version.id,
        version=config_version.version,
        deployed_at=config_version.deployed_to_gateway_at.isoformat() + 'Z'
        if config_version.deployed_to_gateway_at
        else config_version.created_at.isoformat() + 'Z',
        deployed_by=config_version.created_by,
        endpoint_count=endpoint_count,
        config_snapshot=config_version.config_snapshot,
    )


@router.get("/pending", response_model=List[ActiveConfigResponse])
async def get_pending_config_versions(
    db: AsyncSession = Depends(get_db),
):
    """Get all configuration versions pending approval."""
    query = select(ConfigVersion).where(ConfigVersion.status == 'pending_approval').order_by(ConfigVersion.created_at.desc())
    result = await db.execute(query)
    config_versions = result.scalars().all()

    return [
        ActiveConfigResponse(
            version_id=cv.id,
            version=cv.version,
            deployed_at=cv.created_at.isoformat() + 'Z',
            deployed_by=cv.created_by,
            endpoint_count=len(cv.config_snapshot.get("endpoints", [])),
            config_snapshot=cv.config_snapshot,
        )
        for cv in config_versions
    ]


@router.get("/approved", response_model=List[ActiveConfigResponse])
async def get_approved_config_versions(
    db: AsyncSession = Depends(get_db),
):
    """Get all approved configuration versions ready for deployment."""
    query = select(ConfigVersion).where(
        ConfigVersion.status == 'approved',
        ConfigVersion.is_active == False
    ).order_by(ConfigVersion.approved_at.desc())
    result = await db.execute(query)
    config_versions = result.scalars().all()

    return [
        ActiveConfigResponse(
            version_id=cv.id,
            version=cv.version,
            deployed_at=cv.approved_at.isoformat() + 'Z' if cv.approved_at else cv.created_at.isoformat() + 'Z',
            deployed_by=cv.approved_by if cv.approved_by else cv.created_by,
            endpoint_count=len(cv.config_snapshot.get("endpoints", [])),
            config_snapshot=cv.config_snapshot,
        )
        for cv in config_versions
    ]


@router.get("/{version_id}", response_model=ActiveConfigResponse)
async def get_config_version(
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific configuration version by ID."""
    config_version = await db.get(ConfigVersion, version_id)

    if not config_version:
        raise HTTPException(status_code=404, detail="Configuration version not found")

    # Count endpoints in config snapshot
    endpoint_count = len(config_version.config_snapshot.get("endpoints", []))

    return ActiveConfigResponse(
        version_id=config_version.id,
        version=config_version.version,
        deployed_at=config_version.deployed_to_gateway_at.isoformat() + 'Z'
        if config_version.deployed_to_gateway_at
        else config_version.created_at.isoformat() + 'Z',
        deployed_by=config_version.created_by,
        endpoint_count=endpoint_count,
        config_snapshot=config_version.config_snapshot,
    )


# Schemas for submit-draft endpoint
class SubmitDraftRequest(BaseModel):
    """Request schema for submitting draft config."""
    config: Dict[str, Any]


class SubmitDraftResponse(BaseModel):
    """Response schema for submit draft."""
    version_id: UUID
    version: int
    status: str
    changes_count: int
    changes: List[Dict[str, Any]]


@router.post("/submit-draft", response_model=SubmitDraftResponse)
async def submit_draft_for_approval(
    request: SubmitDraftRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit draft config for approval.

    Validates config against KrakenD parser, checks for existing pending approval,
    and saves as new config version with pending_approval status.
    """
    # 1. Validate config structure (basic)
    if 'endpoints' not in request.config:
        raise HTTPException(status_code=400, detail="Invalid config: missing 'endpoints' field")

    # 2. Validate against KrakenD parser (K8s Job or local validation)
    validator = get_validator()
    is_valid, error_msg = await validator.validate_config(request.config)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Config validation failed: {error_msg}")

    # 3. Check for existing pending approval (ONE AT A TIME)
    pending_query = select(ConfigVersion).where(ConfigVersion.status == 'pending_approval')
    pending_result = await db.execute(pending_query)
    if pending_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A config is already pending approval. Please approve or reject it first."
        )

    # 4. Get next version number
    version_query = select(ConfigVersion).order_by(ConfigVersion.version.desc()).limit(1)
    version_result = await db.execute(version_query)
    latest = version_result.scalar_one_or_none()
    next_version = latest.version + 1 if latest else 1

    # 5. Get active config for diff
    active_query = select(ConfigVersion).where(ConfigVersion.is_active == True)
    active_result = await db.execute(active_query)
    active_config = active_result.scalar_one_or_none()

    # 6. Generate changes diff
    changes = compare_configs(
        active_config.config_snapshot if active_config else {},
        request.config
    )

    # 7. Create config_version record
    config_version = ConfigVersion(
        version=next_version,
        config_snapshot=request.config,
        status='pending_approval',
        is_active=False,
        created_by='admin',  # TODO: Get from auth when implemented
        created_at=datetime.utcnow()
    )
    db.add(config_version)
    await db.commit()
    await db.refresh(config_version)

    # 8. Log config submitted event
    event = EventLog(
        event_type="config_submitted",
        entity_type="config_version",
        entity_id=config_version.id,
        user_id="admin",  # TODO: Get from auth
        event_metadata={
            "version": config_version.version,
            "endpoint_count": len(request.config.get("endpoints", [])),
            "changes_count": len(changes)
        }
    )
    db.add(event)
    await db.commit()

    # 9. Return result
    return SubmitDraftResponse(
        version_id=config_version.id,
        version=config_version.version,
        status=config_version.status,
        changes_count=len(changes),
        changes=changes
    )


# Schemas for approve endpoint
class ApproveRequest(BaseModel):
    """Request schema for approving config."""
    approved_by: str


class ApproveResponse(BaseModel):
    """Response schema for approve action."""
    approved: bool
    version_id: UUID
    approved_by: str
    approved_at: str


@router.post("/{version_id}/approve", response_model=ApproveResponse)
async def approve_config(
    version_id: UUID,
    request: ApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve pending config. Changes status to 'approved'.

    Updates config_version status and sets approval metadata
    (approved_by and approved_at timestamp).
    """
    # 1. Get config_version (must be pending_approval)
    result = await db.execute(
        select(ConfigVersion).where(
            ConfigVersion.id == version_id,
            ConfigVersion.status == 'pending_approval'
        )
    )
    config_version = result.scalar_one_or_none()

    if not config_version:
        raise HTTPException(
            status_code=404,
            detail="Config not found or not pending approval"
        )

    # 2. Update config_version status
    config_version.status = 'approved'
    config_version.approved_by = request.approved_by
    config_version.approved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(config_version)

    # 3. Log config approved event
    event = EventLog(
        event_type="config_approved",
        entity_type="config_version",
        entity_id=config_version.id,
        user_id=request.approved_by,
        event_metadata={
            "version": config_version.version,
            "approved_by": request.approved_by
        }
    )
    db.add(event)
    await db.commit()

    # 4. Return result
    return ApproveResponse(
        approved=True,
        version_id=config_version.id,
        approved_by=config_version.approved_by,
        approved_at=config_version.approved_at.isoformat() + 'Z'
    )


# Schemas for reject endpoint
class RejectRequest(BaseModel):
    """Request schema for rejecting config."""
    rejected_by: str
    reason: str


class RejectResponse(BaseModel):
    """Response schema for reject action."""
    rejected: bool
    version_id: UUID
    rejected_by: str
    rejected_at: str
    reason: str


@router.post("/{version_id}/reject", response_model=RejectResponse)
async def reject_config(
    version_id: UUID,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reject pending or approved config. Changes status to 'rejected'.

    Updates config_version status and sets rejection metadata
    (rejected_by, rejected_at, and rejection_reason).
    """
    # Validate reason is not empty
    if not request.reason or not request.reason.strip():
        raise HTTPException(
            status_code=400,
            detail="Rejection reason is required"
        )

    # 1. Get config_version (must be pending_approval or approved)
    result = await db.execute(
        select(ConfigVersion).where(
            ConfigVersion.id == version_id,
            ConfigVersion.status.in_(['pending_approval', 'approved'])
        )
    )
    config_version = result.scalar_one_or_none()

    if not config_version:
        raise HTTPException(
            status_code=404,
            detail="Config not found or not rejectable (must be pending or approved)"
        )

    # 2. Update config_version status
    config_version.status = 'rejected'
    config_version.rejected_by = request.rejected_by
    config_version.rejected_at = datetime.utcnow()
    config_version.rejection_reason = request.reason

    await db.commit()
    await db.refresh(config_version)

    # 3. Log config rejected event
    event = EventLog(
        event_type="config_rejected",
        entity_type="config_version",
        entity_id=config_version.id,
        user_id=request.rejected_by,
        event_metadata={
            "version": config_version.version,
            "rejected_by": request.rejected_by,
            "reason": request.reason
        }
    )
    db.add(event)
    await db.commit()

    # 4. Return result
    return RejectResponse(
        rejected=True,
        version_id=config_version.id,
        rejected_by=config_version.rejected_by,
        rejected_at=config_version.rejected_at.isoformat() + 'Z',
        reason=config_version.rejection_reason
    )

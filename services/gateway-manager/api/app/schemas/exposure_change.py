"""Exposure change schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any
from uuid import UUID


class ExposureChangeCreate(BaseModel):
    """Schema for creating an exposure change (draft)."""

    resource_id: UUID
    change_type: str = Field(..., max_length=20)  # add, remove, modify
    exposure_id: UUID | None = None  # NULL for new additions
    settings_before: dict[str, Any] | None = None  # For modify: old settings
    settings_after: dict[str, Any] | None = None   # For add/modify: new settings
    requested_by: str = Field(..., max_length=255)


class ExposureChangeUpdate(BaseModel):
    """Schema for updating an exposure change (edit draft)."""

    settings_after: dict[str, Any] | None = None
    change_type: str | None = Field(None, max_length=20)
    exposure_id: UUID | None = None


class ExposureChangeResponse(BaseModel):
    """Schema for exposure change response."""

    id: UUID
    exposure_id: UUID | None
    resource_id: UUID
    change_type: str
    settings_before: dict[str, Any] | None
    settings_after: dict[str, Any] | None
    status: str  # draft, pending_approval, approved, rejected, deployed, cancelled
    batch_id: UUID | None

    # People and timestamps
    requested_by: str
    requested_at: datetime
    submitted_for_approval_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None

    # Deployment tracking
    deployed_in_version_id: UUID | None = None
    deployed_at: datetime | None = None

    class Config:
        from_attributes = True


class ExposureChangeListResponse(BaseModel):
    """Schema for paginated exposure change list."""

    items: list[ExposureChangeResponse]
    total: int
    page: int
    page_size: int

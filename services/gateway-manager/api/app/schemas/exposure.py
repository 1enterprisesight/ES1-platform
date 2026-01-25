"""Exposure schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any
from uuid import UUID


class ExposureBase(BaseModel):
    """Base exposure schema."""

    resource_id: UUID
    settings: dict[str, Any]
    generated_config: dict[str, Any]


class ExposureCreate(BaseModel):
    """Schema for creating an exposure."""

    resource_id: UUID
    settings: dict[str, Any]


class ExposureUpdate(BaseModel):
    """Schema for updating an exposure."""

    settings: dict[str, Any] | None = None
    status: str | None = Field(None, max_length=20)
    approved_by: str | None = Field(None, max_length=255)
    rejection_reason: str | None = None


class ResourceInfo(BaseModel):
    """Resource information embedded in exposure response."""

    id: UUID
    type: str
    source: str
    source_id: str
    name: str  # Extracted from metadata.name
    metadata: dict[str, Any]


class ExposureResponse(ExposureBase):
    """Schema for exposure response."""

    id: UUID
    status: str
    created_by: str
    created_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    class Config:
        from_attributes = True


class ExposureWithResourceResponse(ExposureResponse):
    """Schema for exposure response with resource details."""

    resource: ResourceInfo | None = None  # Resource information joined from discovered_resources


class ExposureListResponse(BaseModel):
    """Schema for paginated exposure list."""

    items: list[ExposureWithResourceResponse]
    total: int
    page: int
    page_size: int

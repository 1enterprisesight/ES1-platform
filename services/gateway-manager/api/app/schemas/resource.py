"""Resource schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any
from uuid import UUID


class ResourceBase(BaseModel):
    """Base resource schema."""

    type: str = Field(..., max_length=50)
    source: str = Field(..., max_length=50)
    source_id: str = Field(..., max_length=255)
    resource_metadata: dict[str, Any]


class ResourceCreate(ResourceBase):
    """Schema for creating a resource."""

    pass


class ResourceUpdate(BaseModel):
    """Schema for updating a resource."""

    resource_metadata: dict[str, Any] | None = None
    status: str | None = Field(None, max_length=20)


class ResourceResponse(ResourceBase):
    """Schema for resource response."""

    id: UUID
    discovered_at: datetime
    last_updated: datetime
    status: str

    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    """Schema for paginated resource list."""

    items: list[ResourceResponse]
    total: int
    page: int
    page_size: int

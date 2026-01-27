"""Pydantic schemas for the gateway module."""
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Resource Schemas
# =============================================================================

class ResourceBase(BaseModel):
    """Base resource schema."""
    type: str
    source: str
    source_id: str
    metadata: dict[str, Any]


class ResourceCreate(ResourceBase):
    """Schema for creating a resource."""
    pass


class ResourceUpdate(BaseModel):
    """Schema for updating a resource."""
    metadata: dict[str, Any] | None = None
    status: str | None = None


class ResourceResponse(BaseModel):
    """Schema for resource response."""
    id: UUID
    type: str
    source: str
    source_id: str
    metadata: dict[str, Any] = Field(validation_alias="resource_metadata")
    discovered_at: datetime
    last_updated: datetime
    status: str

    class Config:
        from_attributes = True
        populate_by_name = True


class ResourceListResponse(BaseModel):
    """Schema for paginated resource list."""
    items: list[ResourceResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Exposure Schemas
# =============================================================================

class ExposureBase(BaseModel):
    """Base exposure schema."""
    settings: dict[str, Any]


class ExposureCreate(ExposureBase):
    """Schema for creating an exposure."""
    resource_id: UUID
    created_by: str


class ExposureUpdate(BaseModel):
    """Schema for updating an exposure."""
    settings: dict[str, Any] | None = None


class ResourceInfo(BaseModel):
    """Brief resource info for exposure response."""
    id: UUID
    type: str
    source: str
    source_id: str
    metadata: dict[str, Any] = Field(validation_alias="resource_metadata")

    class Config:
        from_attributes = True
        populate_by_name = True


class ExposureResponse(ExposureBase):
    """Schema for exposure response."""
    id: UUID
    resource_id: UUID
    generated_config: dict[str, Any]
    status: str
    created_by: str
    created_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    class Config:
        from_attributes = True


class ExposureWithResourceResponse(ExposureResponse):
    """Schema for exposure with resource details."""
    resource: ResourceInfo | None = None


class ExposureListResponse(BaseModel):
    """Schema for paginated exposure list."""
    items: list[ExposureWithResourceResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Exposure Change Schemas
# =============================================================================

class ExposureChangeCreate(BaseModel):
    """Schema for creating an exposure change."""
    resource_id: UUID
    change_type: str  # add, remove, modify
    settings: dict[str, Any] | None = None
    requested_by: str


class ExposureChangeUpdate(BaseModel):
    """Schema for updating an exposure change."""
    settings: dict[str, Any] | None = None
    status: str | None = None


class ExposureChangeResponse(BaseModel):
    """Schema for exposure change response."""
    id: UUID
    exposure_id: UUID | None
    resource_id: UUID
    change_type: str
    settings_before: dict[str, Any] | None
    settings_after: dict[str, Any] | None
    status: str
    batch_id: UUID | None
    requested_by: str
    requested_at: datetime
    approved_by: str | None
    approved_at: datetime | None
    rejected_by: str | None
    rejected_at: datetime | None
    rejection_reason: str | None

    class Config:
        from_attributes = True


class ExposureChangeListResponse(BaseModel):
    """Schema for paginated exposure change list."""
    items: list[ExposureChangeResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Config Version Schemas
# =============================================================================

class ConfigVersionResponse(BaseModel):
    """Schema for config version response."""
    id: UUID
    version: int
    config_snapshot: dict[str, Any]
    created_by: str
    created_at: datetime
    commit_message: str | None
    is_active: bool
    deployed_to_gateway_at: datetime | None
    status: str | None

    class Config:
        from_attributes = True


class ConfigVersionListResponse(BaseModel):
    """Schema for paginated config version list."""
    items: list[ConfigVersionResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Deployment Schemas
# =============================================================================

class DeploymentCreate(BaseModel):
    """Schema for creating a deployment."""
    deployed_by: str
    commit_message: str | None = None


class DeploymentResponse(BaseModel):
    """Schema for deployment response."""
    id: UUID
    version_id: UUID
    status: str
    deployed_by: str
    deployed_at: datetime
    completed_at: datetime | None
    health_check_passed: bool | None
    error_message: str | None

    class Config:
        from_attributes = True


class DeploymentListResponse(BaseModel):
    """Schema for paginated deployment list."""
    items: list[DeploymentResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Gateway Health Schemas
# =============================================================================

class GatewayHealthResponse(BaseModel):
    """Schema for gateway health status."""
    status: str  # healthy, degraded, unhealthy
    mode: str  # docker, kubernetes
    pod_count: int
    running_pods: int
    failed_health_checks: int
    error: str | None = None


# =============================================================================
# Action Schemas
# =============================================================================

class ApproveRequest(BaseModel):
    """Schema for approval request."""
    approved_by: str
    comments: str | None = None


class RejectRequest(BaseModel):
    """Schema for rejection request."""
    rejected_by: str
    reason: str


class RollbackRequest(BaseModel):
    """Schema for rollback request."""
    version: int
    deployed_by: str
    reason: str | None = None


# =============================================================================
# Current Config Schemas
# =============================================================================

class CurrentConfigResponse(BaseModel):
    """Schema for current gateway config response."""
    config: dict[str, Any] | None
    config_path: str | None = None
    mode: str  # docker, kubernetes
    has_config: bool
    endpoint_count: int = 0


class ConfigFileInfo(BaseModel):
    """Schema for config file version info."""
    version: int
    file: str
    modified_at: str


class ConfigDiffRequest(BaseModel):
    """Schema for requesting config diff between versions."""
    version_a: int
    version_b: int


class ConfigDiffResponse(BaseModel):
    """Schema for config diff response."""
    version_a: int
    version_b: int
    diff: list[dict[str, Any]]  # List of differences
    added_endpoints: list[str]
    removed_endpoints: list[str]
    modified_endpoints: list[str]

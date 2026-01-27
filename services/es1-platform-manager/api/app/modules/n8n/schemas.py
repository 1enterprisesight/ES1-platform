"""Pydantic schemas for the n8n module."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""
    id: str
    name: str
    active: bool
    created_at: str | None = None
    updated_at: str | None = None
    tags: list[str] = []
    nodes_count: int = 0

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    """Schema for workflow list response."""
    workflows: list[WorkflowResponse]
    total: int


class WorkflowDetailResponse(WorkflowResponse):
    """Schema for detailed workflow response."""
    nodes: list[dict[str, Any]] = []
    connections: dict[str, Any] = {}
    settings: dict[str, Any] = {}


class ExecuteWorkflowRequest(BaseModel):
    """Schema for executing a workflow."""
    data: dict[str, Any] | None = None


class ExecutionResponse(BaseModel):
    """Schema for execution response."""
    id: str
    workflow_id: str
    workflow_name: str | None = None
    status: str  # running, success, error, waiting
    started_at: str | None = None
    finished_at: str | None = None
    mode: str | None = None  # manual, trigger, webhook

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """Schema for execution list response."""
    executions: list[ExecutionResponse]
    total: int


class ExecutionDetailResponse(ExecutionResponse):
    """Schema for detailed execution response."""
    data: dict[str, Any] = {}
    error: str | None = None


class CredentialResponse(BaseModel):
    """Schema for credential response."""
    id: str
    name: str
    type: str
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


class CredentialListResponse(BaseModel):
    """Schema for credential list response."""
    credentials: list[CredentialResponse]
    total: int


class N8NHealthResponse(BaseModel):
    """Schema for n8n health response."""
    status: str  # healthy, unhealthy, disabled, setup_required
    message: str | None = None
    error: str | None = None
    setup_url: str | None = None  # URL to complete setup when status is setup_required

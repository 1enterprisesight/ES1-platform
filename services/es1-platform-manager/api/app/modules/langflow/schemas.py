"""Pydantic schemas for the Langflow module."""
from typing import Any
from pydantic import BaseModel


class FlowBase(BaseModel):
    """Base flow schema."""
    name: str
    description: str | None = None


class FlowResponse(FlowBase):
    """Schema for flow response."""
    id: str
    endpoint_name: str | None = None
    is_component: bool = False
    updated_at: str | None = None
    folder_id: str | None = None

    class Config:
        from_attributes = True


class FlowListResponse(BaseModel):
    """Schema for flow list response."""
    flows: list[FlowResponse]
    total: int


class FlowCreateRequest(FlowBase):
    """Schema for creating a flow."""
    data: dict[str, Any] | None = None


class RunFlowRequest(BaseModel):
    """Schema for running a flow."""
    input_value: str
    input_type: str = "chat"
    output_type: str = "chat"
    tweaks: dict[str, Any] | None = None
    session_id: str | None = None


class FlowRunResponse(BaseModel):
    """Schema for flow run response."""
    outputs: list[dict[str, Any]]
    session_id: str | None = None


class LangflowHealthResponse(BaseModel):
    """Schema for Langflow health response."""
    status: str
    message: str | None = None


class DiscoveryResultResponse(BaseModel):
    """Schema for discovery result."""
    flows_discovered: int
    message: str

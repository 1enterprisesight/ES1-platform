"""Pydantic schemas for the Observability module."""
from typing import Any
from pydantic import BaseModel


class TraceResponse(BaseModel):
    """Schema for trace response."""
    id: str
    name: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    input: Any | None = None
    output: Any | None = None
    metadata: dict[str, Any] | None = None
    timestamp: str | None = None
    level: str | None = None

    class Config:
        from_attributes = True


class TraceListResponse(BaseModel):
    """Schema for trace list response."""
    data: list[TraceResponse]
    meta: dict[str, Any]


class SessionResponse(BaseModel):
    """Schema for session response."""
    id: str
    created_at: str | None = None
    project_id: str | None = None

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Schema for session list response."""
    data: list[SessionResponse]
    meta: dict[str, Any]


class ObservationResponse(BaseModel):
    """Schema for observation response."""
    id: str
    trace_id: str
    type: str  # SPAN, GENERATION, EVENT
    name: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    input: Any | None = None
    output: Any | None = None
    level: str | None = None
    model: str | None = None
    usage: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class ObservationListResponse(BaseModel):
    """Schema for observation list response."""
    data: list[ObservationResponse]
    meta: dict[str, Any]


class LangfuseHealthResponse(BaseModel):
    """Schema for Langfuse health response."""
    status: str
    message: str | None = None
    setup_url: str | None = None


class MetricsResponse(BaseModel):
    """Schema for metrics response."""
    total_traces: int = 0
    total_observations: int = 0
    total_generations: int = 0
    daily_traces: list[dict[str, Any]] = []

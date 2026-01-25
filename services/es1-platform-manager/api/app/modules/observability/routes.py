"""API routes for the Observability module."""
from fastapi import APIRouter, HTTPException, Query

from .client import langfuse_client
from .schemas import (
    TraceResponse,
    TraceListResponse,
    SessionResponse,
    SessionListResponse,
    ObservationListResponse,
    LangfuseHealthResponse,
    MetricsResponse,
)

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/health", response_model=LangfuseHealthResponse)
async def get_langfuse_health():
    """Check Langfuse health status."""
    result = await langfuse_client.health_check()
    return LangfuseHealthResponse(
        status=result.get("status", "unknown"),
        message=result.get("message") or result.get("error"),
    )


@router.get("/traces", response_model=TraceListResponse)
async def list_traces(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user_id: str | None = None,
    session_id: str | None = None,
    name: str | None = None,
):
    """List traces from Langfuse."""
    try:
        result = await langfuse_client.list_traces(
            page=page,
            limit=limit,
            user_id=user_id,
            session_id=session_id,
            name=name,
        )
        return TraceListResponse(
            data=[
                TraceResponse(
                    id=t.get("id", ""),
                    name=t.get("name"),
                    user_id=t.get("userId"),
                    session_id=t.get("sessionId"),
                    input=t.get("input"),
                    output=t.get("output"),
                    metadata=t.get("metadata"),
                    timestamp=t.get("timestamp"),
                    level=t.get("level"),
                )
                for t in result.get("data", [])
            ],
            meta=result.get("meta", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(trace_id: str):
    """Get details of a specific trace."""
    try:
        t = await langfuse_client.get_trace(trace_id)
        return TraceResponse(
            id=t.get("id", trace_id),
            name=t.get("name"),
            user_id=t.get("userId"),
            session_id=t.get("sessionId"),
            input=t.get("input"),
            output=t.get("output"),
            metadata=t.get("metadata"),
            timestamp=t.get("timestamp"),
            level=t.get("level"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """List sessions from Langfuse."""
    try:
        result = await langfuse_client.list_sessions(page=page, limit=limit)
        return SessionListResponse(
            data=[
                SessionResponse(
                    id=s.get("id", ""),
                    created_at=s.get("createdAt"),
                    project_id=s.get("projectId"),
                )
                for s in result.get("data", [])
            ],
            meta=result.get("meta", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get details of a specific session."""
    try:
        s = await langfuse_client.get_session(session_id)
        return SessionResponse(
            id=s.get("id", session_id),
            created_at=s.get("createdAt"),
            project_id=s.get("projectId"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/observations", response_model=ObservationListResponse)
async def list_observations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    trace_id: str | None = None,
    type: str | None = None,
):
    """List observations from Langfuse."""
    try:
        result = await langfuse_client.list_observations(
            page=page,
            limit=limit,
            trace_id=trace_id,
            type=type,
        )
        from .schemas import ObservationResponse
        return ObservationListResponse(
            data=[
                ObservationResponse(
                    id=o.get("id", ""),
                    trace_id=o.get("traceId", ""),
                    type=o.get("type", "SPAN"),
                    name=o.get("name"),
                    start_time=o.get("startTime"),
                    end_time=o.get("endTime"),
                    input=o.get("input"),
                    output=o.get("output"),
                    level=o.get("level"),
                    model=o.get("model"),
                    usage=o.get("usage"),
                )
                for o in result.get("data", [])
            ],
            meta=result.get("meta", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get aggregated metrics from Langfuse."""
    try:
        metrics = await langfuse_client.get_metrics()
        return MetricsResponse(
            total_traces=metrics.get("totalTraces", 0),
            total_observations=metrics.get("totalObservations", 0),
            total_generations=metrics.get("totalGenerations", 0),
            daily_traces=metrics.get("dailyTraces", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

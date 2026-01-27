"""API routes for traffic monitoring and audit logs."""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter(prefix="/traffic", tags=["Traffic Monitoring"])


@router.get("/stats")
async def get_traffic_stats(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Get traffic statistics for the specified time period."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                COUNT(*) as total_requests,
                COUNT(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 END) as success_count,
                COUNT(CASE WHEN response_status >= 400 AND response_status < 500 THEN 1 END) as client_error_count,
                COUNT(CASE WHEN response_status >= 500 THEN 1 END) as server_error_count,
                AVG(latency_ms) as avg_latency_ms,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as p50_latency_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency_ms
            FROM audit.api_requests
            WHERE timestamp >= :since
        """),
        {"since": since},
    )
    row = result.mappings().first()

    if not row or row["total_requests"] == 0:
        return {
            "period_hours": hours,
            "total_requests": 0,
            "success_count": 0,
            "client_error_count": 0,
            "server_error_count": 0,
            "success_rate": 0,
            "avg_latency_ms": 0,
            "p50_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
        }

    total = row["total_requests"]
    success = row["success_count"] or 0

    return {
        "period_hours": hours,
        "total_requests": total,
        "success_count": success,
        "client_error_count": row["client_error_count"] or 0,
        "server_error_count": row["server_error_count"] or 0,
        "success_rate": round((success / total) * 100, 2) if total > 0 else 0,
        "avg_latency_ms": round(row["avg_latency_ms"] or 0, 2),
        "p50_latency_ms": round(row["p50_latency_ms"] or 0, 2),
        "p95_latency_ms": round(row["p95_latency_ms"] or 0, 2),
        "p99_latency_ms": round(row["p99_latency_ms"] or 0, 2),
    }


@router.get("/requests")
async def get_recent_requests(
    limit: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = Query(None, description="Filter: success, error, all"),
    path_filter: Optional[str] = Query(None, description="Filter by path prefix"),
    db: AsyncSession = Depends(get_db),
):
    """Get recent API requests from audit log."""
    conditions = []
    params = {"limit": limit}

    if status_filter == "success":
        conditions.append("response_status >= 200 AND response_status < 300")
    elif status_filter == "error":
        conditions.append("response_status >= 400")

    if path_filter:
        conditions.append("path LIKE :path_filter")
        params["path_filter"] = f"{path_filter}%"

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    result = await db.execute(
        text(f"""
            SELECT
                id, request_id, timestamp, source_service, source_ip,
                method, path, response_status, latency_ms
            FROM audit.api_requests
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit
        """),
        params,
    )
    rows = result.mappings().all()

    return {
        "requests": [dict(row) for row in rows],
        "total": len(rows),
    }


@router.get("/requests/{request_id}")
async def get_request_details(
    request_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific request by correlation ID."""
    result = await db.execute(
        text("""
            SELECT * FROM audit.api_requests
            WHERE request_id = :request_id
            ORDER BY timestamp
        """),
        {"request_id": request_id},
    )
    rows = result.mappings().all()

    if not rows:
        return {"request_id": request_id, "requests": [], "total": 0}

    return {
        "request_id": request_id,
        "requests": [dict(row) for row in rows],
        "total": len(rows),
    }


@router.get("/endpoints")
async def get_endpoint_stats(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics grouped by endpoint."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                method,
                path,
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency_ms,
                COUNT(CASE WHEN response_status >= 400 THEN 1 END) as error_count
            FROM audit.api_requests
            WHERE timestamp >= :since
            GROUP BY method, path
            ORDER BY request_count DESC
            LIMIT :limit
        """),
        {"since": since, "limit": limit},
    )
    rows = result.mappings().all()

    return {
        "period_hours": hours,
        "endpoints": [
            {
                "method": row["method"],
                "path": row["path"],
                "request_count": row["request_count"],
                "avg_latency_ms": round(row["avg_latency_ms"] or 0, 2),
                "error_count": row["error_count"] or 0,
                "error_rate": round(
                    ((row["error_count"] or 0) / row["request_count"]) * 100, 2
                ) if row["request_count"] > 0 else 0,
            }
            for row in rows
        ],
    }


@router.get("/services")
async def get_service_stats(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics grouped by calling service."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                COALESCE(source_service, 'external') as service,
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency_ms,
                COUNT(CASE WHEN response_status >= 400 THEN 1 END) as error_count
            FROM audit.api_requests
            WHERE timestamp >= :since
            GROUP BY source_service
            ORDER BY request_count DESC
        """),
        {"since": since},
    )
    rows = result.mappings().all()

    return {
        "period_hours": hours,
        "services": [
            {
                "service": row["service"],
                "request_count": row["request_count"],
                "avg_latency_ms": round(row["avg_latency_ms"] or 0, 2),
                "error_count": row["error_count"] or 0,
            }
            for row in rows
        ],
    }


@router.get("/timeline")
async def get_request_timeline(
    hours: int = Query(24, ge=1, le=168),
    interval_minutes: int = Query(60, ge=5, le=1440),
    db: AsyncSession = Depends(get_db),
):
    """Get request counts over time for charting."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text(f"""
            SELECT
                date_trunc('hour', timestamp) +
                    (EXTRACT(minute FROM timestamp)::int / :interval * :interval) * interval '1 minute' as time_bucket,
                COUNT(*) as request_count,
                COUNT(CASE WHEN response_status >= 400 THEN 1 END) as error_count,
                AVG(latency_ms) as avg_latency_ms
            FROM audit.api_requests
            WHERE timestamp >= :since
            GROUP BY time_bucket
            ORDER BY time_bucket
        """),
        {"since": since, "interval": interval_minutes},
    )
    rows = result.mappings().all()

    return {
        "period_hours": hours,
        "interval_minutes": interval_minutes,
        "data": [
            {
                "timestamp": row["time_bucket"].isoformat() if row["time_bucket"] else None,
                "request_count": row["request_count"],
                "error_count": row["error_count"] or 0,
                "avg_latency_ms": round(row["avg_latency_ms"] or 0, 2),
            }
            for row in rows
        ],
    }


@router.get("/errors")
async def get_recent_errors(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get recent error requests."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                id, request_id, timestamp, source_service, source_ip,
                method, path, response_status, latency_ms, error_code, error_message
            FROM audit.api_requests
            WHERE timestamp >= :since AND response_status >= 400
            ORDER BY timestamp DESC
            LIMIT :limit
        """),
        {"since": since, "limit": limit},
    )
    rows = result.mappings().all()

    return {
        "period_hours": hours,
        "errors": [dict(row) for row in rows],
        "total": len(rows),
    }

"""
Unified Models API - aggregates models from Ollama, MLflow, and tracks inference metrics.

This provides a single view of all models across the platform.
"""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/models", tags=["Models Inventory"])

OLLAMA_URL = settings.OLLAMA_URL
MLFLOW_URL = settings.MLFLOW_URL


# =============================================================================
# Model Inventory - Unified View
# =============================================================================

@router.get("/inventory")
async def get_model_inventory():
    """
    Get unified inventory of all models across the platform.

    Aggregates models from:
    - Ollama (local LLM models)
    - MLflow Model Registry (trained ML models)
    """
    inventory = {
        "ollama": {"status": "unknown", "models": [], "error": None},
        "mlflow": {"status": "unknown", "models": [], "error": None},
        "total_models": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Fetch Ollama models
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                inventory["ollama"] = {
                    "status": "healthy",
                    "models": [
                        {
                            "name": m.get("name"),
                            "type": "llm",
                            "source": "ollama",
                            "size_gb": round(m.get("size", 0) / (1024**3), 2),
                            "modified_at": m.get("modified_at"),
                            "family": m.get("details", {}).get("family"),
                            "parameter_size": m.get("details", {}).get("parameter_size"),
                            "quantization": m.get("details", {}).get("quantization_level"),
                        }
                        for m in models
                    ],
                    "error": None,
                }
            else:
                inventory["ollama"]["status"] = "error"
                inventory["ollama"]["error"] = f"HTTP {response.status_code}"
    except httpx.RequestError as e:
        inventory["ollama"]["status"] = "unavailable"
        inventory["ollama"]["error"] = str(e)

    # Fetch MLflow models
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{MLFLOW_URL}/api/2.0/mlflow/registered-models/search",
                params={"max_results": 100}
            )
            if response.status_code == 200:
                data = response.json()
                models = data.get("registered_models", [])
                inventory["mlflow"] = {
                    "status": "healthy",
                    "models": [
                        {
                            "name": m.get("name"),
                            "type": "ml",
                            "source": "mlflow",
                            "description": m.get("description"),
                            "latest_version": m.get("latest_versions", [{}])[0].get("version") if m.get("latest_versions") else None,
                            "stage": m.get("latest_versions", [{}])[0].get("current_stage") if m.get("latest_versions") else None,
                            "created_at": m.get("creation_timestamp"),
                            "updated_at": m.get("last_updated_timestamp"),
                        }
                        for m in models
                    ],
                    "error": None,
                }
            else:
                inventory["mlflow"]["status"] = "error"
                inventory["mlflow"]["error"] = f"HTTP {response.status_code}"
    except httpx.RequestError as e:
        inventory["mlflow"]["status"] = "unavailable"
        inventory["mlflow"]["error"] = str(e)

    # Calculate totals
    inventory["total_models"] = (
        len(inventory["ollama"]["models"]) +
        len(inventory["mlflow"]["models"])
    )

    return inventory


@router.get("/summary")
async def get_models_summary():
    """Get a quick summary of model counts by source and type."""
    summary = {
        "ollama": {"count": 0, "status": "unknown", "total_size_gb": 0},
        "mlflow": {"count": 0, "status": "unknown", "production": 0, "staging": 0},
        "total": 0,
    }

    # Ollama summary
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                summary["ollama"] = {
                    "count": len(models),
                    "status": "healthy",
                    "total_size_gb": round(sum(m.get("size", 0) for m in models) / (1024**3), 2),
                }
    except:
        summary["ollama"]["status"] = "unavailable"

    # MLflow summary
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{MLFLOW_URL}/api/2.0/mlflow/registered-models/search",
                params={"max_results": 100}
            )
            if response.status_code == 200:
                models = response.json().get("registered_models", [])
                production = 0
                staging = 0
                for m in models:
                    for v in m.get("latest_versions", []):
                        if v.get("current_stage") == "Production":
                            production += 1
                        elif v.get("current_stage") == "Staging":
                            staging += 1
                summary["mlflow"] = {
                    "count": len(models),
                    "status": "healthy",
                    "production": production,
                    "staging": staging,
                }
    except:
        summary["mlflow"]["status"] = "unavailable"

    summary["total"] = summary["ollama"]["count"] + summary["mlflow"]["count"]
    return summary


# =============================================================================
# Inference Metrics
# =============================================================================

@router.get("/inference/metrics")
async def get_inference_metrics(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """
    Get inference metrics from audit logs.

    Tracks:
    - Request counts by model
    - Average latency
    - Error rates
    - Tokens per second (where available)
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    # Query inference endpoints from audit log
    result = await db.execute(
        text("""
            SELECT
                path,
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency_ms,
                COUNT(CASE WHEN response_status >= 400 THEN 1 END) as error_count,
                MIN(timestamp) as first_request,
                MAX(timestamp) as last_request
            FROM audit.api_requests
            WHERE timestamp >= :since
            AND (
                path LIKE '/api/v1/ollama/%'
                OR path LIKE '/api/v1/agents/%'
                OR path LIKE '/api/v1/knowledge/search%'
            )
            GROUP BY path
            ORDER BY request_count DESC
        """),
        {"since": since},
    )
    rows = result.mappings().all()

    # Categorize by type
    metrics = {
        "period_hours": hours,
        "inference": [],
        "agents": [],
        "knowledge": [],
        "totals": {
            "total_requests": 0,
            "total_errors": 0,
            "avg_latency_ms": 0,
        }
    }

    total_requests = 0
    total_errors = 0
    total_latency = 0

    for row in rows:
        path = row["path"]
        entry = {
            "path": path,
            "request_count": row["request_count"],
            "avg_latency_ms": round(row["avg_latency_ms"] or 0, 2),
            "error_count": row["error_count"] or 0,
            "error_rate": round((row["error_count"] or 0) / row["request_count"] * 100, 2),
            "first_request": row["first_request"].isoformat() if row["first_request"] else None,
            "last_request": row["last_request"].isoformat() if row["last_request"] else None,
        }

        total_requests += row["request_count"]
        total_errors += row["error_count"] or 0
        total_latency += (row["avg_latency_ms"] or 0) * row["request_count"]

        if "/ollama/" in path:
            metrics["inference"].append(entry)
        elif "/agents/" in path:
            metrics["agents"].append(entry)
        elif "/knowledge/" in path:
            metrics["knowledge"].append(entry)

    metrics["totals"] = {
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate": round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
        "avg_latency_ms": round(total_latency / total_requests, 2) if total_requests > 0 else 0,
    }

    return metrics


@router.get("/inference/timeline")
async def get_inference_timeline(
    hours: int = Query(24, ge=1, le=168),
    interval_minutes: int = Query(60, ge=5, le=1440),
    db: AsyncSession = Depends(get_db),
):
    """Get inference request timeline for charting."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                date_trunc('hour', timestamp) +
                    (EXTRACT(minute FROM timestamp)::int / :interval * :interval) * interval '1 minute' as time_bucket,
                COUNT(*) as request_count,
                COUNT(CASE WHEN response_status >= 400 THEN 1 END) as error_count,
                AVG(latency_ms) as avg_latency_ms
            FROM audit.api_requests
            WHERE timestamp >= :since
            AND (
                path LIKE '/api/v1/ollama/%'
                OR path LIKE '/api/v1/agents/%'
                OR path LIKE '/api/v1/knowledge/search%'
            )
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


# =============================================================================
# Running Models Status
# =============================================================================

@router.get("/running")
async def get_running_models():
    """Get currently running/loaded models from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/ps")
            if response.status_code != 200:
                return {"running": [], "total": 0, "error": f"HTTP {response.status_code}"}

            data = response.json()
            models = data.get("models", [])

            return {
                "running": [
                    {
                        "name": m.get("name"),
                        "size_gb": round(m.get("size", 0) / (1024**3), 2),
                        "vram_gb": round(m.get("size_vram", 0) / (1024**3), 2) if m.get("size_vram") else None,
                        "expires_at": m.get("expires_at"),
                        "details": m.get("details", {}),
                    }
                    for m in models
                ],
                "total": len(models),
                "total_vram_gb": round(
                    sum(m.get("size_vram", 0) for m in models) / (1024**3), 2
                ),
            }
    except httpx.RequestError as e:
        return {"running": [], "total": 0, "error": str(e)}


# =============================================================================
# Health
# =============================================================================

@router.get("/health")
async def models_health():
    """Check health of all model serving backends."""
    health = {
        "ollama": {"status": "unknown"},
        "mlflow": {"status": "unknown"},
    }

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{OLLAMA_URL}/")
            health["ollama"]["status"] = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        health["ollama"]["status"] = "unavailable"

    # Check MLflow
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{MLFLOW_URL}/health")
            health["mlflow"]["status"] = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        health["mlflow"]["status"] = "unavailable"

    health["overall"] = "healthy" if all(
        h["status"] == "healthy" for h in health.values() if isinstance(h, dict)
    ) else "degraded"

    return health

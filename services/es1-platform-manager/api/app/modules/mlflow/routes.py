"""API routes for MLflow integration - experiments, runs, and model registry."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import httpx

from app.core.config import settings

router = APIRouter(prefix="/mlflow", tags=["MLflow"])

MLFLOW_URL = getattr(settings, 'MLFLOW_URL', 'http://es1-mlflow:5000')


async def mlflow_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make a request to the MLflow tracking server."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{MLFLOW_URL}/api/2.0/mlflow{endpoint}"
        response = await client.request(method, url, **kwargs)
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"MLflow API error: {response.text}"
            )
        return response.json()


# =============================================================================
# Experiments
# =============================================================================

@router.get("/experiments")
async def list_experiments(
    max_results: int = Query(100, ge=1, le=1000),
):
    """List all MLflow experiments."""
    try:
        data = await mlflow_request("GET", "/experiments/search", params={
            "max_results": max_results,
        })
        experiments = data.get("experiments", [])
        return {
            "experiments": [
                {
                    "experiment_id": exp.get("experiment_id"),
                    "name": exp.get("name"),
                    "artifact_location": exp.get("artifact_location"),
                    "lifecycle_stage": exp.get("lifecycle_stage"),
                    "creation_time": exp.get("creation_time"),
                    "last_update_time": exp.get("last_update_time"),
                    "tags": {t["key"]: t["value"] for t in exp.get("tags", [])},
                }
                for exp in experiments
            ],
            "total": len(experiments),
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {str(e)}")


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get a specific experiment by ID."""
    try:
        data = await mlflow_request("GET", "/experiments/get", params={
            "experiment_id": experiment_id,
        })
        exp = data.get("experiment", {})
        return {
            "experiment_id": exp.get("experiment_id"),
            "name": exp.get("name"),
            "artifact_location": exp.get("artifact_location"),
            "lifecycle_stage": exp.get("lifecycle_stage"),
            "creation_time": exp.get("creation_time"),
            "last_update_time": exp.get("last_update_time"),
            "tags": {t["key"]: t["value"] for t in exp.get("tags", [])},
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {str(e)}")


# =============================================================================
# Runs
# =============================================================================

@router.get("/experiments/{experiment_id}/runs")
async def list_runs(
    experiment_id: str,
    max_results: int = Query(100, ge=1, le=1000),
    order_by: str = Query("start_time DESC"),
):
    """List runs for an experiment."""
    try:
        data = await mlflow_request("POST", "/runs/search", json={
            "experiment_ids": [experiment_id],
            "max_results": max_results,
            "order_by": [order_by],
        })
        runs = data.get("runs", [])
        return {
            "runs": [
                {
                    "run_id": run.get("info", {}).get("run_id"),
                    "run_name": run.get("info", {}).get("run_name"),
                    "experiment_id": run.get("info", {}).get("experiment_id"),
                    "status": run.get("info", {}).get("status"),
                    "start_time": run.get("info", {}).get("start_time"),
                    "end_time": run.get("info", {}).get("end_time"),
                    "artifact_uri": run.get("info", {}).get("artifact_uri"),
                    "lifecycle_stage": run.get("info", {}).get("lifecycle_stage"),
                    "metrics": {m["key"]: m["value"] for m in run.get("data", {}).get("metrics", [])},
                    "params": {p["key"]: p["value"] for p in run.get("data", {}).get("params", [])},
                    "tags": {t["key"]: t["value"] for t in run.get("data", {}).get("tags", [])},
                }
                for run in runs
            ],
            "total": len(runs),
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {str(e)}")


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific run by ID."""
    try:
        data = await mlflow_request("GET", "/runs/get", params={"run_id": run_id})
        run = data.get("run", {})
        return {
            "run_id": run.get("info", {}).get("run_id"),
            "run_name": run.get("info", {}).get("run_name"),
            "experiment_id": run.get("info", {}).get("experiment_id"),
            "status": run.get("info", {}).get("status"),
            "start_time": run.get("info", {}).get("start_time"),
            "end_time": run.get("info", {}).get("end_time"),
            "artifact_uri": run.get("info", {}).get("artifact_uri"),
            "lifecycle_stage": run.get("info", {}).get("lifecycle_stage"),
            "metrics": {m["key"]: m["value"] for m in run.get("data", {}).get("metrics", [])},
            "params": {p["key"]: p["value"] for p in run.get("data", {}).get("params", [])},
            "tags": {t["key"]: t["value"] for t in run.get("data", {}).get("tags", [])},
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {str(e)}")


# =============================================================================
# Model Registry
# =============================================================================

@router.get("/models")
async def list_registered_models(
    max_results: int = Query(100, ge=1, le=1000),
):
    """List all registered models in the MLflow Model Registry."""
    try:
        data = await mlflow_request("GET", "/registered-models/search", params={
            "max_results": max_results,
        })
        models = data.get("registered_models", [])
        return {
            "models": [
                {
                    "name": model.get("name"),
                    "creation_timestamp": model.get("creation_timestamp"),
                    "last_updated_timestamp": model.get("last_updated_timestamp"),
                    "description": model.get("description"),
                    "latest_versions": [
                        {
                            "version": v.get("version"),
                            "current_stage": v.get("current_stage"),
                            "creation_timestamp": v.get("creation_timestamp"),
                            "last_updated_timestamp": v.get("last_updated_timestamp"),
                            "run_id": v.get("run_id"),
                            "status": v.get("status"),
                        }
                        for v in model.get("latest_versions", [])
                    ],
                    "tags": {t["key"]: t["value"] for t in model.get("tags", [])},
                }
                for model in models
            ],
            "total": len(models),
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {str(e)}")


@router.get("/models/{model_name}")
async def get_registered_model(model_name: str):
    """Get a specific registered model."""
    try:
        data = await mlflow_request("GET", "/registered-models/get", params={
            "name": model_name,
        })
        model = data.get("registered_model", {})
        return {
            "name": model.get("name"),
            "creation_timestamp": model.get("creation_timestamp"),
            "last_updated_timestamp": model.get("last_updated_timestamp"),
            "description": model.get("description"),
            "latest_versions": [
                {
                    "version": v.get("version"),
                    "current_stage": v.get("current_stage"),
                    "creation_timestamp": v.get("creation_timestamp"),
                    "last_updated_timestamp": v.get("last_updated_timestamp"),
                    "run_id": v.get("run_id"),
                    "status": v.get("status"),
                    "source": v.get("source"),
                    "run_link": v.get("run_link"),
                }
                for v in model.get("latest_versions", [])
            ],
            "tags": {t["key"]: t["value"] for t in model.get("tags", [])},
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {str(e)}")


@router.get("/models/{model_name}/versions")
async def list_model_versions(
    model_name: str,
    max_results: int = Query(100, ge=1, le=1000),
):
    """List all versions of a registered model."""
    try:
        data = await mlflow_request("GET", "/model-versions/search", params={
            "filter": f"name='{model_name}'",
            "max_results": max_results,
        })
        versions = data.get("model_versions", [])
        return {
            "model_name": model_name,
            "versions": [
                {
                    "version": v.get("version"),
                    "name": v.get("name"),
                    "current_stage": v.get("current_stage"),
                    "creation_timestamp": v.get("creation_timestamp"),
                    "last_updated_timestamp": v.get("last_updated_timestamp"),
                    "run_id": v.get("run_id"),
                    "status": v.get("status"),
                    "source": v.get("source"),
                    "description": v.get("description"),
                    "tags": {t["key"]: t["value"] for t in v.get("tags", [])},
                }
                for v in versions
            ],
            "total": len(versions),
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {str(e)}")


@router.post("/models/{model_name}/versions/{version}/stage")
async def transition_model_stage(
    model_name: str,
    version: str,
    stage: str = Query(..., description="Stage: None, Staging, Production, Archived"),
):
    """Transition a model version to a new stage."""
    valid_stages = ["None", "Staging", "Production", "Archived"]
    if stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage. Must be one of: {valid_stages}"
        )

    try:
        data = await mlflow_request("POST", "/model-versions/transition-stage", json={
            "name": model_name,
            "version": version,
            "stage": stage,
        })
        return {
            "message": f"Model {model_name} version {version} transitioned to {stage}",
            "model_version": data.get("model_version", {}),
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MLflow unavailable: {str(e)}")


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def mlflow_health():
    """Check MLflow tracking server health."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MLFLOW_URL}/health")
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "url": MLFLOW_URL,
            }
    except httpx.RequestError as e:
        return {
            "status": "unavailable",
            "url": MLFLOW_URL,
            "error": str(e),
        }

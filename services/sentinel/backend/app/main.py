"""Sentinel backend — workspace-scoped AI data dashboard.

Startup initializes PostgreSQL and an empty DuckDB instance.
Workspace data, silos, and agent loops are loaded lazily on activation.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS
from app.db import init_db
from app.database import init_pool, close_pool
from app.llm import shutdown_llm
from app.agent import stop_agent, is_agent_active
from app.auth import bootstrap_admin
from app.routes import silos, stream, tiles, ask, datasources
from app.routes import auth as auth_routes
from app.routes import datasets as dataset_routes
from app.routes import workspaces as workspace_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def _register_with_agent_router():
    """Register Sentinel as an agent in the Agent Router."""
    agent_router_url = os.environ.get("AGENT_ROUTER_URL", "http://agent-router:8102")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{agent_router_url}/agents/register", json={
                "name": "sentinel-analyst",
                "framework": "custom",
                "description": "AI-powered data analyst — ingests CSV datasets, discovers patterns, generates insight cards using Gemini LLM",
                "capabilities": [
                    "csv_analysis",
                    "anomaly_detection",
                    "trend_discovery",
                    "cross_dataset_correlation",
                    "natural_language_questions",
                    "automated_insight_generation",
                ],
                "metadata": {
                    "service_url": "http://sentinel-api:8010",
                    "ui_url": "http://sentinel-ui:80",
                    "gateway_prefix": "/api/v1/sentinel",
                    "llm_provider": "google_vertex_ai",
                    "llm_model": "gemini-2.5-flash",
                    "data_engine": "duckdb",
                    "storage": "postgresql",
                },
            })
            if resp.status_code in (200, 201):
                logger.info(f"Registered with Agent Router: {resp.json()}")
            else:
                logger.warning(f"Agent Router registration returned {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.info(f"Agent Router not available (will retry on next restart): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Sentinel backend…")

    # PostgreSQL pool + admin bootstrap
    try:
        await init_pool()
        await bootstrap_admin()
    except Exception as e:
        logger.warning(f"PostgreSQL init failed (auth disabled): {e}")

    # DuckDB — empty, workspaces load data lazily on activate
    init_db()

    # Register with Agent Router (non-blocking)
    asyncio.create_task(_register_with_agent_router())

    yield

    # Shutdown
    stop_agent()
    shutdown_llm()
    await close_pool()
    logger.info("Sentinel backend shut down")


app = FastAPI(title="Sentinel", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix="/api")
app.include_router(silos.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(tiles.router, prefix="/api")
app.include_router(ask.router, prefix="/api")
app.include_router(datasources.router, prefix="/api")
app.include_router(dataset_routes.router, prefix="/api")
app.include_router(workspace_routes.router, prefix="/api")


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "agent_running": is_agent_active(),
    }


# Version file written by deploy/update.sh
_version_file = Path(__file__).resolve().parent.parent.parent / ".deployed_version"
_version_file_vm = Path("/opt/sentinel/.deployed_version")


@app.get("/version")
def version():
    import json
    for vf in [_version_file, _version_file_vm]:
        try:
            if vf.exists():
                return json.loads(vf.read_text())
        except Exception:
            pass
    return {"tag": "dev", "commit": "local", "deployed_at": None}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.get("/api/service-info")
def service_info():
    """Service descriptor for platform discovery and registration."""
    return {
        "name": "sentinel",
        "display_name": "Sentinel",
        "description": "AI-powered data dashboard — upload CSVs, get automated insights",
        "version": version().get("tag", "dev"),
        "type": "analytics",
        "endpoints": {
            "api": "/api",
            "health": "/healthz",
            "ready": "/readyz",
            "stream": "/api/stream",
        },
        "capabilities": [
            "csv_upload",
            "automated_analysis",
            "silo_discovery",
            "interactive_questions",
            "workspace_management",
            "user_auth",
        ],
        "gateway_prefix": "/api/v1/sentinel",
        "ui_url": "/sentinel",
    }


# Serve frontend static files in production
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"status": "ok", "service": "sentinel"}

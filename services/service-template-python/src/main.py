"""
Service Template - Python
Replace SERVICE_NAME with your actual service name.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

SERVICE_NAME = "service-template-python"  # TODO: Replace with actual service name


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print(f"Starting {SERVICE_NAME}...")
    # TODO: Add startup logic (database connections, etc.)
    yield
    # TODO: Add shutdown logic
    print(f"Shutting down {SERVICE_NAME}...")


app = FastAPI(
    title=SERVICE_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Liveness probe endpoint."""
    return {"status": "healthy"}


@app.get("/ready")
async def readiness_check():
    """Readiness probe endpoint."""
    # TODO: Add dependency checks
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": SERVICE_NAME,
        "version": "0.1.0",
        "status": "running"
    }


# TODO: Add your service-specific endpoints below

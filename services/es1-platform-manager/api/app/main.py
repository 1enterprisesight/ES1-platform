"""FastAPI application for ES1 Platform Manager."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.init_db import create_tables
from app.core.database import AsyncSessionLocal
from app.core.events import event_bus, EventType
from app.core.logging import logger
from app.core.scheduler import discovery_scheduler
from app.core.middleware import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
    AuditMiddleware,
)
from app.core.auth import AuthService, get_current_user

# Import models to register them with SQLAlchemy
from app.modules.gateway.models import (
    DiscoveredResource,
    Exposure,
    ExposureChange,
    ConfigVersion,
    Deployment,
    Approval,
    EventLog,
)
from app.modules.settings.models import Setting, BrandingConfig

# Import routers
from app.modules.gateway.routes import router as gateway_router
from app.modules.airflow.routes import router as airflow_router
from app.modules.langflow.routes import router as langflow_router
from app.modules.observability.routes import router as observability_router
from app.modules.system.routes import router as system_router
from app.modules.auth.routes import router as auth_router
from app.modules.settings.routes import router as settings_router
from app.modules.n8n.routes import router as n8n_router
from app.modules.knowledge.routes import router as knowledge_router
from app.modules.traffic.routes import router as traffic_router
from app.modules.mlflow.routes import router as mlflow_router
from app.modules.ollama.routes import router as ollama_router
from app.modules.models.routes import router as models_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    logger.info("Starting Platform Manager...")
    await create_tables()
    logger.info("Database tables created/verified")

    # Initialize AuthService (verifies audit.api_keys table, seeds default key)
    async with AsyncSessionLocal() as db:
        await AuthService.initialize(db)
    logger.info("AuthService initialized")

    # Start discovery scheduler
    if settings.DISCOVERY_ENABLED:
        await discovery_scheduler.start()
        logger.info("Discovery scheduler started")

    # Emit startup event
    await event_bus.publish(
        EventType.SYSTEM_INFO,
        {"message": "Platform Manager started", "version": settings.PLATFORM_VERSION},
    )

    yield

    # Shutdown
    logger.info("Shutting down Platform Manager...")

    # Stop discovery scheduler
    if settings.DISCOVERY_ENABLED:
        await discovery_scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PLATFORM_VERSION,
    description="Platform Manager - Unified management for API Gateway, Workflows, and AI services",
    lifespan=lifespan,
)

# Add CORS middleware
# Note: allow_credentials=True is incompatible with allow_origins=["*"]
# When CORS_ORIGINS is ["*"], credentials are disabled for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.cors_allows_credentials,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
)

# Add custom middleware (order matters - first added = last executed)
# Audit logging (logs to database)
app.add_middleware(AuditMiddleware, enabled=True)
# Request logging (logs to stdout)
app.add_middleware(RequestLoggingMiddleware)
# Correlation ID (must be first to generate ID for other middleware)
app.add_middleware(CorrelationIdMiddleware)

# Include routers
# Auth-protected routers: require valid API key when AUTH_MODE != "none"
_auth_deps = [Depends(get_current_user)] if settings.auth_enabled else []

app.include_router(gateway_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(airflow_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(langflow_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(observability_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(system_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(settings_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(n8n_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(knowledge_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(traffic_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(mlflow_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(ollama_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
app.include_router(models_router, prefix=settings.API_V1_PREFIX, dependencies=_auth_deps)
# Auth router is always public (login/status endpoints must be accessible)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "modules": ["gateway", "airflow", "langflow", "observability", "automation", "knowledge", "agents", "traffic", "mlflow", "ollama", "models"],
    }


@app.get("/api/v1/events/stream")
async def event_stream(request: Request):
    """
    Server-Sent Events endpoint for real-time updates.

    Clients can connect to this endpoint to receive real-time updates
    about operations, deployments, and system status.
    """
    async def generate():
        queue = await event_bus.subscribe()
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "id": event.id,
                        "event": event.type.value,
                        "data": event.model_dump_json(),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "keepalive", "data": ""}
        finally:
            await event_bus.unsubscribe(queue)

    return EventSourceResponse(generate())


@app.get("/api/v1/events/history")
async def get_event_history(limit: int = 50):
    """Get recent event history."""
    events = await event_bus.get_history(limit=limit)
    return {"events": [e.model_dump() for e in events]}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", path=request.url.path)

    # Emit error event
    await event_bus.publish(
        EventType.SYSTEM_ERROR,
        {
            "error": str(exc),
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.RUNTIME_MODE != "kubernetes" else "An error occurred",
        },
    )

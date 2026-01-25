"""FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.init_db import create_tables

# IMPORTANT: Import all models BEFORE routes
# Models must be imported first so SQLAlchemy can register all tables
# and resolve foreign key relationships correctly
from app.models import (  # noqa: F401
    DiscoveredResource,
    Exposure,
    ExposureChange,
    ConfigVersion,
    Deployment,
    Approval,
    EventLog,
    BrandingConfig,
)

# Now import routes (which reference the models)
from app.routes import (
    resources_router,
    exposures_router,
    exposure_changes_router,
    deployments_router,
    integrations_router,
    metrics_router,
    events_router,
    gateway_router,
    config_versions_router,
    branding_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup: Create database tables
    await create_tables()
    yield
    # Shutdown: cleanup if needed


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="ES Core-GW API for managing API gateway configurations",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(resources_router, prefix=settings.API_V1_PREFIX)
app.include_router(exposures_router, prefix=settings.API_V1_PREFIX)
app.include_router(exposure_changes_router, prefix=settings.API_V1_PREFIX)
app.include_router(deployments_router, prefix=settings.API_V1_PREFIX)
app.include_router(integrations_router, prefix=settings.API_V1_PREFIX)
app.include_router(metrics_router, prefix=settings.API_V1_PREFIX)
app.include_router(events_router, prefix=settings.API_V1_PREFIX)
app.include_router(gateway_router, prefix=settings.API_V1_PREFIX)
app.include_router(config_versions_router, prefix=settings.API_V1_PREFIX)
app.include_router(branding_router, prefix=settings.API_V1_PREFIX)


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
    }

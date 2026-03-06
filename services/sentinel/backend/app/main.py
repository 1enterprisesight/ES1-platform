import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS
from app.db import init_db
from app.database import init_pool, close_pool
from app.profiler import discover_silos, silo_discovery_done, get_silos
from app.tiles import tile_store, recover_interacted_tiles
from app.llm import shutdown_llm
from app.agent import start_agent, stop_agent, is_agent_active
from app.auth import bootstrap_admin
from app.routes import silos, stream, tiles, ask, datasources
from app.routes import auth as auth_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def _background_init():
    """Run silo discovery + agent start in the background so the server can accept requests immediately."""
    try:
        await discover_silos()
        logger.info("Silo discovery complete")
        # Notify any connected frontends that silos are now available
        tile_store.broadcast_status("silos_ready")

        # Only start agent after successful silo discovery
        start_agent()
        logger.info("Agent started")
    except Exception as e:
        logger.error(f"Background init failed: {e}", exc_info=True)


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

    # DuckDB — fast (sync), do it inline
    counts = init_db()
    logger.info(f"Data loaded: {counts}")

    # Recover any interacted tiles that were evicted from the tile store
    recover_interacted_tiles()

    # Only start background LLM init if we have data loaded
    init_task = None
    if any(v > 0 for v in counts.values()):
        init_task = asyncio.create_task(_background_init())
        logger.info("Background init scheduled (data loaded)")
    else:
        logger.info("No data loaded — skipping agent/silo discovery")

    yield

    # Shutdown
    stop_agent()
    if init_task:
        init_task.cancel()
        try:
            await init_task
        except asyncio.CancelledError:
            pass
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


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "tiles": len(tile_store.tiles),
        "agent_running": is_agent_active(),
    }


# Version file written by deploy/update.sh
_version_file = Path(__file__).resolve().parent.parent.parent / ".deployed_version"
# Also check /opt/sentinel/.deployed_version for VM deploys
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
    from app.profiler import silo_discovery_done
    if not silo_discovery_done:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "silo discovery in progress"},
        )
    return {"status": "ready", "silos": len(get_silos())}


# Serve frontend static files in production (when frontend/dist exists)
# In local dev, Vite handles this via proxy
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"status": "ok", "service": "sentinel"}

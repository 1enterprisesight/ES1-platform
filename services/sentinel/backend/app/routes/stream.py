"""SSE stream — workspace-scoped tile broadcasting."""
import asyncio
import json
import logging

from fastapi import APIRouter, Request, Query
from sse_starlette.sse import EventSourceResponse

from app.auth import get_current_user
from app.tiles import get_tile_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stream")
async def stream(request: Request, workspace_id: str = Query(None)):
    """SSE stream scoped to a workspace.

    The workspace_id can be passed as a query param or inferred from the session.
    """
    # Resolve workspace_id
    ws_id = workspace_id
    if not ws_id:
        session = await get_current_user(request)
        if session and session.workspace_id:
            ws_id = session.workspace_id

    if not ws_id:
        # No workspace context — return empty stream
        async def empty():
            yield {"event": "error", "data": json.dumps({"message": "No active workspace"})}
        return EventSourceResponse(empty())

    tile_store = get_tile_store(ws_id)

    async def event_generator():
        queue = tile_store.subscribe()
        try:
            # Send all existing tiles as initial batch
            existing = tile_store.tiles
            if existing:
                yield {
                    "event": "initial_tiles",
                    "data": json.dumps([t.model_dump() for t in existing], default=str),
                }

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = event.get("type", "message")
                    payload = {k: v for k, v in event.items() if k != "type"}
                    yield {
                        "event": event_type,
                        "data": json.dumps(payload, default=str),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            tile_store.unsubscribe(queue)
            logger.info("SSE subscriber removed for workspace %s (remaining: %d)",
                        ws_id, len(tile_store._subscribers))

    return EventSourceResponse(event_generator(), ping=15)

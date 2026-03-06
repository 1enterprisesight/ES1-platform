import asyncio
import json
import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.tiles import tile_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stream")
async def stream(request: Request):
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
            logger.info("SSE subscriber removed (remaining: %d)", len(tile_store._subscribers))

    # ping=15 makes sse_starlette send transport-level pings every 15s.
    # When the client is gone, the write fails and the generator is closed,
    # triggering the finally block to unsubscribe.
    return EventSourceResponse(event_generator(), ping=15)

"""Tile and interaction routes — workspace-scoped."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_user, SessionInfo
from app.tiles import get_tile_store, get_interaction_store
from app.row_config import get_row_config

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_workspace_id(session: SessionInfo) -> str:
    if not session.workspace_id:
        raise HTTPException(status_code=400, detail="No active workspace")
    return session.workspace_id


@router.get("/tiles")
def list_tiles(session: SessionInfo = Depends(require_user)):
    workspace_id = _get_workspace_id(session)
    tile_store = get_tile_store(workspace_id)
    try:
        return [t.model_dump() for t in tile_store.tiles]
    except Exception as e:
        logger.error(f"list_tiles failed: {e}", exc_info=True)
        raise


class MoveRequest(BaseModel):
    column: str


@router.post("/tiles/{tile_id}/move")
async def move_tile(tile_id: int, body: MoveRequest, session: SessionInfo = Depends(require_user)):
    workspace_id = _get_workspace_id(session)
    tile_store = get_tile_store(workspace_id)

    valid = {r["id"] for r in get_row_config()} | {"resolved"}
    if body.column not in valid:
        raise HTTPException(400, f"column must be one of {valid}")
    tile = await tile_store.move_tile(tile_id, body.column)
    if not tile:
        raise HTTPException(404, "Tile not found")
    return tile.model_dump()


class InteractionRequest(BaseModel):
    tile_title: str = ""
    tile_silo: str = ""
    tile_summary: str = ""
    thumbs_up: int = Field(default=0, ge=0, le=1)
    thumbs_down: int = Field(default=0, ge=0, le=1)
    expanded: bool = False
    expand_duration_s: float = Field(default=0.0, ge=0.0, le=300.0)
    followup_questions: List[str] = Field(default_factory=list, max_length=10)


@router.post("/tiles/{tile_id}/interact")
async def interact_tile(tile_id: int, body: InteractionRequest, session: SessionInfo = Depends(require_user)):
    workspace_id = _get_workspace_id(session)
    interaction_store = get_interaction_store(workspace_id)
    interaction = await interaction_store.record(tile_id, body.model_dump())
    return interaction.model_dump()


@router.get("/interactions")
def list_interactions(session: SessionInfo = Depends(require_user)):
    workspace_id = _get_workspace_id(session)
    interaction_store = get_interaction_store(workspace_id)
    return {str(i.tile_id): i.model_dump() for i in interaction_store.get_all()}


@router.post("/interactions/reset")
async def reset_interactions(session: SessionInfo = Depends(require_user)):
    workspace_id = _get_workspace_id(session)
    interaction_store = get_interaction_store(workspace_id)
    await interaction_store.reset()
    return {"status": "ok"}


@router.post("/tiles/{tile_id}/interaction/reset")
async def reset_tile_interaction(tile_id: int, session: SessionInfo = Depends(require_user)):
    workspace_id = _get_workspace_id(session)
    tile_store = get_tile_store(workspace_id)
    interaction_store = get_interaction_store(workspace_id)

    await interaction_store.reset_one(tile_id)
    tile_removed = False
    for t in tile_store.tiles:
        if t.id == tile_id and t.column == "resolved" and "User Question" in t.sources:
            await tile_store.remove_tile(tile_id)
            tile_removed = True
            break
    return {"status": "ok", "tile_removed": tile_removed}

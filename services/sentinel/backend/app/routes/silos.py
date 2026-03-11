"""Silo routes — workspace-scoped."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.auth import require_user, SessionInfo
from app.profiler import get_silos, rediscover_silos
from app.row_config import get_row_config, update_row_config

router = APIRouter()


def _get_workspace_id(session: SessionInfo) -> str:
    if not session.workspace_id:
        raise HTTPException(status_code=400, detail="No active workspace")
    return session.workspace_id


@router.get("/silos")
def list_silos(session: SessionInfo = Depends(require_user)):
    workspace_id = _get_workspace_id(session)
    return get_silos(workspace_id)


@router.get("/silos/hints")
def list_hints(session: SessionInfo = Depends(require_user)):
    # Hints are now stored in workspace settings
    return {"hints": []}


class HintsRequest(BaseModel):
    hints: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("hints", mode="before")
    @classmethod
    def truncate_hints(cls, v):
        if isinstance(v, list):
            return [str(h)[:50] for h in v[:10]]
        return v


@router.post("/silos/rediscover")
async def rediscover(body: HintsRequest, session: SessionInfo = Depends(require_user)):
    workspace_id = _get_workspace_id(session)
    hints = body.hints if body.hints else None
    await rediscover_silos(workspace_id=workspace_id, hints=hints)
    return {"silos": get_silos(workspace_id), "hints": hints or []}


@router.get("/rows/config")
def list_row_config():
    return {"rows": get_row_config()}


class RowConfigItem(BaseModel):
    label: str
    description: str
    icon: Optional[str] = None
    bright: Optional[bool] = None


class RowConfigRequest(BaseModel):
    rows: List[RowConfigItem]


@router.post("/rows/config")
def save_row_config(body: RowConfigRequest):
    update_row_config([r.dict(exclude_none=True) for r in body.rows])
    return {"rows": get_row_config()}

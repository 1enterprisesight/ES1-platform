from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.profiler import get_silos, get_hints, rediscover_silos
from app.row_config import get_row_config, update_row_config

router = APIRouter()


@router.get("/silos")
def list_silos():
    return get_silos()


@router.get("/silos/hints")
def list_hints():
    return {"hints": get_hints() or []}


class HintsRequest(BaseModel):
    hints: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("hints", mode="before")
    @classmethod
    def truncate_hints(cls, v):
        if isinstance(v, list):
            return [str(h)[:50] for h in v[:10]]
        return v


@router.post("/silos/rediscover")
async def rediscover(body: HintsRequest):
    hints = body.hints if body.hints else None
    await rediscover_silos(hints)
    return {"silos": get_silos(), "hints": hints or []}


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

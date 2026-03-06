"""Workspace management: create, list, switch, delete, save/load state."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_user, SessionInfo
from app.database import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None
    dataset_ids: Optional[list[str]] = None


def _row_to_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "dataset_ids": row["dataset_ids"] if row["dataset_ids"] else [],
        "settings": row["settings"] if row["settings"] else {},
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "last_accessed": row["last_accessed"].isoformat() if row["last_accessed"] else None,
    }


async def ensure_default_workspace(user_id: str) -> dict:
    """Create a default workspace for the user if none exists. Returns the workspace."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM sentinel.workspaces WHERE user_id = $1 ORDER BY created_at LIMIT 1",
        uuid.UUID(user_id),
    )
    if row:
        return _row_to_dict(row)

    row = await pool.fetchrow(
        """INSERT INTO sentinel.workspaces (user_id, name)
           VALUES ($1, 'Default')
           RETURNING *""",
        uuid.UUID(user_id),
    )
    logger.info(f"Created default workspace for user {user_id}")
    return _row_to_dict(row)


async def set_session_workspace(token: str, workspace_id: str):
    """Update the session's active workspace."""
    pool = get_pool()
    await pool.execute(
        "UPDATE sentinel.sessions SET workspace_id = $1 WHERE token = $2",
        uuid.UUID(workspace_id), token,
    )


@router.get("/workspaces")
async def list_workspaces(session: SessionInfo = Depends(require_user)):
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM sentinel.workspaces WHERE user_id = $1 ORDER BY last_accessed DESC",
        uuid.UUID(session.user.id),
    )
    # Ensure at least one workspace exists
    if not rows:
        ws = await ensure_default_workspace(session.user.id)
        return {"workspaces": [ws]}
    return {"workspaces": [_row_to_dict(r) for r in rows]}


@router.post("/workspaces")
async def create_workspace(body: CreateWorkspaceRequest, session: SessionInfo = Depends(require_user)):
    pool = get_pool()
    row = await pool.fetchrow(
        """INSERT INTO sentinel.workspaces (user_id, name)
           VALUES ($1, $2) RETURNING *""",
        uuid.UUID(session.user.id), body.name,
    )
    return _row_to_dict(row)


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    body: UpdateWorkspaceRequest,
    session: SessionInfo = Depends(require_user),
):
    pool = get_pool()
    ws = await pool.fetchrow(
        "SELECT * FROM sentinel.workspaces WHERE id = $1 AND user_id = $2",
        uuid.UUID(workspace_id), uuid.UUID(session.user.id),
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if body.name is not None:
        await pool.execute(
            "UPDATE sentinel.workspaces SET name = $1 WHERE id = $2",
            body.name, uuid.UUID(workspace_id),
        )
    if body.dataset_ids is not None:
        await pool.execute(
            "UPDATE sentinel.workspaces SET dataset_ids = $1 WHERE id = $2",
            json.dumps(body.dataset_ids), uuid.UUID(workspace_id),
        )

    row = await pool.fetchrow("SELECT * FROM sentinel.workspaces WHERE id = $1", uuid.UUID(workspace_id))
    return _row_to_dict(row)


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, session: SessionInfo = Depends(require_user)):
    pool = get_pool()
    count = await pool.fetchval(
        "SELECT count(*) FROM sentinel.workspaces WHERE user_id = $1",
        uuid.UUID(session.user.id),
    )
    if count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete your only workspace")

    result = await pool.execute(
        "DELETE FROM sentinel.workspaces WHERE id = $1 AND user_id = $2",
        uuid.UUID(workspace_id), uuid.UUID(session.user.id),
    )
    if result != "DELETE 1":
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"ok": True}


@router.post("/workspaces/{workspace_id}/activate")
async def activate_workspace(
    workspace_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Switch to a workspace: update session, touch last_accessed, return workspace state."""
    pool = get_pool()
    ws_uuid = uuid.UUID(workspace_id)
    ws = await pool.fetchrow(
        "SELECT * FROM sentinel.workspaces WHERE id = $1 AND user_id = $2",
        ws_uuid, uuid.UUID(session.user.id),
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    await pool.execute("UPDATE sentinel.workspaces SET last_accessed = now() WHERE id = $1", ws_uuid)
    await set_session_workspace(session.session_id, workspace_id)

    # Load tiles
    tile_rows = await pool.fetch(
        "SELECT * FROM sentinel.workspace_tiles WHERE workspace_id = $1 ORDER BY created_at DESC",
        ws_uuid,
    )
    tiles = [
        {
            "id": r["id"], "silo": r["silo"], "column": r["col"],
            "title": r["title"], "summary": r["summary"], "detail": r["detail"] or "",
            "sources": r["sources"] or [], "chartData": (r["chart_data"] or {}).get("points"),
            "chartLabel": (r["chart_data"] or {}).get("label"),
            "metric": r["metric"], "metricSub": r["metric_sub"],
            "suggestedQuestions": r["suggested_questions"],
            "created_at": r["created_at"].timestamp() if r["created_at"] else 0,
        }
        for r in tile_rows
    ]

    # Load interactions
    inter_rows = await pool.fetch(
        "SELECT * FROM sentinel.workspace_interactions WHERE workspace_id = $1", ws_uuid,
    )
    interactions = {
        str(r["tile_id"]): {
            "tile_id": r["tile_id"], "tile_title": r["tile_title"] or "",
            "tile_silo": r["tile_silo"] or "", "tile_summary": r["tile_summary"] or "",
            "thumbs_up": r["thumbs_up"], "thumbs_down": r["thumbs_down"],
            "expanded": r["expanded"], "expand_duration_s": r["expand_duration_s"],
            "followup_questions": r["followup_questions"] or [],
            "interest_score": r["interest_score"],
        }
        for r in inter_rows
    }

    # Load silos
    silo_rows = await pool.fetch(
        "SELECT * FROM sentinel.workspace_silos WHERE workspace_id = $1", ws_uuid,
    )
    silos = [
        {"id": r["silo_id"], "label": r["label"], "color": r["color"],
         "bg": r["bg"], "border": r["border"]}
        for r in silo_rows
    ]

    return {
        "workspace": _row_to_dict(ws),
        "tiles": tiles,
        "interactions": interactions,
        "silos": silos,
    }


@router.post("/workspaces/{workspace_id}/save")
async def save_workspace_state(
    workspace_id: str,
    body: dict,
    session: SessionInfo = Depends(require_user),
):
    """Save current tile/interaction/silo state to a workspace."""
    pool = get_pool()
    ws_uuid = uuid.UUID(workspace_id)
    ws = await pool.fetchrow(
        "SELECT id FROM sentinel.workspaces WHERE id = $1 AND user_id = $2",
        ws_uuid, uuid.UUID(session.user.id),
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Save tiles
    tiles = body.get("tiles", [])
    await pool.execute("DELETE FROM sentinel.workspace_tiles WHERE workspace_id = $1", ws_uuid)
    for tile in tiles:
        chart_data = None
        if tile.get("chartData") or tile.get("chartLabel"):
            chart_data = json.dumps({"points": tile.get("chartData"), "label": tile.get("chartLabel")})
        await pool.execute(
            """INSERT INTO sentinel.workspace_tiles
               (id, workspace_id, silo, col, title, summary, detail, sources, chart_data,
                metric, metric_sub, suggested_questions, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                       to_timestamp($13))""",
            tile.get("id", 0), ws_uuid, tile.get("silo", "alpha"),
            tile.get("column", "row2"), tile.get("title", ""), tile.get("summary", ""),
            tile.get("detail", ""), json.dumps(tile.get("sources", [])),
            chart_data, tile.get("metric"), tile.get("metricSub"),
            json.dumps(tile.get("suggestedQuestions")) if tile.get("suggestedQuestions") else None,
            tile.get("created_at", 0),
        )

    # Save interactions
    interactions = body.get("interactions", {})
    await pool.execute("DELETE FROM sentinel.workspace_interactions WHERE workspace_id = $1", ws_uuid)
    for tile_id_str, inter in interactions.items():
        await pool.execute(
            """INSERT INTO sentinel.workspace_interactions
               (workspace_id, tile_id, tile_title, tile_silo, tile_summary,
                thumbs_up, thumbs_down, expanded, expand_duration_s,
                followup_questions, interest_score)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            ws_uuid, int(tile_id_str),
            inter.get("tile_title", ""), inter.get("tile_silo", ""),
            inter.get("tile_summary", ""),
            inter.get("thumbs_up", 0), inter.get("thumbs_down", 0),
            inter.get("expanded", False), inter.get("expand_duration_s", 0.0),
            json.dumps(inter.get("followup_questions", [])),
            inter.get("interest_score", 0.0),
        )

    # Save silos
    silos = body.get("silos", [])
    await pool.execute("DELETE FROM sentinel.workspace_silos WHERE workspace_id = $1", ws_uuid)
    for silo in silos:
        await pool.execute(
            """INSERT INTO sentinel.workspace_silos
               (workspace_id, silo_id, label, color, bg, border)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            ws_uuid, silo.get("id", ""), silo.get("label", ""),
            silo.get("color"), silo.get("bg"), silo.get("border"),
        )

    return {"ok": True}

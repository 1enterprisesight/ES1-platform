"""Workspace management: create, list, switch, delete, save/load state.

Workspaces are shared resources — any member can access them.
Access is controlled via sentinel.workspace_members.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_user, SessionInfo
from app.database import get_pool
from app.db import load_workspace_datasets, is_workspace_loaded
from app.tiles import get_tile_store, get_interaction_store, Tile, TileInteraction, remove_workspace_stores

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None


def _row_to_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "settings": row["settings"] if row["settings"] else {},
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "last_accessed": row["last_accessed"].isoformat() if row["last_accessed"] else None,
    }


async def _check_membership(workspace_id: str, user_id: str) -> dict:
    """Verify user is a member of the workspace. Returns workspace row or raises 404."""
    pool = get_pool()
    ws = await pool.fetchrow(
        """SELECT w.* FROM sentinel.workspaces w
           JOIN sentinel.workspace_members wm ON wm.workspace_id = w.id
           WHERE w.id = $1 AND wm.user_id = $2""",
        uuid.UUID(workspace_id), uuid.UUID(user_id),
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


async def ensure_default_workspace(user_id: str) -> dict:
    """Create a default workspace for the user if they have none. Returns the workspace."""
    pool = get_pool()
    row = await pool.fetchrow(
        """SELECT w.* FROM sentinel.workspaces w
           JOIN sentinel.workspace_members wm ON wm.workspace_id = w.id
           WHERE wm.user_id = $1
           ORDER BY w.created_at LIMIT 1""",
        uuid.UUID(user_id),
    )
    if row:
        return _row_to_dict(row)

    row = await pool.fetchrow(
        """INSERT INTO sentinel.workspaces (created_by, name)
           VALUES ($1, 'Default')
           RETURNING *""",
        uuid.UUID(user_id),
    )
    # Add creator as owner
    await pool.execute(
        """INSERT INTO sentinel.workspace_members (workspace_id, user_id, role)
           VALUES ($1, $2, 'owner')""",
        row["id"], uuid.UUID(user_id),
    )
    logger.info(f"Created default workspace for user {user_id}")
    return _row_to_dict(row)


async def set_session_workspace(session_id: str, workspace_id: str):
    """Update the session's active workspace."""
    pool = get_pool()
    await pool.execute(
        "UPDATE sentinel.sessions SET workspace_id = $1 WHERE id = $2",
        uuid.UUID(workspace_id), uuid.UUID(session_id),
    )


MAX_DATASETS_PER_WORKSPACE = 3


async def is_workspace_data_ready(workspace_id: str) -> dict:
    """Check if a workspace's data is ready for activation and the agent.

    Returns a status dict the frontend can use to show the correct UI state
    (data setup flow vs dashboard).
    """
    from app.db import get_workspace_tables

    pool = get_pool()
    ws_uuid = uuid.UUID(workspace_id)

    tables = get_workspace_tables(workspace_id)
    table_count = len(tables)

    # Load settings for join_config and data_activated flag
    settings_raw = await pool.fetchval(
        "SELECT settings FROM sentinel.workspaces WHERE id = $1", ws_uuid,
    )
    settings = json.loads(settings_raw) if isinstance(settings_raw, str) else (settings_raw or {})
    join_config = settings.get("join_config", [])
    # Normalize legacy single-link format to list
    if isinstance(join_config, dict):
        join_config = [join_config] if join_config else []
    data_activated = settings.get("data_activated", False)

    if table_count == 0:
        return {
            "ready": False,
            "reason": "no_data",
            "table_count": 0,
            "tables": [],
            "links": [],
            "links_needed": 0,
            "can_activate": False,
            "data_activated": False,
        }

    if table_count == 1:
        return {
            "ready": data_activated,
            "reason": None if data_activated else "not_activated",
            "table_count": 1,
            "tables": tables,
            "links": [],
            "links_needed": 0,
            "can_activate": True,
            "data_activated": data_activated,
        }

    # 2-3 tables — check connectivity through confirmed links
    links_needed = table_count - 1
    confirmed_links = len(join_config)

    # Build adjacency to check all tables are connected
    connected = set()
    if join_config:
        # Start from the first table mentioned in any link
        adj: dict[str, set] = {t: set() for t in tables}
        for link in join_config:
            lt = link.get("left_table", "")
            rt = link.get("right_table", "")
            if lt in adj and rt in adj:
                adj[lt].add(rt)
                adj[rt].add(lt)
        # BFS from first table
        start = next(iter(adj))
        queue = [start]
        connected.add(start)
        while queue:
            node = queue.pop(0)
            for neighbor in adj[node]:
                if neighbor not in connected:
                    connected.add(neighbor)
                    queue.append(neighbor)

    all_connected = connected == set(tables) and confirmed_links >= links_needed
    can_activate = all_connected

    reason = None
    if not can_activate:
        reason = "join_required"
    elif not data_activated:
        reason = "not_activated"

    return {
        "ready": data_activated and can_activate,
        "reason": reason,
        "table_count": table_count,
        "tables": tables,
        "links": join_config,
        "links_needed": max(0, links_needed - confirmed_links),
        "can_activate": can_activate,
        "data_activated": data_activated,
    }


@router.post("/workspaces/{workspace_id}/activate-data")
async def activate_data(
    workspace_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Activate a workspace's data so the agent can run.

    Only succeeds if the data is ready: 1 table, or 2+ tables with all
    links confirmed and all tables connected.
    """
    await _check_membership(workspace_id, session.user.id)

    status = await is_workspace_data_ready(workspace_id)
    if not status["can_activate"]:
        reason = status.get("reason", "unknown")
        if reason == "no_data":
            detail = "No data uploaded. Upload at least one CSV file."
        elif reason == "join_required":
            detail = (f"Tables are not fully linked. "
                      f"{status['links_needed']} more link(s) needed.")
        else:
            detail = "Workspace data is not ready for activation."
        raise HTTPException(status_code=400, detail=detail)

    # Set data_activated flag
    pool = get_pool()
    ws_uuid = uuid.UUID(workspace_id)
    settings_raw = await pool.fetchval(
        "SELECT settings FROM sentinel.workspaces WHERE id = $1", ws_uuid,
    )
    settings = json.loads(settings_raw) if isinstance(settings_raw, str) else (settings_raw or {})
    settings["data_activated"] = True
    await pool.execute(
        "UPDATE sentinel.workspaces SET settings = $1 WHERE id = $2",
        json.dumps(settings), ws_uuid,
    )

    logger.info(f"Workspace {workspace_id} data activated by {session.user.email}")

    # Return updated status
    status = await is_workspace_data_ready(workspace_id)
    return {"ok": True, "data_status": status}


@router.get("/workspaces/{workspace_id}/data-status")
async def get_data_status(
    workspace_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Get the current data readiness status for a workspace."""
    await _check_membership(workspace_id, session.user.id)
    status = await is_workspace_data_ready(workspace_id)
    return status


@router.get("/workspaces")
async def list_workspaces(session: SessionInfo = Depends(require_user)):
    """List all workspaces the user is a member of."""
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT w.* FROM sentinel.workspaces w
           JOIN sentinel.workspace_members wm ON wm.workspace_id = w.id
           WHERE wm.user_id = $1
           ORDER BY w.last_accessed DESC""",
        uuid.UUID(session.user.id),
    )
    if not rows:
        ws = await ensure_default_workspace(session.user.id)
        return {"workspaces": [ws]}
    return {"workspaces": [_row_to_dict(r) for r in rows]}


@router.post("/workspaces")
async def create_workspace(body: CreateWorkspaceRequest, session: SessionInfo = Depends(require_user)):
    pool = get_pool()
    row = await pool.fetchrow(
        """INSERT INTO sentinel.workspaces (created_by, name)
           VALUES ($1, $2) RETURNING *""",
        uuid.UUID(session.user.id), body.name,
    )
    # Add creator as owner
    await pool.execute(
        """INSERT INTO sentinel.workspace_members (workspace_id, user_id, role)
           VALUES ($1, $2, 'owner')""",
        row["id"], uuid.UUID(session.user.id),
    )
    logger.info(f"Workspace '{body.name}' created by {session.user.email}")
    return _row_to_dict(row)


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    body: UpdateWorkspaceRequest,
    session: SessionInfo = Depends(require_user),
):
    await _check_membership(workspace_id, session.user.id)
    pool = get_pool()

    if body.name is not None:
        await pool.execute(
            "UPDATE sentinel.workspaces SET name = $1 WHERE id = $2",
            body.name, uuid.UUID(workspace_id),
        )

    row = await pool.fetchrow("SELECT * FROM sentinel.workspaces WHERE id = $1", uuid.UUID(workspace_id))
    return _row_to_dict(row)


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, session: SessionInfo = Depends(require_user)):
    pool = get_pool()
    # Check ownership
    role = await pool.fetchval(
        """SELECT role FROM sentinel.workspace_members
           WHERE workspace_id = $1 AND user_id = $2""",
        uuid.UUID(workspace_id), uuid.UUID(session.user.id),
    )
    if not role:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can delete a workspace")

    # Check they have at least one other workspace
    count = await pool.fetchval(
        """SELECT count(*) FROM sentinel.workspace_members WHERE user_id = $1""",
        uuid.UUID(session.user.id),
    )
    if count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete your only workspace")

    # Unload from DuckDB and clean up in-memory stores
    from app.db import unload_workspace
    unload_workspace(workspace_id)
    remove_workspace_stores(workspace_id)

    result = await pool.execute(
        "DELETE FROM sentinel.workspaces WHERE id = $1",
        uuid.UUID(workspace_id),
    )
    if result != "DELETE 1":
        raise HTTPException(status_code=404, detail="Workspace not found")
    logger.info(f"Workspace {workspace_id} deleted by {session.user.email}")
    return {"ok": True}


@router.post("/workspaces/{workspace_id}/activate")
async def activate_workspace(
    workspace_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Switch to a workspace: load data into DuckDB, update session, return state."""
    ws = await _check_membership(workspace_id, session.user.id)
    pool = get_pool()
    ws_uuid = uuid.UUID(workspace_id)

    await pool.execute("UPDATE sentinel.workspaces SET last_accessed = now() WHERE id = $1", ws_uuid)
    await set_session_workspace(session.session_id, workspace_id)

    # Load workspace datasets into DuckDB if not already loaded
    if not is_workspace_loaded(workspace_id):
        ds_rows = await pool.fetch(
            "SELECT name, csv_data FROM sentinel.datasets WHERE workspace_id = $1 ORDER BY uploaded_at",
            ws_uuid,
        )
        if ds_rows:
            load_workspace_datasets(workspace_id, [(r["name"], bytes(r["csv_data"])) for r in ds_rows])

    # Load tiles into workspace tile store
    tile_store = get_tile_store(workspace_id)
    tile_rows = await pool.fetch(
        "SELECT * FROM sentinel.workspace_tiles WHERE workspace_id = $1 ORDER BY created_at DESC",
        ws_uuid,
    )
    tiles = [
        Tile(
            id=r["id"], silo=r["silo"], column=r["col"],
            title=r["title"], summary=r["summary"], detail=r["detail"] or "",
            sources=r["sources"] or [],
            chartData=(r["chart_data"] or {}).get("points"),
            chartLabel=(r["chart_data"] or {}).get("label"),
            metric=r["metric"], metricSub=r["metric_sub"],
            suggestedQuestions=r["suggested_questions"],
            created_at=r["created_at"].timestamp() if r["created_at"] else 0,
        )
        for r in tile_rows
    ]
    tile_store.load_tiles(tiles)

    # Load interactions for this user
    interaction_store = get_interaction_store(workspace_id)
    inter_rows = await pool.fetch(
        "SELECT * FROM sentinel.workspace_interactions WHERE workspace_id = $1 AND user_id = $2",
        ws_uuid, uuid.UUID(session.user.id),
    )
    interactions = {}
    for r in inter_rows:
        inter = TileInteraction(
            tile_id=r["tile_id"],
            tile_title=r["tile_title"] or "",
            tile_silo=r["tile_silo"] or "",
            tile_summary=r["tile_summary"] or "",
            thumbs_up=r["thumbs_up"],
            thumbs_down=r["thumbs_down"],
            expanded=r["expanded"],
            expand_duration_s=r["expand_duration_s"],
            followup_questions=r["followup_questions"] or [],
            interest_score=r["interest_score"],
        )
        interactions[r["tile_id"]] = inter
    interaction_store.load_interactions(interactions)

    # Load silos
    silo_rows = await pool.fetch(
        "SELECT * FROM sentinel.workspace_silos WHERE workspace_id = $1", ws_uuid,
    )
    silos = [
        {"id": r["silo_id"], "label": r["label"], "color": r["color"],
         "bg": r["bg"], "border": r["border"]}
        for r in silo_rows
    ]

    # Include data readiness status so frontend knows which view to show
    data_status = await is_workspace_data_ready(workspace_id)

    return {
        "workspace": _row_to_dict(ws),
        "tiles": [t.model_dump() for t in tiles],
        "interactions": {
            str(tid): inter.model_dump() for tid, inter in interactions.items()
        },
        "silos": silos,
        "data_status": data_status,
    }


@router.post("/workspaces/{workspace_id}/save")
async def save_workspace_state(
    workspace_id: str,
    body: dict,
    session: SessionInfo = Depends(require_user),
):
    """Save current tile/interaction/silo state to a workspace."""
    await _check_membership(workspace_id, session.user.id)
    pool = get_pool()
    ws_uuid = uuid.UUID(workspace_id)
    user_uuid = uuid.UUID(session.user.id)

    # Save tiles (shared across users)
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

    # Save interactions (per-user)
    interactions = body.get("interactions", {})
    await pool.execute(
        "DELETE FROM sentinel.workspace_interactions WHERE workspace_id = $1 AND user_id = $2",
        ws_uuid, user_uuid,
    )
    for tile_id_str, inter in interactions.items():
        await pool.execute(
            """INSERT INTO sentinel.workspace_interactions
               (workspace_id, tile_id, user_id, tile_title, tile_silo, tile_summary,
                thumbs_up, thumbs_down, expanded, expand_duration_s,
                followup_questions, interest_score)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
            ws_uuid, int(tile_id_str), user_uuid,
            inter.get("tile_title", ""), inter.get("tile_silo", ""),
            inter.get("tile_summary", ""),
            inter.get("thumbs_up", 0), inter.get("thumbs_down", 0),
            inter.get("expanded", False), inter.get("expand_duration_s", 0.0),
            json.dumps(inter.get("followup_questions", [])),
            inter.get("interest_score", 0.0),
        )

    # Save silos (shared across users)
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

"""Dataset management: upload CSV, list, delete, reload — scoped to workspace."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional

from app.auth import require_user, SessionInfo
from app.database import get_pool
from app.db import load_workspace_datasets, invalidate_profile_cache, get_workspace_tables, get_workspace_table_info, is_workspace_loaded
from app.dataset_profiler import profile_and_store

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def _get_active_workspace_id(session: SessionInfo) -> str:
    """Get the user's active workspace ID from their session."""
    if session.workspace_id:
        return session.workspace_id
    raise HTTPException(status_code=400, detail="No active workspace. Switch to a workspace first.")


async def _reload_workspace_duckdb(workspace_id: str):
    """Reload a workspace's datasets into DuckDB."""
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT name, csv_data FROM sentinel.datasets WHERE workspace_id = $1 ORDER BY uploaded_at",
        uuid.UUID(workspace_id),
    )
    load_workspace_datasets(workspace_id, [(r["name"], bytes(r["csv_data"])) for r in rows])
    invalidate_profile_cache(workspace_id)


@router.get("/datasets")
async def list_datasets(session: SessionInfo = Depends(require_user)):
    """List datasets for the active workspace."""
    workspace_id = await _get_active_workspace_id(session)
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT id, name, filename, row_count, columns, file_size, source_type, uploaded_at, profile
           FROM sentinel.datasets
           WHERE workspace_id = $1
           ORDER BY uploaded_at DESC""",
        uuid.UUID(workspace_id),
    )
    result = {
        "datasets": [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "filename": r["filename"],
                "row_count": r["row_count"],
                "columns": r["columns"],
                "file_size": r["file_size"],
                "source_type": r["source_type"],
                "uploaded_at": r["uploaded_at"].isoformat() if r["uploaded_at"] else None,
                "profile": json.loads(r["profile"]) if isinstance(r["profile"], str) else r["profile"],
            }
            for r in rows
        ]
    }
    # Include join suggestion if 2+ datasets and no confirmed join yet
    if len(rows) >= 2:
        settings_raw = await pool.fetchval(
            "SELECT settings FROM sentinel.workspaces WHERE id = $1",
            uuid.UUID(workspace_id),
        )
        settings = json.loads(settings_raw) if isinstance(settings_raw, str) else (settings_raw or {})
        if not settings.get("join_config"):
            # Ensure DuckDB tables are loaded so _suggest_join can inspect them
            if not is_workspace_loaded(workspace_id):
                await _reload_workspace_duckdb(workspace_id)
            suggestion = await _suggest_join(workspace_id)
            if suggestion:
                result["join_suggestion"] = suggestion
    return result


@router.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(None),
    session: SessionInfo = Depends(require_user),
):
    """Upload a CSV dataset to the active workspace."""
    workspace_id = await _get_active_workspace_id(session)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_FILE_SIZE // 1024 // 1024} MB)")

    # Parse CSV to get metadata
    try:
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        headers = next(reader)
        row_count = sum(1 for _ in reader)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")

    dataset_name = name or file.filename.rsplit(".", 1)[0]

    pool = get_pool()
    row = await pool.fetchrow(
        """INSERT INTO sentinel.datasets (uploaded_by, workspace_id, name, filename, csv_data, row_count, columns, file_size)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
           RETURNING id, uploaded_at""",
        uuid.UUID(session.user.id),
        uuid.UUID(workspace_id),
        dataset_name,
        file.filename,
        content,
        row_count,
        json.dumps(headers),
        len(content),
    )

    logger.info(f"Dataset uploaded: {dataset_name} ({row_count} rows, {len(headers)} cols) "
                f"to workspace {workspace_id} by {session.user.email}")

    # Reload workspace datasets into DuckDB
    await _reload_workspace_duckdb(workspace_id)

    # Generate LLM profile in background
    table_name = re.sub(r'[^a-z0-9]', '_', dataset_name.lower()).strip('_') or "dataset"
    asyncio.create_task(_profile_dataset(table_name, dataset_name, workspace_id))

    # Check for join candidates if this is the 2nd+ dataset
    join_suggestion = await _suggest_join(workspace_id)

    result = {
        "id": str(row["id"]),
        "name": dataset_name,
        "filename": file.filename,
        "row_count": row_count,
        "columns": headers,
        "file_size": len(content),
        "uploaded_at": row["uploaded_at"].isoformat(),
    }
    if join_suggestion:
        result["join_suggestion"] = join_suggestion

    return result


async def _profile_dataset(table_name: str, dataset_name: str, workspace_id: str):
    """Background task: generate and store LLM profile for a dataset."""
    try:
        profile = await profile_and_store(table_name, dataset_name, workspace_id=workspace_id)
        logger.info(f"Profile generated for '{dataset_name}': domain={profile.get('domain')}")
    except Exception as e:
        logger.error(f"Background profiling failed for '{dataset_name}': {e}", exc_info=True)


async def _suggest_join(workspace_id: str) -> Optional[dict]:
    """Analyze workspace tables for join candidates. Returns suggestion or None."""
    tables = get_workspace_tables(workspace_id)
    if len(tables) < 2:
        return None

    table_info = get_workspace_table_info(workspace_id)
    col_sets = {t: {c["name"] for c in table_info.get(t, [])} for t in tables}

    # Find shared column names
    candidates = []
    table_list = list(tables)
    for i in range(len(table_list)):
        for j in range(i + 1, len(table_list)):
            shared = col_sets[table_list[i]] & col_sets[table_list[j]]
            if shared:
                for col_name in sorted(shared):
                    # Get type info for both sides
                    left_type = next(
                        (c["type"] for c in table_info[table_list[i]] if c["name"] == col_name), None
                    )
                    right_type = next(
                        (c["type"] for c in table_info[table_list[j]] if c["name"] == col_name), None
                    )
                    candidates.append({
                        "left_table": table_list[i],
                        "right_table": table_list[j],
                        "column": col_name,
                        "left_type": left_type,
                        "right_type": right_type,
                        "types_match": left_type == right_type,
                    })

    if not candidates:
        return None

    # Return best candidate (prefer matching types)
    candidates.sort(key=lambda c: (not c["types_match"], c["column"]))
    best = candidates[0]
    return {
        "left_table": best["left_table"],
        "right_table": best["right_table"],
        "left_column": best["column"],
        "right_column": best["column"],
        "types_match": best["types_match"],
        "all_candidates": candidates,
    }


class JoinConfigRequest(BaseModel):
    left_table: str
    right_table: str
    left_column: str
    right_column: str


@router.post("/workspaces/{workspace_id}/join-config")
async def save_join_config(
    workspace_id: str,
    body: JoinConfigRequest,
    session: SessionInfo = Depends(require_user),
):
    """Save confirmed join configuration for a workspace."""
    from app.routes.workspaces import _check_membership
    await _check_membership(workspace_id, session.user.id)

    # Validate the join actually works
    from app.db import run_query
    try:
        test_sql = (
            f'SELECT count(*) as matched FROM "{body.left_table}" '
            f'JOIN "{body.right_table}" ON "{body.left_table}"."{body.left_column}" = '
            f'"{body.right_table}"."{body.right_column}" LIMIT 1'
        )
        result = run_query(test_sql, workspace_id=workspace_id)
        matched = result[0]["matched"] if result else 0
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Join validation failed: {e}")

    if matched == 0:
        raise HTTPException(status_code=400, detail="Join produced no matching rows — check your column selection")

    # Store in workspace settings
    pool = get_pool()
    settings_raw = await pool.fetchval(
        "SELECT settings FROM sentinel.workspaces WHERE id = $1",
        uuid.UUID(workspace_id),
    )
    settings = json.loads(settings_raw) if isinstance(settings_raw, str) else (settings_raw or {})
    settings["join_config"] = {
        "left_table": body.left_table,
        "right_table": body.right_table,
        "left_column": body.left_column,
        "right_column": body.right_column,
        "matched_rows": matched,
    }
    await pool.execute(
        "UPDATE sentinel.workspaces SET settings = $1 WHERE id = $2",
        json.dumps(settings), uuid.UUID(workspace_id),
    )

    logger.info(f"Join config saved for workspace {workspace_id}: "
                f"{body.left_table}.{body.left_column} = {body.right_table}.{body.right_column} "
                f"({matched} rows matched)")
    return {"ok": True, "matched_rows": matched}


@router.post("/workspaces/{workspace_id}/validate-join")
async def validate_join(
    workspace_id: str,
    body: JoinConfigRequest,
    session: SessionInfo = Depends(require_user),
):
    """Test a proposed join without saving it."""
    from app.routes.workspaces import _check_membership
    await _check_membership(workspace_id, session.user.id)

    from app.db import run_query
    try:
        # Count matched rows
        match_sql = (
            f'SELECT count(*) as matched FROM "{body.left_table}" '
            f'JOIN "{body.right_table}" ON "{body.left_table}"."{body.left_column}" = '
            f'"{body.right_table}"."{body.right_column}"'
        )
        match_result = run_query(match_sql, workspace_id=workspace_id)
        matched = match_result[0]["matched"] if match_result else 0

        # Count left orphans
        left_sql = (
            f'SELECT count(*) as orphans FROM "{body.left_table}" '
            f'WHERE "{body.left_column}" NOT IN '
            f'(SELECT "{body.right_column}" FROM "{body.right_table}")'
        )
        left_result = run_query(left_sql, workspace_id=workspace_id)
        left_orphans = left_result[0]["orphans"] if left_result else 0

        # Count right orphans
        right_sql = (
            f'SELECT count(*) as orphans FROM "{body.right_table}" '
            f'WHERE "{body.right_column}" NOT IN '
            f'(SELECT "{body.left_column}" FROM "{body.left_table}")'
        )
        right_result = run_query(right_sql, workspace_id=workspace_id)
        right_orphans = right_result[0]["orphans"] if right_result else 0

        # Total rows in each table
        left_total_sql = f'SELECT count(*) as total FROM "{body.left_table}"'
        right_total_sql = f'SELECT count(*) as total FROM "{body.right_table}"'
        left_total = run_query(left_total_sql, workspace_id=workspace_id)[0]["total"]
        right_total = run_query(right_total_sql, workspace_id=workspace_id)[0]["total"]

        return {
            "valid": matched > 0,
            "matched_rows": matched,
            "left_table": body.left_table,
            "left_total": left_total,
            "left_orphans": left_orphans,
            "right_table": body.right_table,
            "right_total": right_total,
            "right_orphans": right_orphans,
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Delete a dataset. Reloads the workspace's DuckDB tables."""
    pool = get_pool()
    # Get workspace_id before deleting
    row = await pool.fetchrow(
        "SELECT workspace_id FROM sentinel.datasets WHERE id = $1",
        uuid.UUID(dataset_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")

    workspace_id = str(row["workspace_id"])

    result = await pool.execute(
        "DELETE FROM sentinel.datasets WHERE id = $1",
        uuid.UUID(dataset_id),
    )
    if result != "DELETE 1":
        raise HTTPException(status_code=404, detail="Dataset not found")

    logger.info(f"Dataset {dataset_id} deleted by {session.user.email}")

    # Reload workspace DuckDB
    await _reload_workspace_duckdb(workspace_id)
    return {"ok": True}


@router.post("/datasets/reload")
async def reload_datasets(session: SessionInfo = Depends(require_user)):
    """Reload active workspace's datasets into DuckDB and re-run silo discovery."""
    workspace_id = await _get_active_workspace_id(session)
    await _reload_workspace_duckdb(workspace_id)

    # Trigger silo rediscovery if we have data
    tables = get_workspace_tables(workspace_id)
    if tables:
        from app.profiler import rediscover_silos
        await rediscover_silos(workspace_id=workspace_id)

    return {"tables": {t: True for t in tables}}


@router.get("/datasets/{dataset_id}/profile")
async def get_dataset_profile(
    dataset_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Get the LLM-generated semantic profile for a dataset."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT name, profile FROM sentinel.datasets WHERE id = $1",
        uuid.UUID(dataset_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = json.loads(row["profile"]) if isinstance(row["profile"], str) else row["profile"]
    return {"name": row["name"], "profile": profile}


@router.post("/datasets/{dataset_id}/profile")
async def regenerate_dataset_profile(
    dataset_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Regenerate the LLM profile for a dataset."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT name, workspace_id FROM sentinel.datasets WHERE id = $1",
        uuid.UUID(dataset_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    name = row["name"]
    workspace_id = str(row["workspace_id"])
    table_name = re.sub(r'[^a-z0-9]', '_', name.lower()).strip('_') or "dataset"
    profile = await profile_and_store(table_name, name, workspace_id=workspace_id)
    return {"name": name, "profile": profile}

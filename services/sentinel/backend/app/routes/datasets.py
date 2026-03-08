"""Dataset management: upload CSV, list, delete, reload into DuckDB."""
from __future__ import annotations

import asyncio
import csv
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.auth import require_user, SessionInfo
from app.database import get_pool
from app.db import load_datasets, get_tables, get_conn, invalidate_profile_cache
from app.dataset_profiler import profile_and_store

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.get("/datasets")
async def list_datasets(session: SessionInfo = Depends(require_user)):
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT id, name, filename, row_count, columns, file_size, source_type, uploaded_at, profile
           FROM sentinel.datasets ORDER BY uploaded_at DESC"""
    )
    return {
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
                "profile": __import__("json").loads(r["profile"]) if isinstance(r["profile"], str) else r["profile"],
            }
            for r in rows
        ]
    }


@router.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(None),
    session: SessionInfo = Depends(require_user),
):
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
        """INSERT INTO sentinel.datasets (user_id, name, filename, csv_data, row_count, columns, file_size)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           RETURNING id, uploaded_at""",
        __import__("uuid").UUID(session.user.id),
        dataset_name,
        file.filename,
        content,
        row_count,
        __import__("json").dumps(headers),
        len(content),
    )

    logger.info(f"Dataset uploaded: {dataset_name} ({row_count} rows, {len(headers)} cols) by {session.user.email}")

    # Reload into DuckDB so profiler can access the data
    all_rows = await pool.fetch(
        "SELECT name, csv_data FROM sentinel.datasets ORDER BY uploaded_at"
    )
    load_datasets([(r["name"], bytes(r["csv_data"])) for r in all_rows])
    invalidate_profile_cache()

    # Generate LLM profile in background (non-blocking)
    import re
    table_name = re.sub(r'[^a-z0-9]', '_', dataset_name.lower()).strip('_') or "dataset"
    asyncio.create_task(_profile_dataset(table_name, dataset_name))

    return {
        "id": str(row["id"]),
        "name": dataset_name,
        "filename": file.filename,
        "row_count": row_count,
        "columns": headers,
        "file_size": len(content),
        "uploaded_at": row["uploaded_at"].isoformat(),
    }


async def _profile_dataset(table_name: str, dataset_name: str):
    """Background task: generate and store LLM profile for a dataset."""
    try:
        profile = await profile_and_store(table_name, dataset_name)
        logger.info(f"Profile generated for '{dataset_name}': domain={profile.get('domain')}")
    except Exception as e:
        logger.error(f"Background profiling failed for '{dataset_name}': {e}", exc_info=True)


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    session: SessionInfo = Depends(require_user),
):
    pool = get_pool()
    result = await pool.execute(
        "DELETE FROM sentinel.datasets WHERE id = $1",
        __import__("uuid").UUID(dataset_id),
    )
    if result != "DELETE 1":
        raise HTTPException(status_code=404, detail="Dataset not found")
    logger.info(f"Dataset {dataset_id} deleted by {session.user.email}")
    return {"ok": True}


@router.post("/datasets/reload")
async def reload_datasets(session: SessionInfo = Depends(require_user)):
    """Reload all datasets from PostgreSQL into DuckDB and re-run silo discovery."""
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT name, csv_data FROM sentinel.datasets ORDER BY uploaded_at"
    )

    counts = load_datasets([(r["name"], bytes(r["csv_data"])) for r in rows])
    invalidate_profile_cache()

    # Trigger silo rediscovery if we have data
    if any(v > 0 for v in counts.values()):
        from app.profiler import rediscover_silos
        await rediscover_silos()

    logger.info(f"Datasets reloaded into DuckDB: {counts}")
    return {"tables": counts}


@router.get("/datasets/{dataset_id}/profile")
async def get_dataset_profile(
    dataset_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Get the LLM-generated semantic profile for a dataset."""
    import json as _json
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT name, profile FROM sentinel.datasets WHERE id = $1",
        __import__("uuid").UUID(dataset_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = _json.loads(row["profile"]) if isinstance(row["profile"], str) else row["profile"]
    return {"name": row["name"], "profile": profile}


@router.post("/datasets/{dataset_id}/profile")
async def regenerate_dataset_profile(
    dataset_id: str,
    session: SessionInfo = Depends(require_user),
):
    """Regenerate the LLM profile for a dataset."""
    import re
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT name FROM sentinel.datasets WHERE id = $1",
        __import__("uuid").UUID(dataset_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    name = row["name"]
    table_name = re.sub(r'[^a-z0-9]', '_', name.lower()).strip('_') or "dataset"
    profile = await profile_and_store(table_name, name)
    return {"name": name, "profile": profile}

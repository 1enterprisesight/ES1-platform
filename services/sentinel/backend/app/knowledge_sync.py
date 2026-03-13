"""Sentinel knowledge sync — periodically syncs PG data into RAG documents.

Reads workspaces, datasets, tiles, and aggregated interactions from the
sentinel schema and upserts them as documents in the rag.documents table
so the platform Knowledge / RAG pipeline can surface Sentinel data.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from app.database import get_pool

logger = logging.getLogger(__name__)

SYNC_INTERVAL = int(os.environ.get("KNOWLEDGE_SYNC_INTERVAL", "300"))
INITIAL_DELAY = 30
TILE_BATCH_SIZE = 100
KB_NAME = "sentinel-data"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Content builders
# ------------------------------------------------------------------

def _workspace_content(row) -> str:
    settings = row["settings"] or {}
    return (
        f"Workspace: {row['name']}\n"
        f"Created: {row['created_at']}\n"
        f"Status: {row.get('status', 'unknown')}\n"
        f"Members: {row.get('member_count', 0)}\n"
        f"Datasets: {row.get('dataset_count', 0)}\n"
        f"Settings: {json.dumps(settings, default=str)}\n"
    )


def _dataset_content(row) -> str:
    return (
        f"Dataset: {row['name']}\n"
        f"Filename: {row.get('filename', row['name'])}\n"
        f"Rows: {row.get('row_count', 'unknown')}\n"
        f"Columns: {json.dumps(row.get('columns', []), default=str)}\n"
        f"Size: {row.get('file_size', 'unknown')} bytes\n"
        f"Source type: {row.get('source_type', 'csv')}\n"
        f"Workspace: {row.get('workspace_id')}\n"
    )


def _tile_content(row) -> str:
    sources = row.get("sources") or []
    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except (json.JSONDecodeError, TypeError):
            pass
    suggested = row.get("suggested_questions") or []
    if isinstance(suggested, str):
        try:
            suggested = json.loads(suggested)
        except (json.JSONDecodeError, TypeError):
            pass
    return (
        f"Insight: {row['title']}\n"
        f"Silo: {row.get('silo', '')}\n"
        f"Summary: {row.get('summary', '')}\n"
        f"Detail: {row.get('detail', '')}\n"
        f"Metric: {row.get('metric', '')} {row.get('metric_sub', '')}\n"
        f"Sources: {json.dumps(sources, default=str)}\n"
        f"Suggested questions: {json.dumps(suggested, default=str)}\n"
    )


def _engagement_content(workspace_name: str, stats: dict) -> str:
    return (
        f"Engagement: {workspace_name}\n"
        f"Total interactions: {stats.get('total', 0)}\n"
        f"Likes: {stats.get('likes', 0)}\n"
        f"Dislikes: {stats.get('dislikes', 0)}\n"
        f"Questions asked: {stats.get('questions', 0)}\n"
        f"Top tiles: {json.dumps(stats.get('top_tiles', []), default=str)}\n"
    )


# ------------------------------------------------------------------
# Upsert / cleanup helpers
# ------------------------------------------------------------------

async def _upsert_doc(
    conn,
    kb_id: str,
    sentinel_type: str,
    sentinel_id: str,
    title: str,
    content: str,
    extra_meta: dict | None = None,
):
    """Insert or update a RAG document by sentinel_type + sentinel_id."""
    content_hash = _sha256(content)
    meta = {
        "sentinel_type": sentinel_type,
        "sentinel_id": str(sentinel_id),
        "synced_at": _now_iso(),
    }
    if extra_meta:
        meta.update(extra_meta)

    # Check existing
    existing = await conn.fetchrow(
        """SELECT id, content_hash FROM rag.documents
           WHERE knowledge_base_id = $1
             AND metadata->>'sentinel_type' = $2
             AND metadata->>'sentinel_id' = $3""",
        kb_id, sentinel_type, str(sentinel_id),
    )

    if existing:
        if existing["content_hash"] == content_hash:
            return  # no change
        await conn.execute(
            """UPDATE rag.documents
               SET content = $1, content_hash = $2, title = $3,
                   metadata = $4, updated_at = NOW()
               WHERE id = $5""",
            content, content_hash, title,
            json.dumps(meta), existing["id"],
        )
    else:
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        await conn.execute(
            """INSERT INTO rag.documents
                   (id, knowledge_base_id, title, content, content_hash,
                    content_type, metadata)
               VALUES ($1, $2, $3, $4, $5, 'text/plain', $6)""",
            doc_id, kb_id, title, content, content_hash,
            json.dumps(meta),
        )
        await conn.execute(
            """INSERT INTO rag.chunks
                   (id, document_id, chunk_index, content, content_hash, metadata)
               VALUES ($1, $2, 0, $3, $4, '{}')""",
            chunk_id, doc_id, content, content_hash,
        )


async def _cleanup_deleted(conn, kb_id: str, sentinel_type: str, live_ids: set[str]):
    """Remove RAG documents whose sentinel_id no longer exists in source."""
    rows = await conn.fetch(
        """SELECT id, metadata->>'sentinel_id' AS sid FROM rag.documents
           WHERE knowledge_base_id = $1
             AND metadata->>'sentinel_type' = $2""",
        kb_id, sentinel_type,
    )
    for row in rows:
        if row["sid"] not in live_ids:
            await conn.execute("DELETE FROM rag.documents WHERE id = $1", row["id"])


# ------------------------------------------------------------------
# Main sync cycle
# ------------------------------------------------------------------

async def _run_sync():
    """Single sync pass — reads Sentinel tables, upserts RAG documents."""
    pool = get_pool()
    async with pool.acquire() as conn:
        # Graceful check: does the RAG schema exist?
        rag_exists = await conn.fetchval(
            """SELECT EXISTS (
                   SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'rag' AND table_name = 'knowledge_bases'
               )"""
        )
        if not rag_exists:
            logger.debug("RAG schema not present — skipping knowledge sync")
            return

        # Find the sentinel-data KB
        kb_id = await conn.fetchval(
            "SELECT id FROM rag.knowledge_bases WHERE name = $1", KB_NAME,
        )
        if kb_id is None:
            logger.debug(f"Knowledge base '{KB_NAME}' not found — skipping sync")
            return

        # --- Workspaces ---
        workspaces = await conn.fetch(
            """SELECT w.id, w.name, w.created_at, w.status, w.settings,
                      (SELECT count(*) FROM sentinel.workspace_members wm WHERE wm.workspace_id = w.id) AS member_count,
                      (SELECT count(*) FROM sentinel.datasets d WHERE d.workspace_id = w.id) AS dataset_count
               FROM sentinel.workspaces w"""
        )
        ws_ids = set()
        for ws in workspaces:
            ws_ids.add(str(ws["id"]))
            await _upsert_doc(
                conn, kb_id, "workspace", str(ws["id"]),
                f"Workspace: {ws['name']}", _workspace_content(ws),
                {"workspace_id": str(ws["id"])},
            )
        await _cleanup_deleted(conn, kb_id, "workspace", ws_ids)

        # --- Datasets ---
        datasets = await conn.fetch(
            """SELECT id, workspace_id, name, filename, row_count,
                      columns, file_size, source_type
               FROM sentinel.datasets"""
        )
        ds_ids = set()
        for ds in datasets:
            ds_ids.add(str(ds["id"]))
            columns = ds["columns"]
            if isinstance(columns, str):
                try:
                    columns = json.loads(columns)
                except (json.JSONDecodeError, TypeError):
                    pass
            ds_dict = dict(ds)
            ds_dict["columns"] = columns
            await _upsert_doc(
                conn, kb_id, "dataset", str(ds["id"]),
                f"Dataset: {ds['name']}", _dataset_content(ds_dict),
                {"workspace_id": str(ds["workspace_id"])},
            )
        await _cleanup_deleted(conn, kb_id, "dataset", ds_ids)

        # --- Tiles (batched) ---
        tile_count = await conn.fetchval("SELECT count(*) FROM sentinel.workspace_tiles")
        tile_ids = set()
        for offset in range(0, tile_count, TILE_BATCH_SIZE):
            tiles = await conn.fetch(
                """SELECT id, workspace_id, title, silo, summary, detail,
                          metric, metric_sub, sources, suggested_questions
                   FROM sentinel.workspace_tiles
                   ORDER BY id
                   LIMIT $1 OFFSET $2""",
                TILE_BATCH_SIZE, offset,
            )
            for tile in tiles:
                tile_ids.add(str(tile["id"]))
                await _upsert_doc(
                    conn, kb_id, "tile", str(tile["id"]),
                    f"Insight: {tile['title']}", _tile_content(dict(tile)),
                    {"workspace_id": str(tile["workspace_id"]),
                     "silo": tile.get("silo", "")},
                )
        await _cleanup_deleted(conn, kb_id, "tile", tile_ids)

        # --- Engagement (aggregated per workspace) ---
        engagement_rows = await conn.fetch(
            """SELECT w.id AS workspace_id, w.name AS workspace_name,
                      count(wi.tile_id) AS total,
                      coalesce(sum(wi.thumbs_up), 0) AS likes,
                      coalesce(sum(wi.thumbs_down), 0) AS dislikes,
                      coalesce(sum(jsonb_array_length(wi.followup_questions)), 0) AS questions
               FROM sentinel.workspaces w
               LEFT JOIN sentinel.workspace_interactions wi ON wi.workspace_id = w.id
               GROUP BY w.id, w.name"""
        )
        eng_ids = set()
        for eng in engagement_rows:
            eng_id = str(eng["workspace_id"])
            eng_ids.add(eng_id)
            # Top tiles by interaction count
            top_tiles = await conn.fetch(
                """SELECT t.title,
                          (wi.thumbs_up + wi.thumbs_down +
                           jsonb_array_length(wi.followup_questions)) AS cnt
                   FROM sentinel.workspace_interactions wi
                   JOIN sentinel.workspace_tiles t ON t.id = wi.tile_id
                   WHERE wi.workspace_id = $1
                   ORDER BY cnt DESC
                   LIMIT 5""",
                eng["workspace_id"],
            )
            stats = {
                "total": eng["total"],
                "likes": eng["likes"],
                "dislikes": eng["dislikes"],
                "questions": eng["questions"],
                "top_tiles": [{"title": r["title"], "count": r["cnt"]} for r in top_tiles],
            }
            await _upsert_doc(
                conn, kb_id, "engagement", eng_id,
                f"Engagement: {eng['workspace_name']}",
                _engagement_content(eng["workspace_name"], stats),
                {"workspace_id": eng_id},
            )
        await _cleanup_deleted(conn, kb_id, "engagement", eng_ids)

    logger.info("Knowledge sync completed")


# ------------------------------------------------------------------
# Background loop
# ------------------------------------------------------------------

async def run_knowledge_sync_loop():
    """Run the knowledge sync on a periodic interval."""
    logger.info(f"Knowledge sync starting (initial delay {INITIAL_DELAY}s, interval {SYNC_INTERVAL}s)")
    await asyncio.sleep(INITIAL_DELAY)

    while True:
        try:
            await _run_sync()
        except asyncio.CancelledError:
            logger.info("Knowledge sync cancelled")
            return
        except Exception as e:
            logger.error(f"Knowledge sync error: {e}", exc_info=True)

        await asyncio.sleep(SYNC_INTERVAL)

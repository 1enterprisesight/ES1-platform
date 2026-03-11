"""Data source listing — scoped to the active workspace."""
import json
import logging

from fastapi import APIRouter, Depends
from app.auth import require_user, SessionInfo
from app.database import get_pool
from app.db import get_conn, get_workspace_table_info, get_workspace_tables

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/datasources")
async def list_datasources(session: SessionInfo = Depends(require_user)):
    """List data sources for the active workspace with join info."""
    workspace_id = session.workspace_id
    if not workspace_id:
        return {"sources": [], "join": None}

    try:
        conn = get_conn()
        tables = get_workspace_tables(workspace_id)
        table_info = get_workspace_table_info(workspace_id)
    except RuntimeError:
        return {"sources": [], "join": None}

    from app.db import _prefixed_name

    sources = []
    for table in tables:
        full_name = _prefixed_name(workspace_id, table)
        try:
            row_count = conn.execute(f'SELECT count(*) FROM "{full_name}"').fetchone()[0]
        except Exception:
            row_count = 0
        cols = table_info.get(table, [])
        sources.append({
            "table": table,
            "file": table,
            "label": table.replace("_", " ").title(),
            "description": f"{len(cols)} columns, {row_count:,} rows",
            "rows": row_count,
            "columns": len(cols),
            "active": True,
        })

    # Use stored join config if available, otherwise auto-detect
    join_info = None

    pool = get_pool()
    import uuid
    ws_settings = await pool.fetchval(
        "SELECT settings FROM sentinel.workspaces WHERE id = $1",
        uuid.UUID(workspace_id),
    )
    if ws_settings and isinstance(ws_settings, dict):
        jc = ws_settings.get("join_config")
        if jc:
            join_info = {
                "description": f"Linked on {jc['left_column']}",
                "left": jc["left_table"],
                "right": jc["right_table"],
                "key": jc["left_column"],
                "confirmed": True,
            }

    # Auto-detect if no confirmed join
    if not join_info and len(tables) >= 2:
        col_sets = {t: {c["name"] for c in table_info.get(t, [])} for t in tables}
        table_list = list(tables)
        for i in range(len(table_list)):
            for j in range(i + 1, len(table_list)):
                shared = col_sets[table_list[i]] & col_sets[table_list[j]]
                if shared:
                    join_info = {
                        "description": f"Suggested link on {', '.join(sorted(shared))}",
                        "left": table_list[i],
                        "right": table_list[j],
                        "key": next(iter(shared)),
                        "confirmed": False,
                    }
                    break
            if join_info:
                break

    return {"sources": sources, "join": join_info}

import logging
from fastapi import APIRouter
from app.db import get_conn, get_table_info
from app.config import FEATURE_USAGE_CSV, PERFORMANCE_CSV

logger = logging.getLogger(__name__)
router = APIRouter()

_SOURCE_META = {
    "feature_usage": {
        "file": FEATURE_USAGE_CSV.name,
        "label": "Feature Usage",
        "description": "iTero order lifecycle, product usage, and treatment workflow data",
    },
    "performance": {
        "file": PERFORMANCE_CSV.name,
        "label": "Performance",
        "description": "Doctor performance metrics, segmentation, and channel data",
    },
}


@router.get("/datasources")
def list_datasources():
    try:
        conn = get_conn()
        table_info = get_table_info()
    except RuntimeError:
        return {"sources": [], "join": None}

    sources = []
    for table, meta in _SOURCE_META.items():
        row_count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        cols = table_info.get(table, [])
        sources.append({
            "table": table,
            "file": meta["file"],
            "label": meta["label"],
            "description": meta["description"],
            "rows": row_count,
            "columns": len(cols),
            "active": True,
        })

    return {
        "sources": sources,
        "join": {
            "description": "Linked on Doctor ID",
            "left": "feature_usage",
            "right": "performance",
            "key": "Doctor ID",
        },
    }

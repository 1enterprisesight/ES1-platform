import logging
from fastapi import APIRouter
from app.db import get_conn, get_table_info, get_tables

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/datasources")
def list_datasources():
    try:
        conn = get_conn()
        tables = get_tables()
        table_info = get_table_info()
    except RuntimeError:
        return {"sources": [], "join": None}

    sources = []
    for table in tables:
        row_count = conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
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

    # Auto-detect join keys: columns with the same name across tables
    join_info = None
    if len(tables) >= 2:
        col_sets = {t: {c["name"] for c in table_info.get(t, [])} for t in tables}
        table_list = list(tables)
        for i in range(len(table_list)):
            for j in range(i + 1, len(table_list)):
                shared = col_sets[table_list[i]] & col_sets[table_list[j]]
                if shared:
                    join_info = {
                        "description": f"Linked on {', '.join(sorted(shared))}",
                        "left": table_list[i],
                        "right": table_list[j],
                        "key": next(iter(shared)),
                    }
                    break
            if join_info:
                break

    return {"sources": sources, "join": join_info}

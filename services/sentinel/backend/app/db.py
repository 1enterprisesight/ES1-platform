"""DuckDB management with workspace-scoped table namespacing.

Tables are prefixed as  ws_{workspace_short_id}_{sanitized_name}  so that
multiple workspaces can coexist in a single in-memory DuckDB instance.
All public helpers accept a *workspace_id* to scope operations.
"""
from __future__ import annotations

import os
import re
import tempfile
import threading
from typing import Optional

import duckdb
import logging

logger = logging.getLogger(__name__)

_conn: duckdb.DuckDBPyConnection | None = None
_lock = threading.Lock()

_DDL_PATTERN = re.compile(
    r'\b(DROP|CREATE|ALTER|DELETE|INSERT|UPDATE|COPY)\b', re.IGNORECASE
)

# Pattern to strip quoted identifiers and string literals before DDL check
_QUOTED_PATTERN = re.compile(r'"[^"]*"|\'[^\']*\'')

# Per-workspace data profile cache
_profile_cache: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_ddl(sql: str) -> bool:
    """Check for DDL/DML keywords, ignoring content inside quotes."""
    stripped = _QUOTED_PATTERN.sub('', sql)
    return bool(_DDL_PATTERN.search(stripped))


def _sanitize_table_name(name: str) -> str:
    """Derive a safe table suffix from a dataset name."""
    t = re.sub(r'[^a-z0-9]', '_', name.lower()).strip('_')
    return t or "dataset"


def _ws_prefix(workspace_id: str) -> str:
    """Short, stable prefix for a workspace's tables.

    Uses the first 12 hex chars of the UUID (enough to avoid collisions).
    """
    return f"ws_{workspace_id.replace('-', '')[:12]}"


def _prefixed_name(workspace_id: str, table_name: str) -> str:
    return f"{_ws_prefix(workspace_id)}_{table_name}"


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

def get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        raise RuntimeError("DuckDB not initialized — call init_db() first")
    return _conn


def init_db() -> None:
    """Initialize an empty DuckDB in-memory instance.

    Workspace data is loaded lazily via load_workspace_datasets().
    """
    global _conn
    _conn = duckdb.connect(":memory:")
    logger.info("DuckDB initialized (empty — workspaces load on activate)")


# ---------------------------------------------------------------------------
# Workspace dataset loading
# ---------------------------------------------------------------------------

def load_workspace_datasets(
    workspace_id: str,
    datasets: list[tuple[str, bytes]],
) -> dict[str, int]:
    """Load datasets for a workspace into DuckDB, replacing any existing tables
    for that workspace.

    Args:
        workspace_id: UUID string of the workspace.
        datasets: list of (dataset_name, csv_bytes).

    Returns:
        dict of display_table_name -> row_count.
    """
    conn = get_conn()
    prefix = _ws_prefix(workspace_id)
    counts: dict[str, int] = {}

    with _lock:
        # Drop existing tables for this workspace
        for table in [r[0] for r in conn.execute("SHOW TABLES").fetchall()]:
            if table.startswith(prefix + "_"):
                conn.execute(f'DROP TABLE IF EXISTS "{table}"')

        for name, csv_bytes in datasets:
            display = _sanitize_table_name(name)
            full_name = _prefixed_name(workspace_id, display)

            fd, tmp_path = tempfile.mkstemp(suffix=".csv")
            try:
                os.write(fd, csv_bytes)
                os.close(fd)
                conn.execute(f"""
                    CREATE TABLE "{full_name}" AS
                    SELECT * FROM read_csv_auto('{tmp_path}', header=true, ignore_errors=true)
                """)
                counts[display] = conn.execute(
                    f'SELECT count(*) FROM "{full_name}"'
                ).fetchone()[0]
            except Exception as e:
                logger.error(f"Failed to load dataset '{name}' for workspace {workspace_id}: {e}")
                counts[display] = 0
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # Invalidate profile cache for this workspace
    _profile_cache.pop(workspace_id, None)

    logger.info(f"Workspace {workspace_id} datasets loaded: {counts}")
    return counts


def unload_workspace(workspace_id: str) -> None:
    """Drop all DuckDB tables belonging to a workspace."""
    conn = get_conn()
    prefix = _ws_prefix(workspace_id)
    with _lock:
        for table in [r[0] for r in conn.execute("SHOW TABLES").fetchall()]:
            if table.startswith(prefix + "_"):
                conn.execute(f'DROP TABLE IF EXISTS "{table}"')
    _profile_cache.pop(workspace_id, None)
    logger.info(f"Workspace {workspace_id} tables unloaded")


def is_workspace_loaded(workspace_id: str) -> bool:
    """Check whether a workspace has any tables in DuckDB."""
    conn = get_conn()
    prefix = _ws_prefix(workspace_id)
    with _lock:
        for table in [r[0] for r in conn.execute("SHOW TABLES").fetchall()]:
            if table.startswith(prefix + "_"):
                return True
    return False


# ---------------------------------------------------------------------------
# Workspace-scoped queries
# ---------------------------------------------------------------------------

def get_workspace_tables(workspace_id: str) -> list[str]:
    """Return display table names (without prefix) for a workspace."""
    conn = get_conn()
    prefix = _ws_prefix(workspace_id) + "_"
    with _lock:
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    return [t[len(prefix):] for t in tables if t.startswith(prefix)]


def get_workspace_table_info(workspace_id: str) -> dict[str, list[dict]]:
    """Return column metadata for a workspace's tables.

    Keys are display names (no prefix). Values are lists of {name, type}.
    """
    conn = get_conn()
    prefix = _ws_prefix(workspace_id) + "_"
    info: dict[str, list[dict]] = {}
    with _lock:
        for table in [r[0] for r in conn.execute("SHOW TABLES").fetchall()]:
            if table.startswith(prefix):
                display = table[len(prefix):]
                cols = conn.execute(f'DESCRIBE "{table}"').fetchall()
                info[display] = [{"name": c[0], "type": c[1]} for c in cols]
    return info


def run_query(sql: str, workspace_id: Optional[str] = None) -> list[dict]:
    """Execute a read-only SQL query and return results as list of dicts.

    When workspace_id is provided, table references in the SQL should use
    display names (without prefix). This function rewrites them to the
    prefixed form before execution.
    """
    if _has_ddl(sql):
        raise ValueError(f"DDL/DML statements are not allowed: {sql[:80]}")

    if workspace_id:
        sql = _rewrite_table_refs(sql, workspace_id)

    conn = get_conn()
    with _lock:
        try:
            result = conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Query failed: {e}\nSQL: {sql}")
            raise


def _rewrite_table_refs(sql: str, workspace_id: str) -> str:
    """Replace display table names with workspace-prefixed names in SQL.

    Handles both quoted ("table_name") and unquoted references.
    """
    tables = get_workspace_tables(workspace_id)
    # Sort by length descending to avoid partial replacements
    for table in sorted(tables, key=len, reverse=True):
        full = _prefixed_name(workspace_id, table)
        # Replace quoted references: "table_name" -> "ws_xxx_table_name"
        sql = sql.replace(f'"{table}"', f'"{full}"')
        # Replace unquoted word-boundary references
        sql = re.sub(
            rf'\b{re.escape(table)}\b',
            f'"{full}"',
            sql,
        )
    return sql


# ---------------------------------------------------------------------------
# Data profile (workspace-scoped)
# ---------------------------------------------------------------------------

def invalidate_profile_cache(workspace_id: Optional[str] = None):
    """Clear cached data profile. If workspace_id given, clear only that one."""
    if workspace_id:
        _profile_cache.pop(workspace_id, None)
    else:
        _profile_cache.clear()


def get_data_profile(workspace_id: str) -> str:
    """Build a rich text profile of a workspace's tables.

    Includes row counts, columns, types, distinct values, top value
    distributions, and sample rows. Cached per workspace.
    """
    cached = _profile_cache.get(workspace_id)
    if cached is not None:
        return cached

    conn = get_conn()
    prefix = _ws_prefix(workspace_id) + "_"
    lines: list[str] = []

    with _lock:
        all_tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        ws_tables = [t for t in all_tables if t.startswith(prefix)]

        if not ws_tables:
            result = "No data loaded. Upload CSV datasets to begin analysis."
            _profile_cache[workspace_id] = result
            return result

        for full_name in ws_tables:
            display = full_name[len(prefix):]
            count = conn.execute(f'SELECT count(*) FROM "{full_name}"').fetchone()[0]
            lines.append(f"\n## {display} ({count:,} rows)")

            cols = conn.execute(f'DESCRIBE "{full_name}"').fetchall()
            for col_name, col_type, *_ in cols:
                try:
                    distinct = conn.execute(
                        f'SELECT count(DISTINCT "{col_name}") FROM "{full_name}"'
                    ).fetchone()[0]
                    nulls = conn.execute(
                        f'SELECT count(*) FROM "{full_name}" WHERE "{col_name}" IS NULL'
                    ).fetchone()[0]
                    top = conn.execute(
                        f'SELECT "{col_name}", count(*) as n FROM "{full_name}" '
                        f'WHERE "{col_name}" IS NOT NULL '
                        f'GROUP BY "{col_name}" ORDER BY n DESC LIMIT 8'
                    ).fetchall()
                    top_str = ", ".join(f"{r[0]} ({r[1]:,})" for r in top)
                    lines.append(
                        f'  "{col_name}" ({col_type}) — {distinct:,} distinct, '
                        f'{nulls:,} nulls — top: [{top_str}]'
                    )
                except Exception:
                    lines.append(f'  "{col_name}" ({col_type})')

            # Sample rows
            sample = conn.execute(f'SELECT * FROM "{full_name}" LIMIT 3').fetchall()
            col_names = [c[0] for c in cols]
            lines.append("  Sample rows:")
            for row in sample:
                row_str = ", ".join(f'{col_names[i]}={row[i]}' for i in range(len(col_names)))
                lines.append(f"    {row_str}")

    # Join key hint
    if len(ws_tables) > 1:
        lines.append("\n## Join hint")
        lines.append("  Look for common column names across tables to identify join keys.")

    result = "\n".join(lines)
    _profile_cache[workspace_id] = result
    logger.info(f"Data profile built for workspace {workspace_id}: {len(result)} chars")
    return result


# ---------------------------------------------------------------------------
# Legacy helpers (for backward compat during migration — will be removed)
# ---------------------------------------------------------------------------

def get_tables() -> list[str]:
    """Return all table names (all workspaces). DEPRECATED — use get_workspace_tables()."""
    conn = get_conn()
    with _lock:
        return [r[0] for r in conn.execute("SHOW TABLES").fetchall()]


def get_table_info() -> dict[str, list[dict]]:
    """Return column metadata for all tables. DEPRECATED — use get_workspace_table_info()."""
    conn = get_conn()
    info = {}
    with _lock:
        for table in [r[0] for r in conn.execute("SHOW TABLES").fetchall()]:
            cols = conn.execute(f'DESCRIBE "{table}"').fetchall()
            info[table] = [{"name": c[0], "type": c[1]} for c in cols]
    return info

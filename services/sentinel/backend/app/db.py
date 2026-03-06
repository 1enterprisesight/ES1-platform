from __future__ import annotations

import re
import threading
import duckdb
import logging
from app.config import FEATURE_USAGE_CSV, PERFORMANCE_CSV

logger = logging.getLogger(__name__)

_conn: duckdb.DuckDBPyConnection | None = None
_lock = threading.Lock()

_DDL_PATTERN = re.compile(
    r'\b(DROP|CREATE|ALTER|DELETE|INSERT|UPDATE|COPY)\b', re.IGNORECASE
)

# Pattern to strip quoted identifiers and string literals before DDL check
_QUOTED_PATTERN = re.compile(r'"[^"]*"|\'[^\']*\'')


def _has_ddl(sql: str) -> bool:
    """Check for DDL/DML keywords, ignoring content inside quotes."""
    stripped = _QUOTED_PATTERN.sub('', sql)
    return bool(_DDL_PATTERN.search(stripped))


def get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        raise RuntimeError("DuckDB not initialized — call init_db() first")
    return _conn


def init_db() -> dict[str, int]:
    """Initialize DuckDB in-memory and load CSVs if available. Returns row counts."""
    global _conn
    _conn = duckdb.connect(":memory:")

    counts = {}
    for table, csv_path in [("feature_usage", FEATURE_USAGE_CSV), ("performance", PERFORMANCE_CSV)]:
        if csv_path.exists():
            _conn.execute(f"""
                CREATE TABLE {table} AS
                SELECT * FROM read_csv_auto('{csv_path}', header=true, ignore_errors=true)
            """)
            counts[table] = _conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        else:
            logger.warning(f"CSV not found: {csv_path} — skipping {table}")
            counts[table] = 0

    logger.info(f"DuckDB loaded: {counts}")
    return counts


def load_datasets(datasets: list[tuple[str, bytes]]) -> dict[str, int]:
    """Load datasets (name, csv_bytes) into DuckDB, replacing existing tables.

    Returns dict of table_name -> row_count.
    """
    import io
    import tempfile
    import os

    conn = get_conn()
    counts = {}

    with _lock:
        # Drop all existing tables first
        for table in [r[0] for r in conn.execute("SHOW TABLES").fetchall()]:
            conn.execute(f'DROP TABLE IF EXISTS "{table}"')

        for name, csv_bytes in datasets:
            # Sanitize table name: lowercase, replace non-alnum with underscore
            table_name = re.sub(r'[^a-z0-9]', '_', name.lower()).strip('_')
            if not table_name:
                table_name = "dataset"

            # Write to temp file for DuckDB to read
            fd, tmp_path = tempfile.mkstemp(suffix=".csv")
            try:
                os.write(fd, csv_bytes)
                os.close(fd)
                conn.execute(f"""
                    CREATE TABLE "{table_name}" AS
                    SELECT * FROM read_csv_auto('{tmp_path}', header=true, ignore_errors=true)
                """)
                counts[table_name] = conn.execute(f'SELECT count(*) FROM "{table_name}"').fetchone()[0]
            except Exception as e:
                logger.error(f"Failed to load dataset '{name}' into DuckDB: {e}")
                counts[table_name] = 0
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    logger.info(f"Datasets loaded into DuckDB: {counts}")
    return counts


def invalidate_profile_cache():
    """Clear the cached data profile so it gets rebuilt on next request."""
    global _data_profile_cache
    _data_profile_cache = None


def run_query(sql: str) -> list[dict]:
    """Execute a SQL query and return results as list of dicts."""
    if _has_ddl(sql):
        raise ValueError(f"DDL/DML statements are not allowed: {sql[:80]}")
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


def get_tables() -> list[str]:
    """Return list of loaded tables."""
    conn = get_conn()
    with _lock:
        rows = conn.execute("SHOW TABLES").fetchall()
    return [r[0] for r in rows]


def get_table_info() -> dict[str, list[dict]]:
    """Return column metadata for all loaded tables."""
    conn = get_conn()
    info = {}
    with _lock:
        for table in get_tables():
            cols = conn.execute(f"DESCRIBE {table}").fetchall()
            info[table] = [{"name": c[0], "type": c[1]} for c in cols]
    return info


_data_profile_cache: str | None = None


def get_data_profile() -> str:
    """Build a rich text profile of both tables: row counts, columns, types,
    distinct values, top value distributions, sample rows. Cached after first call."""
    global _data_profile_cache
    if _data_profile_cache is not None:
        return _data_profile_cache

    conn = get_conn()
    lines = []
    tables = get_tables()
    if not tables:
        _data_profile_cache = "No data loaded. Upload CSV datasets to begin analysis."
        return _data_profile_cache

    with _lock:
        for table in tables:
            count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            lines.append(f"\n## {table} ({count:,} rows)")

            cols = conn.execute(f"DESCRIBE {table}").fetchall()
            for col_name, col_type, *_ in cols:
                try:
                    distinct = conn.execute(
                        f'SELECT count(DISTINCT "{col_name}") FROM {table}'
                    ).fetchone()[0]
                    nulls = conn.execute(
                        f'SELECT count(*) FROM {table} WHERE "{col_name}" IS NULL'
                    ).fetchone()[0]
                    top = conn.execute(
                        f'SELECT "{col_name}", count(*) as n FROM {table} '
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
            sample = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
            col_names = [c[0] for c in cols]
            lines.append(f"  Sample rows:")
            for row in sample:
                row_str = ", ".join(f'{col_names[i]}={row[i]}' for i in range(len(col_names)))
                lines.append(f"    {row_str}")

    # Join key hint
    lines.append("\n## Join hint")
    lines.append('  Tables can be joined on: feature_usage."Doctor ID" = performance."Doctor ID"')

    _data_profile_cache = "\n".join(lines)
    logger.info(f"Data profile built: {len(_data_profile_cache)} chars")
    return _data_profile_cache

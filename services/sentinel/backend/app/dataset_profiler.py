"""Generate and store LLM-powered semantic profiles for datasets.

A profile captures *what* the data is about — domain, entities, column semantics,
relationships, and suggested analysis angles — so that downstream prompts have
rich context without re-profiling on every request.
"""
from __future__ import annotations

import json
import logging
from app.db import get_conn, get_workspace_table_info, _prefixed_name

logger = logging.getLogger(__name__)


def build_statistical_summary(table_name: str, workspace_id: str = "") -> str:
    """Build a statistical summary of a single DuckDB table for the LLM."""
    conn = get_conn()

    if workspace_id:
        info = get_workspace_table_info(workspace_id)
        full_table = _prefixed_name(workspace_id, table_name)
    else:
        # Fallback to querying all tables
        from app.db import get_table_info
        info = get_table_info()
        full_table = table_name

    cols = info.get(table_name, [])
    if not cols:
        return f"Table '{table_name}' not found in DuckDB."

    row_count = conn.execute(f'SELECT count(*) FROM "{full_table}"').fetchone()[0]
    lines = [f"Table: {table_name} ({row_count:,} rows)", ""]

    for col in cols:
        name = col["name"]
        dtype = col["type"]
        try:
            distinct = conn.execute(f'SELECT count(DISTINCT "{name}") FROM "{full_table}"').fetchone()[0]
            nulls = conn.execute(f'SELECT count(*) FROM "{full_table}" WHERE "{name}" IS NULL').fetchone()[0]
            top = conn.execute(
                f'SELECT "{name}", count(*) as n FROM "{full_table}" '
                f'WHERE "{name}" IS NOT NULL '
                f'GROUP BY "{name}" ORDER BY n DESC LIMIT 8'
            ).fetchall()
            top_str = ", ".join(f"{r[0]} ({r[1]:,})" for r in top)

            # Add numeric stats for numeric columns
            stats_str = ""
            if "INT" in dtype.upper() or "FLOAT" in dtype.upper() or "DOUBLE" in dtype.upper() or "DECIMAL" in dtype.upper() or "NUMERIC" in dtype.upper():
                try:
                    stats = conn.execute(
                        f'SELECT MIN("{name}"), MAX("{name}"), AVG("{name}")::DECIMAL(18,2) '
                        f'FROM "{full_table}" WHERE "{name}" IS NOT NULL'
                    ).fetchone()
                    if stats[0] is not None:
                        stats_str = f" | range=[{stats[0]}, {stats[1]}], avg={stats[2]}"
                except Exception:
                    pass

            lines.append(
                f'  "{name}" ({dtype}) — {distinct:,} distinct, {nulls:,} nulls{stats_str}'
                f'\n    top values: [{top_str}]'
            )
        except Exception:
            lines.append(f'  "{name}" ({dtype})')

    # Sample rows
    sample = conn.execute(f'SELECT * FROM "{full_table}" LIMIT 3').fetchall()
    col_names = [c["name"] for c in cols]
    lines.append("\nSample rows:")
    for row in sample:
        row_str = ", ".join(f'{col_names[i]}={row[i]}' for i in range(len(col_names)))
        lines.append(f"  {row_str}")

    return "\n".join(lines)


async def generate_dataset_profile(table_name: str, workspace_id: str = "") -> dict:
    """Use the LLM to generate a semantic profile of a dataset.

    Returns a dict with:
        domain: str — business domain (e.g. "banking", "healthcare", "retail")
        description: str — 2-3 sentence description of what this dataset represents
        entity: str — what each row represents (e.g. "a bank customer", "a sales order")
        column_profiles: list[dict] — semantic description of each column
        relationships: list[str] — notable relationships between columns
        analysis_angles: list[str] — suggested analytical questions / dimensions
        key_metrics: list[str] — important numeric columns for KPIs
        categorical_dimensions: list[str] — good columns for grouping/filtering
    """
    from app.llm import generate_json

    summary = build_statistical_summary(table_name, workspace_id=workspace_id)

    prompt = f"""Analyze this dataset and produce a semantic profile. Your goal is to understand
what this data represents, what domain it belongs to, and what makes it analytically interesting.

{summary}

Return a JSON object with:
- "domain": the business domain (e.g. "banking", "healthcare", "retail", "logistics")
- "description": 2-3 sentence description of what this dataset contains and its purpose
- "entity": what each row represents (e.g. "a bank customer", "a product order")
- "column_profiles": array of objects, one per column, each with:
    - "name": exact column name
    - "semantic_type": what this column represents (e.g. "customer_id", "geographic_region", "monetary_amount", "binary_flag", "categorical_label", "date", "count", "percentage", "name")
    - "description": one sentence describing this column in business context
    - "analytical_role": one of "dimension" (grouping/filtering), "measure" (aggregation/KPI), "identifier" (unique key), "metadata" (descriptive, not for analysis)
- "relationships": array of strings describing notable relationships between columns (e.g. "Revenue and Margin are correlated financial metrics")
- "analysis_angles": array of 5-8 high-value analytical questions this data could answer
- "key_metrics": array of column names that serve as important KPIs or measures
- "categorical_dimensions": array of column names good for grouping, filtering, or silo creation

Return ONLY the JSON object."""

    try:
        profile = await generate_json(prompt, temperature=0.3)
        logger.info(f"Generated profile for '{table_name}': domain={profile.get('domain')}, "
                     f"{len(profile.get('column_profiles', []))} columns profiled")
        return profile
    except Exception as e:
        logger.error(f"Failed to generate profile for '{table_name}': {e}")
        return {"domain": "unknown", "description": f"Dataset '{table_name}' (profile generation failed)", "entity": "record"}


async def profile_and_store(table_name: str, dataset_name: str, workspace_id: str = "") -> dict:
    """Generate a profile and store it in PostgreSQL."""
    from app.database import get_pool

    profile = await generate_dataset_profile(table_name, workspace_id=workspace_id)

    pool = get_pool()
    await pool.execute(
        "UPDATE sentinel.datasets SET profile = $1 WHERE name = $2",
        json.dumps(profile),
        dataset_name,
    )
    logger.info(f"Stored profile for dataset '{dataset_name}'")
    return profile


async def get_stored_profiles() -> dict[str, dict]:
    """Load all dataset profiles from PostgreSQL. Returns {dataset_name: profile}."""
    from app.database import get_pool

    pool = get_pool()
    rows = await pool.fetch(
        "SELECT name, profile FROM sentinel.datasets WHERE profile IS NOT NULL"
    )
    return {r["name"]: json.loads(r["profile"]) if isinstance(r["profile"], str) else r["profile"] for r in rows}


def format_profiles_for_prompt(profiles: dict[str, dict]) -> str:
    """Format stored profiles into a prompt-friendly context block."""
    if not profiles:
        return ""

    sections = []
    for name, profile in profiles.items():
        lines = [f"### Dataset: {name}"]
        lines.append(f"Domain: {profile.get('domain', 'unknown')}")
        lines.append(f"Description: {profile.get('description', 'N/A')}")
        lines.append(f"Entity: Each row is {profile.get('entity', 'a record')}")

        # Key metrics and dimensions
        metrics = profile.get("key_metrics", [])
        dims = profile.get("categorical_dimensions", [])
        if metrics:
            lines.append(f"Key metrics: {', '.join(metrics)}")
        if dims:
            lines.append(f"Dimensions: {', '.join(dims)}")

        # Column semantics (compact)
        col_profiles = profile.get("column_profiles", [])
        if col_profiles:
            lines.append("Columns:")
            for cp in col_profiles:
                role = cp.get("analytical_role", "")
                lines.append(f'  - "{cp["name"]}": {cp.get("description", "")} [{role}]')

        # Relationships
        rels = profile.get("relationships", [])
        if rels:
            lines.append("Relationships:")
            for r in rels:
                lines.append(f"  - {r}")

        sections.append("\n".join(lines))

    return "\n\n".join(sections)

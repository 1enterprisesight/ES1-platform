"""Silo discovery — workspace-scoped.

Each workspace has its own set of silos. Discovery runs against
the workspace's DuckDB tables.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from app.db import get_conn, get_workspace_table_info, _prefixed_name
from app.llm import generate_json
from app.config import SILO_PALETTE, ALPHA_SILO

logger = logging.getLogger(__name__)

# Per-workspace silo cache: {workspace_id: [silos]}
_workspace_silos: dict[str, list[dict]] = {}

# Per-workspace discovery status
_workspace_discovery_done: dict[str, bool] = {}


def get_silos(workspace_id: str = "") -> list[dict]:
    """Get silos for a workspace. Returns empty list if no workspace given."""
    if not workspace_id:
        return [ALPHA_SILO]
    return _workspace_silos.get(workspace_id, [ALPHA_SILO])


def set_silos(workspace_id: str, silos: list[dict]):
    """Set silos for a workspace (used when loading from DB)."""
    _workspace_silos[workspace_id] = silos


def is_discovery_done(workspace_id: str = "") -> bool:
    if not workspace_id:
        return True
    return _workspace_discovery_done.get(workspace_id, False)


# Legacy compat
silo_discovery_done = True


def get_hints(workspace_id: str = "") -> Optional[list]:
    """Get silo hints for a workspace (from workspace settings)."""
    # Hints are now stored in workspace settings, not on disk
    return None


async def rediscover_silos(workspace_id: str = "", hints: Optional[list] = None):
    """Force re-discovery for a workspace."""
    if not workspace_id:
        return
    _workspace_silos[workspace_id] = []
    await discover_silos(workspace_id, hints)


async def discover_silos(workspace_id: str = "", hints: Optional[list] = None):
    """Profile columns and ask LLM to pick the best categorical dimensions as silos."""
    if not workspace_id:
        return

    # If we already have cached silos (more than just alpha), reuse
    existing = _workspace_silos.get(workspace_id, [])
    if len(existing) > 1:
        logger.info(f"Reusing {len(existing)} cached silos for workspace {workspace_id}")
        _workspace_discovery_done[workspace_id] = True
        return

    conn = get_conn()
    table_info = get_workspace_table_info(workspace_id)

    if not table_info:
        logger.warning(f"No tables for workspace {workspace_id} — skipping silo discovery")
        _workspace_silos[workspace_id] = [ALPHA_SILO]
        _workspace_discovery_done[workspace_id] = True
        return

    # Build column profiles
    profiles = {}
    for table, cols in table_info.items():
        full_name = _prefixed_name(workspace_id, table)
        profiles[table] = []
        for col in cols:
            name = col["name"]
            dtype = col["type"]
            try:
                card = conn.execute(f'SELECT count(DISTINCT "{name}") FROM "{full_name}"').fetchone()[0]
                sample = conn.execute(
                    f'SELECT "{name}", count(*) as cnt FROM "{full_name}" '
                    f'GROUP BY "{name}" ORDER BY cnt DESC LIMIT 8'
                ).fetchall()
                top_values = [{"value": str(r[0]), "count": r[1]} for r in sample if r[0] is not None]
                profiles[table].append({
                    "column": name,
                    "type": dtype,
                    "cardinality": card,
                    "top_values": top_values,
                })
            except Exception:
                profiles[table].append({"column": name, "type": dtype, "cardinality": None, "top_values": []})

    # Build hints guidance
    hints_block = ""
    if hints:
        hints_list = ", ".join(f'"{h}"' for h in hints)
        hints_block = f"""
IMPORTANT: The user wants the dashboard organized around these themes: {hints_list}
Map each theme to the most relevant column(s) in the data. Use the theme names as silo IDs/labels.
If a theme doesn't map cleanly to a single column, pick the closest match or derive it from the data.
You MUST include all requested themes. You may add 1-2 additional data-driven silos if they are clearly valuable.
"""

    table_sections = []
    for table, cols in profiles.items():
        table_sections.append(f"## {table} table\n{_format_profiles(cols)}")
    tables_text = "\n\n".join(table_sections)

    # Include stored semantic profiles if available
    semantic_block = ""
    try:
        from app.dataset_profiler import get_stored_profiles, format_profiles_for_prompt
        stored = await get_stored_profiles()
        if stored:
            semantic_block = f"""
Dataset context (LLM-generated semantic understanding):
{format_profiles_for_prompt(stored)}
"""
    except Exception:
        pass

    prompt = f"""You are analyzing datasets to find the best categorical dimensions for a data dashboard.

Here are column profiles for each table:

{tables_text}
{semantic_block}{hints_block}
Pick 4-6 columns that would make the best "silo" filters for a dashboard. Good silos are:
- Categorical with 3-20 distinct values (not too many, not too few)
- Meaningful business dimensions (Region, Product type, Channel, etc.)
- Useful for grouping and comparing data

Return JSON array of objects with:
- "id": short lowercase slug (e.g. "region", "product", "channel")
- "label": human-readable label (e.g. "Region", "Product")
- "source_column": exact column name from the data
- "source_table": which table it comes from

Return ONLY the JSON array, no other text."""

    try:
        result = await generate_json(prompt, temperature=0.3)
        if not isinstance(result, list):
            result = result.get("silos", result.get("dimensions", []))

        discovered = []
        for i, silo in enumerate(result[:6]):
            palette = SILO_PALETTE[i % len(SILO_PALETTE)]
            discovered.append({
                "id": silo["id"],
                "label": silo["label"],
                "source_column": silo.get("source_column", ""),
                "source_table": silo.get("source_table", ""),
                **palette,
            })

        _workspace_silos[workspace_id] = [ALPHA_SILO] + discovered
        logger.info(f"Discovered {len(discovered)} silos for workspace {workspace_id}: "
                     f"{[s['label'] for s in discovered]}")

    except Exception as e:
        logger.error(f"Silo discovery failed for workspace {workspace_id}, using fallback: {e}")
        fallback = []
        first_table = next(iter(profiles), None)
        if first_table:
            candidates = sorted(
                [p for p in profiles[first_table] if p["cardinality"] and 2 <= p["cardinality"] <= 30],
                key=lambda p: p["cardinality"],
            )
            for i, p in enumerate(candidates[:4]):
                slug = re.sub(r'[^a-z0-9]', '_', p["column"].lower()).strip('_')
                fallback.append({
                    "id": slug,
                    "label": p["column"],
                    "source_column": p["column"],
                    "source_table": first_table,
                    **SILO_PALETTE[i % len(SILO_PALETTE)],
                })
        _workspace_silos[workspace_id] = [ALPHA_SILO] + fallback

    _workspace_discovery_done[workspace_id] = True


def _format_profiles(profiles: list[dict]) -> str:
    lines = []
    for p in profiles:
        top = ", ".join(f'"{v["value"]}" ({v["count"]})' for v in p["top_values"][:5])
        lines.append(f"- {p['column']} ({p['type']}): cardinality={p['cardinality']}, top=[{top}]")
    return "\n".join(lines)

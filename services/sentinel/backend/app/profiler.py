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
    """Analyze data and ask LLM to identify analytical themes as silos.

    Silos are high-level analytical themes (e.g. "Revenue Performance",
    "Customer Risk", "Operational Efficiency") — NOT column names.
    The agent uses these themes to guide its question generation.
    """
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

    # Build column profiles for context
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
You MUST include all requested themes. You may add 1-2 additional data-driven themes if clearly valuable.
"""

    table_sections = []
    for table, cols in profiles.items():
        table_sections.append(f"## {table} table\n{_format_profiles(cols)}")
    tables_text = "\n\n".join(table_sections)

    # Include stored semantic profiles if available
    semantic_block = ""
    try:
        from app.dataset_profiler import get_stored_profiles, format_profiles_for_prompt
        stored = await get_stored_profiles(workspace_id=workspace_id)
        if stored:
            semantic_block = f"""
Dataset context (LLM-generated semantic understanding):
{format_profiles_for_prompt(stored)}
"""
    except Exception:
        pass

    prompt = f"""You are analyzing datasets to identify the most interesting analytical themes for an AI-powered data dashboard.

Here are column profiles for each table:

{tables_text}
{semantic_block}{hints_block}
Identify 4-6 analytical THEMES that an AI analyst should investigate in this data.
Each theme is a high-level area of inquiry — NOT a column name.

Good themes are:
- SHORT labels: 1-2 words max (e.g. "Revenue", "Churn", "Risk", "Growth", "Operations")
- Business-relevant analytical dimensions
- Areas where interesting patterns, anomalies, or trends are likely to exist
- Broad enough to generate multiple questions, but specific enough to be meaningful

BAD themes are:
- Verbose labels (e.g. "Financial Transaction Analysis", "Customer Segmentation & Profiling") — TOO LONG
- Raw column names (e.g. "Region", "Product Name") — these are NOT themes
- Generic labels (e.g. "Data Analysis", "Statistics") — too vague

Return a JSON array of objects with:
- "id": short lowercase slug (e.g. "revenue", "churn", "risk")
- "label": SHORT human-readable name, 1-2 words (e.g. "Revenue", "Churn", "Risk")
- "description": 1-2 sentence description of what this theme covers and what kinds of questions to ask about it

Return ONLY the JSON array, no other text."""

    # Langfuse trace for silo discovery
    from app.llm import get_langfuse
    lf = get_langfuse()
    trace = None
    if lf:
        try:
            trace = lf.trace(
                name=f"Silo Discovery",
                session_id=f"workspace-{workspace_id}",
                metadata={"workspace_id": workspace_id},
                tags=["silo-discovery"],
            )
        except Exception:
            pass

    try:
        result = await generate_json(prompt, temperature=0.4, parent=trace, generation_name="discover-silos")
        if not isinstance(result, list):
            result = result.get("silos", result.get("themes", result.get("dimensions", [])))

        discovered = []
        for i, silo in enumerate(result[:6]):
            palette = SILO_PALETTE[i % len(SILO_PALETTE)]
            label = silo["label"]
            # Enforce short labels — take first 2 words if too long
            if len(label) > 20:
                label = " ".join(label.split()[:2])
            discovered.append({
                "id": silo["id"],
                "label": label,
                "description": silo.get("description", ""),
                **palette,
            })

        _workspace_silos[workspace_id] = [ALPHA_SILO] + discovered
        logger.info(f"Discovered {len(discovered)} thematic silos for workspace {workspace_id}: "
                     f"{[s['label'] for s in discovered]}")
        if trace:
            try:
                trace.update(output=[s["label"] for s in discovered], metadata={
                    "silo_count": len(discovered),
                })
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Silo discovery failed for workspace {workspace_id}, using table-based fallback: {e}")
        # Fallback: one silo per table so the agent has something to work with
        fallback = []
        for i, table in enumerate(profiles.keys()):
            fallback.append({
                "id": re.sub(r'[^a-z0-9]', '_', table.lower()).strip('_'),
                "label": table,
                "description": f"Analytical themes derived from the {table} dataset.",
                **SILO_PALETTE[i % len(SILO_PALETTE)],
            })
        _workspace_silos[workspace_id] = [ALPHA_SILO] + fallback


def _format_profiles(profiles: list[dict]) -> str:
    lines = []
    for p in profiles:
        top = ", ".join(f'"{v["value"]}" ({v["count"]})' for v in p["top_values"][:5])
        lines.append(f"- {p['column']} ({p['type']}): cardinality={p['cardinality']}, top=[{top}]")
    return "\n".join(lines)

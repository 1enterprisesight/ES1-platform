from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
from app.db import get_conn, get_table_info
from app.llm import generate_json
from app.config import SILO_PALETTE, ALPHA_SILO, SILO_HINTS

logger = logging.getLogger(__name__)

_SILOS_FILE = Path(__file__).resolve().parent.parent / ".silos_cache.json"
_HINTS_FILE = Path(__file__).resolve().parent.parent / ".silo_hints.json"
_silos: list[dict] = []
_hints: Optional[list] = None


def _atomic_write(path: Path, data_str: str):
    """Write data atomically: write to tempfile then os.replace()."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data_str)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _load_hints() -> Optional[list]:
    """Load user-defined silo hints from disk, falling back to config."""
    try:
        if _HINTS_FILE.exists():
            data = json.loads(_HINTS_FILE.read_text())
            if isinstance(data, list) and len(data) > 0:
                return data
    except Exception:
        pass
    return SILO_HINTS


def _save_hints(hints: Optional[list]):
    global _hints
    _hints = hints
    try:
        if hints:
            _atomic_write(_HINTS_FILE, json.dumps(hints))
        elif _HINTS_FILE.exists():
            _HINTS_FILE.unlink()
    except Exception as e:
        logger.warning(f"Failed to save hints: {e}")


def _load_silos_from_disk():
    global _silos
    try:
        if _SILOS_FILE.exists():
            data = json.loads(_SILOS_FILE.read_text())
            if isinstance(data, list) and len(data) > 0:
                _silos = data
                logger.info(f"Loaded {len(_silos)} silos from disk cache")
                return True
    except Exception as e:
        logger.warning(f"Failed to load silos cache: {e}")
    return False


def _save_silos_to_disk():
    try:
        _atomic_write(_SILOS_FILE, json.dumps(_silos, default=str))
    except Exception as e:
        logger.warning(f"Failed to save silos cache: {e}")


# Load cached silos and hints immediately
_load_silos_from_disk()
_hints = _load_hints()


def get_silos() -> list[dict]:
    return _silos


def get_hints() -> Optional[list]:
    return _hints or _load_hints()


# Track whether silo discovery has completed at least once
silo_discovery_done = False


async def rediscover_silos(hints: Optional[list] = None):
    """Force re-discovery with optional new hints. Clears the silo cache."""
    global _silos
    _save_hints(hints)
    _silos = []  # Clear cache so discover_silos actually runs
    if _SILOS_FILE.exists():
        _SILOS_FILE.unlink()
    await discover_silos()


async def discover_silos():
    """Profile columns and ask Gemini to pick the best categorical dimensions as silos."""
    global _silos, silo_discovery_done

    # If we have a valid silo cache with non-alpha silos, reuse it.
    # This keeps silo IDs stable across restarts and avoids orphaning tiles.
    if len(_silos) > 1:
        logger.info(f"Reusing {len(_silos)} cached silos (skipping LLM discovery)")
        await _remap_orphaned_tiles()
        silo_discovery_done = True
        return

    conn = get_conn()
    table_info = get_table_info()

    # Build column profiles
    profiles = {}
    for table, cols in table_info.items():
        profiles[table] = []
        for col in cols:
            name = col["name"]
            dtype = col["type"]
            try:
                card = conn.execute(f'SELECT count(DISTINCT "{name}") FROM {table}').fetchone()[0]
                sample = conn.execute(
                    f'SELECT "{name}", count(*) as cnt FROM {table} '
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

    # Build hints guidance if user provided themes
    active_hints = _hints or _load_hints()
    hints_block = ""
    if active_hints:
        hints_list = ", ".join(f'"{h}"' for h in active_hints)
        hints_block = f"""
IMPORTANT: The user wants the dashboard organized around these themes: {hints_list}
Map each theme to the most relevant column(s) in the data. Use the theme names as silo IDs/labels.
If a theme doesn't map cleanly to a single column, pick the closest match or derive it from the data.
You MUST include all requested themes. You may add 1-2 additional data-driven silos if they are clearly valuable.
"""

    prompt = f"""You are analyzing two Invisalign dental datasets to find the best categorical dimensions for a data dashboard.

Here are column profiles for each table:

## feature_usage table
{_format_profiles(profiles['feature_usage'])}

## performance table
{_format_profiles(profiles['performance'])}
{hints_block}
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

        _silos = [ALPHA_SILO] + discovered
        _save_silos_to_disk()
        await _remap_orphaned_tiles()
        logger.info(f"Discovered {len(discovered)} silos: {[s['label'] for s in discovered]}")

    except Exception as e:
        logger.error(f"Silo discovery failed, using defaults: {e}")
        _silos = [
            ALPHA_SILO,
            {"id": "region", "label": "Region", "source_column": "Region", "source_table": "feature_usage", **SILO_PALETTE[0]},
            {"id": "product", "label": "Product", "source_column": "Product Name", "source_table": "feature_usage", **SILO_PALETTE[1]},
            {"id": "channel", "label": "Channel", "source_column": "Channel", "source_table": "performance", **SILO_PALETTE[2]},
            {"id": "segment", "label": "Segment", "source_column": "Cur. Segment", "source_table": "performance", **SILO_PALETTE[3]},
        ]
        _save_silos_to_disk()
        await _remap_orphaned_tiles()

    silo_discovery_done = True


async def _remap_orphaned_tiles():
    """Reassign tiles whose silo ID doesn't match any current silo.

    Uses the LLM to classify each orphaned tile into the best-matching
    current silo based on the tile's title and summary content.
    Falls back to round-robin if the LLM call fails.
    """
    from app.tiles import tile_store

    known_ids = {s["id"] for s in _silos}
    non_alpha = [s for s in _silos if s["id"] != "alpha"]
    if not non_alpha:
        return

    orphans = [(i, t) for i, t in enumerate(tile_store._tiles) if t.silo not in known_ids]
    if not orphans:
        return

    logger.info(f"Found {len(orphans)} orphaned tiles to remap")

    # Build the classification prompt
    silo_descriptions = "\n".join(
        f'- "{s["id"]}": {s["label"]} (source: {s.get("source_column", "n/a")} from {s.get("source_table", "n/a")})'
        for s in non_alpha
    )

    tile_entries = []
    for idx, (_, tile) in enumerate(orphans):
        tile_entries.append(f'{idx}: "{tile.title}" — {tile.summary[:120]}')
    tiles_text = "\n".join(tile_entries)

    prompt = f"""Classify each tile into the single best-matching silo based on its content.

Available silos:
{silo_descriptions}

Tiles to classify:
{tiles_text}

Return a JSON array of objects, one per tile, in order:
[{{"index": 0, "silo": "<silo_id>"}}, ...]

Use ONLY the silo IDs listed above. Pick the most relevant silo for each tile's subject matter.
Return ONLY the JSON array."""

    try:
        result = await generate_json(prompt, temperature=0.1)
        if not isinstance(result, list):
            raise ValueError(f"Expected list, got {type(result)}")

        # Build lookup: index -> silo_id
        valid_ids = {s["id"] for s in non_alpha}
        assignments = {}
        for entry in result:
            idx = entry.get("index")
            silo_id = entry.get("silo")
            if isinstance(idx, int) and silo_id in valid_ids and 0 <= idx < len(orphans):
                assignments[idx] = silo_id

        remapped = 0
        for idx, (_, tile) in enumerate(orphans):
            new_id = assignments.get(idx)
            if new_id:
                old = tile.silo
                tile.silo = new_id
                remapped += 1
                logger.debug(f"LLM remapped tile '{tile.title[:40]}': {old} -> {new_id}")
            else:
                # Fallback for any tile the LLM missed
                tile.silo = non_alpha[idx % len(non_alpha)]["id"]
                remapped += 1

        if remapped > 0:
            tile_store._save_to_disk()
            logger.info(f"LLM-remapped {remapped} orphaned tiles to current silos")

    except Exception as e:
        logger.warning(f"LLM remap failed, falling back to round-robin: {e}")
        remapped = 0
        for idx, (_, tile) in enumerate(orphans):
            tile.silo = non_alpha[idx % len(non_alpha)]["id"]
            remapped += 1
        if remapped > 0:
            tile_store._save_to_disk()
            logger.info(f"Round-robin remapped {remapped} orphaned tiles")


def _format_profiles(profiles: list[dict]) -> str:
    lines = []
    for p in profiles:
        top = ", ".join(f'"{v["value"]}" ({v["count"]})' for v in p["top_values"][:5])
        lines.append(f"- {p['column']} ({p['type']}): cardinality={p['cardinality']}, top=[{top}]")
    return "\n".join(lines)

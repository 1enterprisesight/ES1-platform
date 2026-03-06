from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from app.config import DEFAULT_ROW_CONFIG

logger = logging.getLogger(__name__)

_ROW_CONFIG_FILE = Path(__file__).resolve().parent.parent / ".row_config.json"
_rows: List[dict] = []


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


def _load_from_disk():
    global _rows
    try:
        if _ROW_CONFIG_FILE.exists():
            data = json.loads(_ROW_CONFIG_FILE.read_text())
            if isinstance(data, list) and len(data) == 2:
                _rows = data
                logger.info(f"Loaded row config from disk: {[r['label'] for r in _rows]}")
                return
    except Exception as e:
        logger.warning(f"Failed to load row config: {e}")
    _rows = [dict(r) for r in DEFAULT_ROW_CONFIG]


def _save_to_disk():
    try:
        _atomic_write(_ROW_CONFIG_FILE, json.dumps(_rows, indent=2))
    except Exception as e:
        logger.warning(f"Failed to save row config: {e}")


# Load on import
_load_from_disk()


def get_row_config() -> List[dict]:
    return _rows


def update_row_config(rows: List[dict]):
    global _rows
    # Enforce exactly 2 rows, preserve id structure
    if len(rows) != 2:
        raise ValueError("Exactly 2 rows required")
    for i, row in enumerate(rows):
        _rows[i]["label"] = row.get("label", _rows[i]["label"])
        _rows[i]["description"] = row.get("description", _rows[i]["description"])
        if "icon" in row:
            _rows[i]["icon"] = row["icon"]
        if "bright" in row:
            _rows[i]["bright"] = row["bright"]
    _save_to_disk()


def get_row_prompt_context() -> str:
    """Build text for LLM prompts describing what goes in each row."""
    lines = []
    for r in _rows:
        lines.append(f'- "{r["id"]}": {r["label"]} — {r["description"]}')
    return "\n".join(lines)

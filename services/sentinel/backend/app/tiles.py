import asyncio
import itertools
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Persistence file — lives outside app/ so uvicorn --reload doesn't trigger on writes
_TILES_FILE = Path(__file__).resolve().parent.parent / ".tiles_cache.json"

# Atomic counter for tile IDs — seeded from current time, increments monotonically
_id_counter = itertools.count(int(time.time() * 1000))


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


class BarData(BaseModel):
    label: str
    value: float
    max: float


class BarChart(BaseModel):
    title: str
    bars: List[BarData]


class Tile(BaseModel):
    id: int = Field(default_factory=lambda: next(_id_counter))
    silo: str
    column: str  # "action" | "watching" | "informational" | "resolved"
    age: str = "just now"
    title: str
    summary: str
    detail: str
    sources: List[str] = []
    chart: Optional[str] = None  # sparkline pattern name (fallback)
    chartData: Optional[List[float]] = None  # actual data points for sparkline
    chartLabel: Optional[str] = None
    metric: Optional[str] = None
    metricSub: Optional[str] = None
    barCharts: Optional[List[BarChart]] = None
    suggestedQuestions: Optional[List[str]] = None
    created_at: float = Field(default_factory=time.time)


class TileStore:
    """In-memory tile store with file-based persistence and SSE broadcast."""

    def __init__(self):
        self._tiles: List[Tile] = []
        self._subscribers: List[asyncio.Queue] = []
        self._lock: Optional[asyncio.Lock] = None
        self._load_from_disk()

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _load_from_disk(self):
        """Load tiles from disk cache on startup."""
        try:
            if _TILES_FILE.exists():
                data = json.loads(_TILES_FILE.read_text())
                self._tiles = [Tile(**t) for t in data]
                logger.info(f"Loaded {len(self._tiles)} tiles from disk cache")
        except Exception as e:
            logger.warning(f"Failed to load tiles cache: {e}")
            self._tiles = []

    def _save_to_disk(self):
        """Persist tiles to disk atomically."""
        try:
            data = [t.model_dump() for t in self._tiles]
            _atomic_write(_TILES_FILE, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Failed to save tiles cache: {e}")

    @property
    def tiles(self) -> List[Tile]:
        return list(self._tiles)

    async def add_tile(self, tile: Tile):
        async with self._get_lock():
            self._tiles.insert(0, tile)
            from app.config import MAX_TILES
            if len(self._tiles) > MAX_TILES:
                # Protect tiles that have user interactions from eviction
                protected_ids = set()
                try:
                    for inter in interaction_store.get_all():
                        if abs(inter.interest_score) >= 0.5:
                            protected_ids.add(inter.tile_id)
                except Exception:
                    pass
                # Split into protected and unprotected
                protected = [t for t in self._tiles if t.id in protected_ids]
                unprotected = [t for t in self._tiles if t.id not in protected_ids]
                # Trim unprotected tiles to make room, keeping newest first
                max_unprotected = MAX_TILES - len(protected)
                if max_unprotected > 0:
                    self._tiles = protected + unprotected[:max_unprotected]
                else:
                    # More protected than MAX_TILES — keep all protected, trim oldest
                    self._tiles = protected[:MAX_TILES]
                # Sort back: newest first
                self._tiles.sort(key=lambda t: t.created_at, reverse=True)
            self._save_to_disk()
        # Broadcast to all subscribers
        event = {"type": "new_tile", "tile": tile.model_dump()}
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def remove_tile(self, tile_id: int) -> bool:
        async with self._get_lock():
            before = len(self._tiles)
            self._tiles = [t for t in self._tiles if t.id != tile_id]
            if len(self._tiles) < before:
                self._save_to_disk()
                return True
        return False

    async def move_tile(self, tile_id: int, new_column: str) -> Optional[Tile]:
        async with self._get_lock():
            for t in self._tiles:
                if t.id == tile_id:
                    t.column = new_column
                    self._save_to_disk()
                    return t
        return None

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    def has_subscribers(self) -> bool:
        return len(self._subscribers) > 0

    def broadcast_status(self, status: str, **extra):
        event = {"type": status, **extra}
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


tile_store = TileStore()


def recover_interacted_tiles():
    """Recreate tiles from interaction metadata for any that were evicted."""
    existing_ids = {t.id for t in tile_store._tiles}
    recovered = 0
    for inter in interaction_store.get_all():
        if inter.tile_id not in existing_ids and abs(inter.interest_score) >= 0.5:
            tile = Tile(
                id=inter.tile_id,
                silo=inter.tile_silo or "alpha",
                column="resolved",
                title=inter.tile_title or "Saved interaction",
                summary=inter.tile_summary or "",
                detail="",
                sources=[inter.tile_silo or "alpha"],
                created_at=inter.tile_id / 1000.0,  # ID is timestamp-based
            )
            tile_store._tiles.append(tile)
            recovered += 1
    if recovered:
        tile_store._tiles.sort(key=lambda t: t.created_at, reverse=True)
        tile_store._save_to_disk()
        logger.info(f"Recovered {recovered} tiles from interaction data")


# --- Interaction tracking ---

_INTERACTIONS_FILE = Path(__file__).resolve().parent.parent / ".interactions_cache.json"


class TileInteraction(BaseModel):
    tile_id: int
    tile_title: str = ""
    tile_silo: str = ""
    tile_summary: str = ""
    thumbs_up: int = 0
    thumbs_down: int = 0
    expanded: bool = False
    expand_duration_s: float = 0.0
    followup_questions: List[str] = []
    interest_score: float = 0.0

    def compute_score(self) -> float:
        score = 0.0
        score += 2.0 * self.thumbs_up
        score -= 2.0 * self.thumbs_down
        if self.expanded:
            score += 0.5
        score += min(self.expand_duration_s / 30.0, 1.0)
        score += 1.0 * len(self.followup_questions)
        return round(score, 2)


class InteractionStore:
    """In-memory interaction store with file-based persistence."""

    def __init__(self):
        self._interactions: dict[int, TileInteraction] = {}
        self._lock: Optional[asyncio.Lock] = None
        self._load_from_disk()

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _load_from_disk(self):
        try:
            if _INTERACTIONS_FILE.exists():
                data = json.loads(_INTERACTIONS_FILE.read_text())
                for item in data:
                    inter = TileInteraction(**item)
                    self._interactions[inter.tile_id] = inter
                logger.info(f"Loaded {len(self._interactions)} interactions from disk cache")
        except Exception as e:
            logger.warning(f"Failed to load interactions cache: {e}")
            self._interactions = {}

    def _save_to_disk(self):
        try:
            data = [i.model_dump() for i in self._interactions.values()]
            _atomic_write(_INTERACTIONS_FILE, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Failed to save interactions cache: {e}")

    async def record(self, tile_id: int, data: dict) -> TileInteraction:
        async with self._get_lock():
            existing = self._interactions.get(tile_id)
            if existing:
                # Merge signals
                existing.thumbs_up += data.get("thumbs_up", 0)
                existing.thumbs_down += data.get("thumbs_down", 0)
                if data.get("expanded"):
                    existing.expanded = True
                existing.expand_duration_s += data.get("expand_duration_s", 0.0)
                for q in data.get("followup_questions", []):
                    if q and q not in existing.followup_questions:
                        existing.followup_questions.append(q)
                # Update metadata if provided
                if data.get("tile_title"):
                    existing.tile_title = data["tile_title"]
                if data.get("tile_silo"):
                    existing.tile_silo = data["tile_silo"]
                if data.get("tile_summary"):
                    existing.tile_summary = data["tile_summary"]
                existing.interest_score = existing.compute_score()
                result = existing
            else:
                inter = TileInteraction(
                    tile_id=tile_id,
                    tile_title=data.get("tile_title", ""),
                    tile_silo=data.get("tile_silo", ""),
                    tile_summary=data.get("tile_summary", ""),
                    thumbs_up=data.get("thumbs_up", 0),
                    thumbs_down=data.get("thumbs_down", 0),
                    expanded=data.get("expanded", False),
                    expand_duration_s=data.get("expand_duration_s", 0.0),
                    followup_questions=[q for q in data.get("followup_questions", []) if q],
                )
                inter.interest_score = inter.compute_score()
                self._interactions[tile_id] = inter
                result = inter

            # Cap at 200 interactions — drop lowest scores
            if len(self._interactions) > 200:
                sorted_ids = sorted(
                    self._interactions,
                    key=lambda tid: self._interactions[tid].interest_score,
                )
                while len(self._interactions) > 200:
                    self._interactions.pop(sorted_ids.pop(0))

            self._save_to_disk()
            return result

    async def reset(self):
        async with self._get_lock():
            self._interactions = {}
            self._save_to_disk()

    async def reset_one(self, tile_id: int):
        async with self._get_lock():
            if tile_id in self._interactions:
                del self._interactions[tile_id]
                self._save_to_disk()

    def get_all(self) -> List[TileInteraction]:
        return list(self._interactions.values())

    def get_silo_scores(self) -> dict[str, float]:
        """Cumulative interest score per silo."""
        scores: dict[str, float] = {}
        for inter in self._interactions.values():
            if inter.tile_silo:
                scores[inter.tile_silo] = scores.get(inter.tile_silo, 0.0) + inter.interest_score
        return scores

    def get_top_liked(self, n: int = 5) -> List[TileInteraction]:
        """Top-n interactions by positive score."""
        positive = [i for i in self._interactions.values() if i.interest_score > 0]
        return sorted(positive, key=lambda i: i.interest_score, reverse=True)[:n]

    def get_disliked(self) -> List[TileInteraction]:
        """Interactions with net negative score."""
        return [i for i in self._interactions.values() if i.interest_score < 0]

    def get_drilldown_candidates(self, threshold: float = 3.0) -> List[TileInteraction]:
        """Interactions with score >= threshold, suitable for drill-down."""
        return [i for i in self._interactions.values() if i.interest_score >= threshold]


interaction_store = InteractionStore()

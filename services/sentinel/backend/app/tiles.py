"""Workspace-scoped tile and interaction stores.

Each workspace gets its own TileStore and InteractionStore, keyed by
workspace_id. The global singletons are replaced by factory functions
that return the correct store for a given workspace.
"""
import asyncio
import itertools
import json
import logging
import time
from typing import Optional, List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Atomic counter for tile IDs — seeded from current time, increments monotonically
_id_counter = itertools.count(int(time.time() * 1000))


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
    """In-memory tile store with SSE broadcast, scoped to a workspace."""

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self._tiles: List[Tile] = []
        self._subscribers: List[asyncio.Queue] = []
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def load_tiles(self, tiles: List[Tile]):
        """Load tiles from database (called on workspace activate)."""
        self._tiles = list(tiles)

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
                    istore = get_interaction_store(self.workspace_id)
                    for inter in istore.get_all():
                        if abs(inter.interest_score) >= 0.5:
                            protected_ids.add(inter.tile_id)
                except Exception:
                    pass
                protected = [t for t in self._tiles if t.id in protected_ids]
                unprotected = [t for t in self._tiles if t.id not in protected_ids]
                max_unprotected = MAX_TILES - len(protected)
                if max_unprotected > 0:
                    self._tiles = protected + unprotected[:max_unprotected]
                else:
                    self._tiles = protected[:MAX_TILES]
                self._tiles.sort(key=lambda t: t.created_at, reverse=True)
        # Broadcast to all subscribers of this workspace
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
            return len(self._tiles) < before

    async def move_tile(self, tile_id: int, new_column: str) -> Optional[Tile]:
        async with self._get_lock():
            for t in self._tiles:
                if t.id == tile_id:
                    t.column = new_column
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


# --- Interaction tracking ---

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
    """In-memory interaction store, scoped to a workspace + user."""

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self._interactions: dict[int, TileInteraction] = {}
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def load_interactions(self, interactions: dict[int, TileInteraction]):
        """Load interactions from database (called on workspace activate)."""
        self._interactions = dict(interactions)

    async def record(self, tile_id: int, data: dict) -> TileInteraction:
        async with self._get_lock():
            existing = self._interactions.get(tile_id)
            if existing:
                existing.thumbs_up += data.get("thumbs_up", 0)
                existing.thumbs_down += data.get("thumbs_down", 0)
                if data.get("expanded"):
                    existing.expanded = True
                existing.expand_duration_s += data.get("expand_duration_s", 0.0)
                for q in data.get("followup_questions", []):
                    if q and q not in existing.followup_questions:
                        existing.followup_questions.append(q)
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

            # Cap at 200 interactions
            if len(self._interactions) > 200:
                sorted_ids = sorted(
                    self._interactions,
                    key=lambda tid: self._interactions[tid].interest_score,
                )
                while len(self._interactions) > 200:
                    self._interactions.pop(sorted_ids.pop(0))

            return result

    async def reset(self):
        async with self._get_lock():
            self._interactions = {}

    async def reset_one(self, tile_id: int):
        async with self._get_lock():
            self._interactions.pop(tile_id, None)

    def get_all(self) -> List[TileInteraction]:
        return list(self._interactions.values())

    def get_silo_scores(self) -> dict[str, float]:
        scores: dict[str, float] = {}
        for inter in self._interactions.values():
            if inter.tile_silo:
                scores[inter.tile_silo] = scores.get(inter.tile_silo, 0.0) + inter.interest_score
        return scores

    def get_top_liked(self, n: int = 5) -> List[TileInteraction]:
        positive = [i for i in self._interactions.values() if i.interest_score > 0]
        return sorted(positive, key=lambda i: i.interest_score, reverse=True)[:n]

    def get_disliked(self) -> List[TileInteraction]:
        return [i for i in self._interactions.values() if i.interest_score < 0]

    def get_drilldown_candidates(self, threshold: float = 3.0) -> List[TileInteraction]:
        return [i for i in self._interactions.values() if i.interest_score >= threshold]


# ---------------------------------------------------------------------------
# Workspace-keyed registries
# ---------------------------------------------------------------------------

_tile_stores: dict[str, TileStore] = {}
_interaction_stores: dict[str, InteractionStore] = {}


def get_tile_store(workspace_id: str) -> TileStore:
    """Get or create the TileStore for a workspace."""
    if workspace_id not in _tile_stores:
        _tile_stores[workspace_id] = TileStore(workspace_id)
    return _tile_stores[workspace_id]


def get_interaction_store(workspace_id: str) -> InteractionStore:
    """Get or create the InteractionStore for a workspace."""
    if workspace_id not in _interaction_stores:
        _interaction_stores[workspace_id] = InteractionStore(workspace_id)
    return _interaction_stores[workspace_id]


def remove_workspace_stores(workspace_id: str):
    """Clean up stores when a workspace is deleted."""
    _tile_stores.pop(workspace_id, None)
    _interaction_stores.pop(workspace_id, None)

"""
Seed data loader.
Handles loading reference, sample, and customer seed data.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import asyncpg


@dataclass
class SeedFile:
    """Represents a seed data file."""
    name: str
    path: Path
    sql_content: str
    category: str  # reference, sample, customer


class SeedLoader:
    """Loads seed data into the database."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def load_seed(self, seed: SeedFile, dry_run: bool = False) -> tuple[bool, int, Optional[str]]:
        """
        Load a single seed file.

        Returns: (success, execution_time_ms, error_message)
        """
        if dry_run:
            print(f"  [DRY RUN] Would load seed: {seed.category}/{seed.name}")
            return True, 0, None

        start_time = time.time()
        error_message = None
        success = True

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(seed.sql_content)
        except Exception as e:
            success = False
            error_message = str(e)
            print(f"  [ERROR] Seed {seed.name}: {error_message}")

        execution_time_ms = int((time.time() - start_time) * 1000)
        return success, execution_time_ms, error_message


def discover_seeds(seeds_dir: Path, categories: list[str]) -> list[SeedFile]:
    """
    Discover seed files for the specified categories.

    Categories are processed in order: reference, sample, customer
    """
    seeds = []

    for category in categories:
        category_dir = seeds_dir / category
        if not category_dir.exists():
            continue

        for sql_file in sorted(category_dir.glob("*.sql")):
            seeds.append(SeedFile(
                name=sql_file.stem,
                path=sql_file,
                sql_content=sql_file.read_text(encoding='utf-8'),
                category=category
            ))

    return seeds


def get_seed_categories(seed_mode: str) -> list[str]:
    """
    Get the list of seed categories to load based on mode.

    Modes:
    - none: No seeds
    - reference: Only reference data (entity types, etc.)
    - sample: Reference + sample data (for dev/demo)
    - full: Reference + sample + customer (for full demo)
    """
    mode_map = {
        'none': [],
        'reference': ['reference'],
        'sample': ['reference', 'sample'],
        'full': ['reference', 'sample', 'customer'],
    }
    return mode_map.get(seed_mode, ['reference'])

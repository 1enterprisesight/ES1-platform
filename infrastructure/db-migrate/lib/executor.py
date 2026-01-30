"""
SQL migration executor.
Handles parsing and executing migration files with proper error handling.
"""

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import asyncpg

from .version_tracker import VersionTracker


@dataclass
class Migration:
    """Represents a migration file."""
    version: str
    description: str
    path: Path
    sql_content: str
    checksum: str

    @classmethod
    def from_file(cls, path: Path) -> Optional["Migration"]:
        """
        Parse a migration file.

        Expected filename format: V001__description_here.sql
        """
        filename = path.name

        # Parse version and description from filename
        # Format: V001__description_here.sql
        match = re.match(r'^V(\d+)__(.+)\.sql$', filename)
        if not match:
            return None

        version = f"V{match.group(1).zfill(3)}"
        description = match.group(2).replace('_', ' ')

        sql_content = path.read_text(encoding='utf-8')
        checksum = VersionTracker.compute_checksum(sql_content)

        return cls(
            version=version,
            description=description,
            path=path,
            sql_content=sql_content,
            checksum=checksum
        )


class MigrationExecutor:
    """Executes SQL migrations against a database."""

    def __init__(self, pool: asyncpg.Pool, tracker: VersionTracker):
        self.pool = pool
        self.tracker = tracker

    async def execute_migration(self, migration: Migration, dry_run: bool = False) -> tuple[bool, int, Optional[str]]:
        """
        Execute a single migration.

        Returns: (success, execution_time_ms, error_message)
        """
        if dry_run:
            print(f"  [DRY RUN] Would execute: {migration.version} - {migration.description}")
            return True, 0, None

        start_time = time.time()
        error_message = None
        success = True

        try:
            async with self.pool.acquire() as conn:
                # Execute the migration SQL
                # Using execute() which handles multiple statements
                await conn.execute(migration.sql_content)
        except Exception as e:
            success = False
            error_message = str(e)
            print(f"  [ERROR] {migration.version}: {error_message}")

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Record the migration attempt
        await self.tracker.record_migration(
            version=migration.version,
            description=migration.description,
            checksum=migration.checksum,
            execution_time_ms=execution_time_ms,
            success=success
        )

        return success, execution_time_ms, error_message

    async def validate_checksum(self, migration: Migration) -> tuple[bool, Optional[str]]:
        """
        Validate that a migration hasn't been modified since it was applied.

        Returns: (valid, error_message)
        """
        record = await self.tracker.get_migration_record(migration.version)
        if record and record.checksum != migration.checksum:
            return False, f"Checksum mismatch for {migration.version}: migration file has been modified"
        return True, None


def discover_migrations(migrations_dir: Path) -> list[Migration]:
    """
    Discover all migration files in a directory.

    Returns migrations sorted by version.
    """
    if not migrations_dir.exists():
        return []

    migrations = []
    for sql_file in sorted(migrations_dir.glob("V*.sql")):
        migration = Migration.from_file(sql_file)
        if migration:
            migrations.append(migration)

    # Sort by version number
    migrations.sort(key=lambda m: m.version)
    return migrations

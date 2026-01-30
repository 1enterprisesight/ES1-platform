"""
Version tracker for database migrations.
Manages the _schema_migrations table that tracks applied migrations.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import asyncpg


@dataclass
class MigrationRecord:
    """Represents a migration record in the tracking table."""
    version: str
    description: str
    checksum: str
    applied_at: datetime
    execution_time_ms: int
    success: bool


class VersionTracker:
    """Tracks migration versions in the database."""

    MIGRATIONS_TABLE = "_schema_migrations"

    CREATE_TABLE_SQL = f"""
    CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
        version VARCHAR(50) PRIMARY KEY,
        description TEXT,
        checksum VARCHAR(64) NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        execution_time_ms INTEGER,
        success BOOLEAN NOT NULL DEFAULT TRUE
    );
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def ensure_table_exists(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        async with self.pool.acquire() as conn:
            await conn.execute(self.CREATE_TABLE_SQL)

    async def get_applied_versions(self) -> set[str]:
        """Get all successfully applied migration versions."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT version FROM {self.MIGRATIONS_TABLE} WHERE success = TRUE"
            )
            return {row['version'] for row in rows}

    async def get_migration_record(self, version: str) -> Optional[MigrationRecord]:
        """Get a specific migration record."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {self.MIGRATIONS_TABLE} WHERE version = $1",
                version
            )
            if row:
                return MigrationRecord(
                    version=row['version'],
                    description=row['description'],
                    checksum=row['checksum'],
                    applied_at=row['applied_at'],
                    execution_time_ms=row['execution_time_ms'],
                    success=row['success']
                )
            return None

    async def record_migration(
        self,
        version: str,
        description: str,
        checksum: str,
        execution_time_ms: int,
        success: bool = True
    ) -> None:
        """Record a migration execution."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.MIGRATIONS_TABLE}
                    (version, description, checksum, execution_time_ms, success)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (version) DO UPDATE SET
                    description = EXCLUDED.description,
                    checksum = EXCLUDED.checksum,
                    applied_at = NOW(),
                    execution_time_ms = EXCLUDED.execution_time_ms,
                    success = EXCLUDED.success
                """,
                version, description, checksum, execution_time_ms, success
            )

    async def get_all_records(self) -> list[MigrationRecord]:
        """Get all migration records ordered by version."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM {self.MIGRATIONS_TABLE} ORDER BY version"
            )
            return [
                MigrationRecord(
                    version=row['version'],
                    description=row['description'],
                    checksum=row['checksum'],
                    applied_at=row['applied_at'],
                    execution_time_ms=row['execution_time_ms'],
                    success=row['success']
                )
                for row in rows
            ]

    @staticmethod
    def compute_checksum(sql_content: str) -> str:
        """Compute SHA-256 checksum of SQL content."""
        return hashlib.sha256(sql_content.encode('utf-8')).hexdigest()

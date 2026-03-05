"""Database-backed DAG bundle for Airflow 3.

Reads DAG files from the platform's dag_files table in PostgreSQL.
This eliminates the need for shared filesystems between the platform
and Airflow — both read/write through the database.

Flow:
  1. Platform-manager writes DAG source to dag_files table
  2. This bundle reads from that table on refresh()
  3. Writes files to a local temp directory for the dag-processor
  4. dag-processor parses them into Airflow's own database
  5. After parsing, Airflow's DB is the source of truth for execution
"""
import hashlib
import logging
import os
import shutil
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from airflow.dag_processing.bundles.base import BaseDagBundle

logger = logging.getLogger(__name__)


class PlatformDagBundle(BaseDagBundle):
    """DAG bundle that reads from the platform database's dag_files table."""

    supports_versioning = True

    def __init__(
        self,
        *,
        db_host: str | None = None,
        db_port: int | None = None,
        db_name: str | None = None,
        db_user: str | None = None,
        db_password: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        # Database config from kwargs or environment variables
        self.db_host = db_host or os.getenv("PLATFORM_DB_HOST", "postgres")
        self.db_port = db_port or int(os.getenv("PLATFORM_DB_PORT", "5432"))
        self.db_name = db_name or os.getenv("PLATFORM_DB_NAME", "engine_platform")
        self.db_user = db_user or os.getenv("PLATFORM_DB_USER", "engine_user")
        self.db_password = db_password or os.getenv("PLATFORM_DB_PASSWORD", "engine_dev_password")

        # Local cache directory for DAG files
        self._cache_dir = self.base_dir / "dags"
        self._current_hash: str | None = None

    def _get_connection(self):
        """Create a database connection."""
        return psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password,
        )

    def _fetch_dag_files(self) -> list[dict]:
        """Fetch all DAG files from the database."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT filename, content, updated_at FROM dag_files ORDER BY filename"
                    )
                    return cur.fetchall()
        except psycopg2.OperationalError as e:
            logger.warning(f"Could not connect to platform database: {e}")
            return []
        except psycopg2.ProgrammingError as e:
            # Table doesn't exist yet (first startup before platform-manager creates it)
            logger.info(f"dag_files table not ready: {e}")
            return []

    def _compute_hash(self, files: list[dict]) -> str:
        """Compute a hash of all files for version tracking."""
        h = hashlib.sha256()
        for f in files:
            h.update(f["filename"].encode())
            h.update(f["content"].encode())
        return h.hexdigest()[:12]

    def _sync_to_disk(self, files: list[dict]) -> None:
        """Sync database files to the local cache directory."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Track which files should exist
        expected_files = set()

        for f in files:
            filename = f["filename"]
            content = f["content"]
            expected_files.add(filename)

            file_path = self._cache_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Only write if content changed
            if file_path.exists():
                existing = file_path.read_text()
                if existing == content:
                    continue

            file_path.write_text(content)
            logger.info(f"Synced DAG file from database: {filename}")

        # Remove files that are no longer in the database
        if self._cache_dir.exists():
            for file_path in self._cache_dir.rglob("*.py"):
                rel_path = str(file_path.relative_to(self._cache_dir))
                if rel_path not in expected_files:
                    file_path.unlink()
                    logger.info(f"Removed DAG file no longer in database: {rel_path}")

    def initialize(self) -> None:
        """Initialize the bundle by syncing files from database to disk."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        files = self._fetch_dag_files()
        self._sync_to_disk(files)
        self._current_hash = self._compute_hash(files) if files else None

        super().initialize()
        logger.info(
            f"PlatformDagBundle initialized: {len(files)} DAG files, "
            f"version={self._current_hash}"
        )

    def refresh(self) -> None:
        """Check for updates and sync new/changed files."""
        files = self._fetch_dag_files()
        new_hash = self._compute_hash(files) if files else None

        if new_hash != self._current_hash:
            logger.info(
                f"DAG files changed (version {self._current_hash} -> {new_hash}), syncing..."
            )
            self._sync_to_disk(files)
            self._current_hash = new_hash

    @property
    def path(self) -> Path:
        """Path where DAG files are cached locally."""
        return self._cache_dir

    def get_current_version(self) -> str | None:
        """Return hash of current DAG files state."""
        return self._current_hash

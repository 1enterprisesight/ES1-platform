#!/usr/bin/env python3
"""
ES1 Platform Database Migration Runner

Runs versioned SQL migrations and seed data against PostgreSQL databases.
Supports multiple databases with independent migration tracking.

Usage:
    python migrate.py --all-databases
    python migrate.py --database postgres
    python migrate.py --database aiml-postgres --seed=sample
    python migrate.py --dry-run --all-databases
    python migrate.py --status
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import asyncpg

from lib.version_tracker import VersionTracker
from lib.executor import MigrationExecutor, discover_migrations
from lib.seed_loader import SeedLoader, discover_seeds, get_seed_categories


# Database configurations
DATABASES = {
    'postgres': {
        'host': os.getenv('POSTGRES_HOST', 'postgres'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'es1_platform'),
        'user': os.getenv('POSTGRES_USER', 'es1_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'es1_password'),
        'migrations_dir': 'migrations/postgres',
        'seeds_dir': 'seeds/postgres',
    },
    'aiml-postgres': {
        'host': os.getenv('AIML_POSTGRES_HOST', 'aiml-postgres'),
        'port': int(os.getenv('AIML_POSTGRES_PORT', '5432')),
        'database': os.getenv('AIML_POSTGRES_DB', 'aiml'),
        'user': os.getenv('AIML_POSTGRES_USER', 'aiml_user'),
        'password': os.getenv('AIML_POSTGRES_PASSWORD', 'aiml_password'),
        'migrations_dir': 'migrations/aiml-postgres',
        'seeds_dir': 'seeds/aiml-postgres',
    },
}

# Base directory for migrations and seeds
BASE_DIR = Path(__file__).parent


async def get_pool(config: dict) -> asyncpg.Pool:
    """Create a connection pool for the database."""
    return await asyncpg.create_pool(
        host=config['host'],
        port=config['port'],
        database=config['database'],
        user=config['user'],
        password=config['password'],
        min_size=1,
        max_size=5,
    )


async def run_migrations(
    db_name: str,
    config: dict,
    dry_run: bool = False,
    seed_mode: str = 'reference'
) -> tuple[int, int, int]:
    """
    Run migrations for a single database.

    Returns: (applied_count, skipped_count, failed_count)
    """
    print(f"\n{'='*60}")
    print(f"Database: {db_name} ({config['host']}:{config['port']}/{config['database']})")
    print(f"{'='*60}")

    try:
        pool = await get_pool(config)
    except Exception as e:
        print(f"[ERROR] Failed to connect to {db_name}: {e}")
        return 0, 0, 1

    try:
        # Initialize version tracker
        tracker = VersionTracker(pool)
        await tracker.ensure_table_exists()

        # Get applied versions
        applied_versions = await tracker.get_applied_versions()
        print(f"Previously applied migrations: {len(applied_versions)}")

        # Discover migrations
        migrations_dir = BASE_DIR / config['migrations_dir']
        migrations = discover_migrations(migrations_dir)
        print(f"Found {len(migrations)} migration files in {migrations_dir}")

        # Run migrations
        executor = MigrationExecutor(pool, tracker)
        applied = 0
        skipped = 0
        failed = 0

        for migration in migrations:
            if migration.version in applied_versions:
                # Validate checksum for already applied migrations
                valid, error = await executor.validate_checksum(migration)
                if not valid:
                    print(f"  [WARNING] {error}")
                skipped += 1
                continue

            print(f"\n  Applying: {migration.version} - {migration.description}")
            success, time_ms, error = await executor.execute_migration(migration, dry_run)

            if success:
                applied += 1
                if not dry_run:
                    print(f"    [OK] Applied in {time_ms}ms")
            else:
                failed += 1
                print(f"    [FAILED] {error}")

        # Run seeds
        if seed_mode != 'none':
            print(f"\n  Loading seeds (mode: {seed_mode})")
            seeds_dir = BASE_DIR / config['seeds_dir']
            categories = get_seed_categories(seed_mode)
            seeds = discover_seeds(seeds_dir, categories)

            if seeds:
                seed_loader = SeedLoader(pool)
                for seed in seeds:
                    print(f"    Loading: {seed.category}/{seed.name}")
                    success, time_ms, error = await seed_loader.load_seed(seed, dry_run)
                    if not success:
                        print(f"      [WARNING] Seed error: {error}")
            else:
                print(f"    No seed files found in {seeds_dir}")

        print(f"\n  Summary: {applied} applied, {skipped} skipped, {failed} failed")
        return applied, skipped, failed

    finally:
        await pool.close()


async def show_status(db_name: str, config: dict) -> None:
    """Show migration status for a database."""
    print(f"\n{'='*60}")
    print(f"Database: {db_name}")
    print(f"{'='*60}")

    try:
        pool = await get_pool(config)
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return

    try:
        tracker = VersionTracker(pool)
        await tracker.ensure_table_exists()

        records = await tracker.get_all_records()

        if not records:
            print("  No migrations have been applied.")
            return

        print(f"\n  {'Version':<10} {'Applied At':<20} {'Time':<8} {'Status':<8} Description")
        print(f"  {'-'*10} {'-'*20} {'-'*8} {'-'*8} {'-'*30}")

        for record in records:
            status = "OK" if record.success else "FAILED"
            applied = record.applied_at.strftime("%Y-%m-%d %H:%M:%S")
            time_str = f"{record.execution_time_ms}ms"
            print(f"  {record.version:<10} {applied:<20} {time_str:<8} {status:<8} {record.description}")

    finally:
        await pool.close()


async def main() -> int:
    parser = argparse.ArgumentParser(
        description='ES1 Platform Database Migration Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate.py --all-databases              Run all pending migrations
  python migrate.py --database postgres          Migrate only the main database
  python migrate.py --dry-run                    Show what would be executed
  python migrate.py --seed=sample                Include sample data
  python migrate.py --status                     Show migration status
        """
    )

    parser.add_argument(
        '--all-databases',
        action='store_true',
        help='Run migrations on all configured databases'
    )

    parser.add_argument(
        '--database', '-d',
        choices=list(DATABASES.keys()),
        help='Target database to migrate'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be executed without making changes'
    )

    parser.add_argument(
        '--seed',
        choices=['none', 'reference', 'sample', 'full'],
        default='reference',
        help='Seed data mode (default: reference)'
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Show migration status instead of running migrations'
    )

    args = parser.parse_args()

    # Determine which databases to process
    if args.all_databases:
        databases = list(DATABASES.keys())
    elif args.database:
        databases = [args.database]
    else:
        databases = list(DATABASES.keys())

    if args.status:
        for db_name in databases:
            await show_status(db_name, DATABASES[db_name])
        return 0

    # Run migrations
    total_applied = 0
    total_skipped = 0
    total_failed = 0

    for db_name in databases:
        applied, skipped, failed = await run_migrations(
            db_name,
            DATABASES[db_name],
            dry_run=args.dry_run,
            seed_mode=args.seed
        )
        total_applied += applied
        total_skipped += skipped
        total_failed += failed

    print(f"\n{'='*60}")
    print(f"Total: {total_applied} applied, {total_skipped} skipped, {total_failed} failed")
    print(f"{'='*60}")

    return 1 if total_failed > 0 else 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

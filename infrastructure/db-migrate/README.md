# ES1 Platform Database Migrations

This directory contains the database migration system for ES1 Platform. It provides versioned, idempotent SQL migrations with Python orchestration.

## Overview

The migration system:
- Tracks applied migrations in a `_schema_migrations` table
- Supports multiple databases (postgres, aiml-postgres)
- Provides idempotent migrations (safe to run multiple times)
- Includes seed data for reference, sample, and customer configurations

## Directory Structure

```
db-migrate/
├── Dockerfile              # Container for running migrations
├── migrate.py             # Main migration runner
├── requirements.txt       # Python dependencies
├── lib/
│   ├── version_tracker.py # Version tracking logic
│   ├── executor.py        # Migration execution
│   └── seed_loader.py     # Seed data loading
├── migrations/
│   ├── postgres/          # Main database migrations
│   │   └── V001__*.sql
│   └── aiml-postgres/     # AIML database migrations
│       └── V001__*.sql
└── seeds/
    ├── postgres/
    │   ├── reference/     # Always applied (system defaults)
    │   └── sample/        # Dev/demo data
    └── aiml-postgres/
        ├── reference/     # Entity types, relationship types
        └── sample/        # Demo agents, knowledge bases
```

## Migration File Naming

Migrations follow the format: `V<number>__<description>.sql`

Examples:
- `V001__extensions.sql`
- `V002__audit_schema.sql`
- `V003__vector_tables.sql`

The version number determines execution order.

## Usage

### Docker Compose (Development)

```bash
# Run all migrations with reference seeds
docker compose -f docker-compose.yml -f docker-compose.db-migrate.yml run --rm db-migrate

# Run with sample data (for development)
docker compose -f docker-compose.yml -f docker-compose.db-migrate.yml run --rm db-migrate --seed=sample

# Dry run (preview changes)
docker compose -f docker-compose.yml -f docker-compose.db-migrate.yml run --rm db-migrate --dry-run

# Check status
docker compose -f docker-compose.yml -f docker-compose.db-migrate.yml run --rm db-migrate --status
```

### Kubernetes (Production)

```bash
# Apply the migration job
kubectl apply -f k8s/base/jobs/db-migrate-job.yaml

# Check logs
kubectl logs job/db-migrate

# Run again (delete and recreate)
kubectl delete job db-migrate
kubectl apply -f k8s/base/jobs/db-migrate-job.yaml
```

### Local Python

```bash
cd infrastructure/db-migrate
pip install -r requirements.txt
python migrate.py --all-databases --seed=reference
```

## Seed Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `none` | No seeds | Bare database |
| `reference` | System defaults only | Production |
| `sample` | Reference + demo data | Development |
| `full` | All seeds | Full demo |

## Writing Migrations

### Idempotency Rules

All migrations MUST be idempotent (safe to run multiple times):

```sql
-- Use IF NOT EXISTS for tables
CREATE TABLE IF NOT EXISTS schema.table_name (...);

-- Use IF NOT EXISTS for indexes
CREATE INDEX IF NOT EXISTS idx_name ON table_name(column);

-- Use CREATE OR REPLACE for views/functions
CREATE OR REPLACE VIEW schema.view_name AS ...;

-- Use ON CONFLICT for seed data
INSERT INTO table_name (id, name) VALUES (1, 'value')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
```

### Adding a New Migration

1. Create a new SQL file with the next version number:
   ```
   migrations/aiml-postgres/V008__new_feature.sql
   ```

2. Write idempotent SQL (see rules above)

3. Test locally:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.db-migrate.yml run --rm db-migrate --dry-run
   docker compose -f docker-compose.yml -f docker-compose.db-migrate.yml run --rm db-migrate
   ```

4. Verify idempotency (run twice):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.db-migrate.yml run --rm db-migrate
   # Should report "0 applied, N skipped, 0 failed"
   ```

## Checksum Validation

The migration system computes SHA-256 checksums of each migration file. If a previously applied migration is modified, a warning will be displayed. Never modify migrations that have been applied to production - create a new migration instead.

## Troubleshooting

### Migration Failed

1. Check the error message in the output
2. Fix the SQL issue
3. If the migration was partially applied, you may need to manually clean up
4. Run migrations again

### Checksum Mismatch

This means a migration file was modified after being applied:
1. If in development, you can reset the database
2. In production, create a new migration to fix the issue

### Connection Issues

Ensure the database containers are running and healthy:
```bash
docker compose ps
docker compose logs postgres
docker compose logs aiml-postgres
```

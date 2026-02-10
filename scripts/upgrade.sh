#!/usr/bin/env bash
# Docker Compose upgrade script for ES1 Platform
# Pulls new images, runs database migrations, restarts services with zero data loss.
#
# Usage:
#   ./scripts/upgrade.sh              # Upgrade all services
#   ./scripts/upgrade.sh --dry-run    # Show what would happen without making changes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
    esac
done

# All compose files
COMPOSE_FILES=(
    "-f" "docker-compose.yml"
    "-f" "docker-compose.airflow.yml"
    "-f" "docker-compose.langfuse.yml"
    "-f" "docker-compose.langflow.yml"
    "-f" "docker-compose.aiml.yml"
    "-f" "docker-compose.es1-platform-manager.yml"
    "-f" "docker-compose.n8n.yml"
    "-f" "docker-compose.agents.yml"
    "-f" "docker-compose.crewai-studio.yml"
    "-f" "docker-compose.autogen-studio.yml"
    "-f" "docker-compose.monitoring.yml"
)

cd "$PROJECT_DIR"

echo "=== ES1 Platform Upgrade ==="
echo ""

# Step 1: Pull latest images
echo "Step 1: Pulling latest images..."
if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would pull all service images"
else
    docker compose "${COMPOSE_FILES[@]}" pull
fi
echo ""

# Step 2: Run database migrations
echo "Step 2: Running database migrations..."
if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would run: docker compose -f docker-compose.yml -f docker-compose.db-migrate.yml run --rm db-migrate"
else
    # Ensure databases are up before migrating
    docker compose -f docker-compose.yml up -d postgres aiml-postgres
    echo "  Waiting for databases to be ready..."
    sleep 5

    docker compose \
        -f docker-compose.yml \
        -f docker-compose.db-migrate.yml \
        run --rm db-migrate || {
            echo "WARNING: Migration failed. Services not restarted."
            echo "Fix the migration issue and re-run this script."
            exit 1
        }
fi
echo ""

# Step 3: Restart services with new images
echo "Step 3: Restarting services with new images..."
if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would restart all services"
else
    docker compose "${COMPOSE_FILES[@]}" up -d
fi
echo ""

# Step 4: Wait for health checks
echo "Step 4: Waiting for services to become healthy..."
if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would wait for health checks"
else
    sleep 10
    echo "  Checking service health..."

    # Check Platform Manager API
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  Platform Manager API: healthy"
    else
        echo "  Platform Manager API: not ready (may still be starting)"
    fi

    # Check KrakenD
    if curl -sf http://localhost:8080/__health > /dev/null 2>&1; then
        echo "  KrakenD: healthy"
    else
        echo "  KrakenD: not ready (may still be starting)"
    fi
fi
echo ""

echo "=== Upgrade complete ==="
echo "Run 'docker compose ${COMPOSE_FILES[*]} ps' to check service status."

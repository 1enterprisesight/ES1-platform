#!/usr/bin/env bash
# Build all services locally
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

TAG="${1:-local}"
REGISTRY="${REGISTRY:-ghcr.io/1enterprisesight/es1-platform}"

echo "=== Building All Services ==="
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo ""

cd "$PROJECT_ROOT"

# Find all services with Dockerfiles
for service_dir in services/*/; do
    if [[ -f "${service_dir}Dockerfile" ]]; then
        service_name=$(basename "$service_dir")

        # Skip templates unless explicitly requested
        if [[ "$service_name" == service-template-* ]] && [[ "$TAG" != "template" ]]; then
            echo "Skipping template: $service_name"
            continue
        fi

        echo "Building: $service_name"
        docker build \
            -t "$REGISTRY/$service_name:$TAG" \
            -f "${service_dir}Dockerfile" \
            "$service_dir"
        echo "  ✓ $service_name:$TAG"
    fi
done

echo ""
echo "=== Build Complete ==="
docker images | grep "$REGISTRY" | head -20

#!/usr/bin/env bash
# Build all services for multiple architectures (amd64 + arm64)
# Requires Docker Buildx
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

TAG="${1:-latest}"
REGISTRY="${REGISTRY:-ghcr.io/1enterprisesight/es1-platform}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
PUSH="${PUSH:-false}"

echo "=== Building Multi-Arch Images ==="
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Platforms: $PLATFORMS"
echo "Push: $PUSH"
echo ""

# Ensure buildx builder exists
BUILDER_NAME="${BUILDER_NAME:-es1-multiarch}"
if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
    echo "Creating buildx builder: $BUILDER_NAME"
    docker buildx create --name "$BUILDER_NAME" --use --bootstrap
else
    docker buildx use "$BUILDER_NAME"
fi

cd "$PROJECT_ROOT"

BUILD_ARGS="--platform $PLATFORMS"
if [[ "$PUSH" == "true" ]]; then
    BUILD_ARGS="$BUILD_ARGS --push"
else
    BUILD_ARGS="$BUILD_ARGS --load"
    # Can only load single platform
    PLATFORMS="linux/arm64"  # Native for Apple Silicon
    BUILD_ARGS="--platform $PLATFORMS"
fi

# Find all services with Dockerfiles
for service_dir in services/*/; do
    if [[ -f "${service_dir}Dockerfile" ]]; then
        service_name=$(basename "$service_dir")

        # Skip templates
        if [[ "$service_name" == service-template-* ]]; then
            echo "Skipping template: $service_name"
            continue
        fi

        echo "Building: $service_name ($PLATFORMS)"
        docker buildx build \
            $BUILD_ARGS \
            -t "$REGISTRY/$service_name:$TAG" \
            -f "${service_dir}Dockerfile" \
            "$service_dir"
        echo "  ✓ $service_name:$TAG"
    fi
done

echo ""
echo "=== Multi-Arch Build Complete ==="

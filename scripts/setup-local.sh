#!/usr/bin/env bash
# One-time local environment setup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== ES1 Platform Local Setup ==="

# Check prerequisites
echo "Checking prerequisites..."

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is not installed. Please install it first."
        exit 1
    fi
    echo "  ✓ $1"
}

check_command docker
check_command kubectl

# Check Docker is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker is not running. Please start Docker Desktop."
    exit 1
fi
echo "  ✓ Docker is running"

# Check Kubernetes context
CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "")
if [[ "$CURRENT_CONTEXT" != "docker-desktop" ]]; then
    echo "Switching kubectl context to docker-desktop..."
    kubectl config use-context docker-desktop
fi
echo "  ✓ Using docker-desktop context"

# Check Kubernetes is ready
if ! kubectl cluster-info &> /dev/null; then
    echo "ERROR: Kubernetes is not running. Enable it in Docker Desktop settings."
    exit 1
fi
echo "  ✓ Kubernetes is running"

# Create namespaces
echo ""
echo "Creating namespaces..."
kubectl apply -f "$PROJECT_ROOT/k8s/base/namespaces/namespaces.yaml"

# Build local images
echo ""
echo "Building local Docker images..."
cd "$PROJECT_ROOT"

# Build KrakenD
echo "  Building krakend..."
docker build -t ghcr.io/1enterprisesight/es1-platform/krakend:local \
    -f services/krakend/Dockerfile \
    services/krakend

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Deploy infrastructure: make deploy-infra"
echo "  2. Deploy services: make deploy-local"
echo "  3. Or use Docker Compose: make up"
echo ""

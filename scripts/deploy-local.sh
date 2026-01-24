#!/usr/bin/env bash
# Deploy to local Kubernetes (Docker Desktop)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Deploying to Local Kubernetes ==="

# Verify context
CURRENT_CONTEXT=$(kubectl config current-context)
if [[ "$CURRENT_CONTEXT" != "docker-desktop" ]]; then
    echo "WARNING: Not using docker-desktop context (current: $CURRENT_CONTEXT)"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

cd "$PROJECT_ROOT"

# Apply with kustomize
echo "Applying local overlay..."
kubectl apply -k k8s/overlays/local

echo ""
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=120s deployment/krakend -n es1-platform || true

echo ""
echo "=== Deployment Status ==="
kubectl get pods -n es1-platform
kubectl get pods -n es1-infrastructure

echo ""
echo "=== Services ==="
kubectl get svc -n es1-platform
kubectl get svc -n es1-infrastructure

echo ""
echo "To access KrakenD locally:"
echo "  kubectl port-forward svc/krakend 8080:80 -n es1-platform"

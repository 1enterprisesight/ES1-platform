# ES1 Platform

Cloud-portable, multi-service Kubernetes platform with KrakenD API Gateway.

## Quick Start

```bash
# One-time setup
make setup

# Start with Docker Compose (recommended for development)
make up

# Or deploy to local Kubernetes
make deploy-local
```

## Project Structure

```
ES1-platform/
├── services/                    # Application services
│   ├── krakend/                # KrakenD API Gateway
│   ├── service-template-python/# Python service template
│   ├── service-template-node/  # Node.js service template
│   └── service-template-go/    # Go service template
├── infrastructure/             # Infrastructure containers
│   ├── postgres/              # PostgreSQL with extensions
│   └── redis/                 # Redis configuration
├── k8s/                       # Kubernetes manifests
│   ├── base/                  # Base manifests
│   └── overlays/              # Environment-specific overlays
│       ├── local/            # Docker Desktop
│       ├── gke/              # Google Kubernetes Engine
│       ├── eks/              # Amazon EKS
│       └── aks/              # Azure AKS
├── scripts/                   # Helper scripts
└── .github/workflows/         # CI/CD pipelines
```

## Development Workflows

### Option 1: Docker Compose (Recommended)

Full local environment with hot reload:

```bash
make up          # Start everything
make logs        # View logs
make down        # Stop everything
```

Access:
- KrakenD API: http://localhost:8080
- KrakenD Metrics: http://localhost:8090

### Option 2: Hybrid (Local code + Containerized infra)

Run services locally with containerized Postgres and Redis:

```bash
make up-infra    # Start Postgres + Redis
# Run your services locally
```

### Option 3: Local Kubernetes

Deploy to Docker Desktop's Kubernetes:

```bash
make setup       # Build images and create namespaces
make deploy-local
make port-forward  # Access at localhost:8080
```

## KrakenD Configuration

Edit `services/krakend/config/krakend.json` to:
- Add new endpoints
- Configure backend services
- Set up authentication
- Enable rate limiting

KrakenD supports hot reload in development - changes are picked up automatically.

## Creating a New Service

```bash
make new-service NAME=user-service TYPE=python
# Or: TYPE=node, TYPE=go
```

This creates:
- Service code from template in `services/<name>/`
- Kubernetes manifests in `k8s/base/services/<name>/`

Then add routes to KrakenD config to expose your service.

## Building Images

```bash
# Build KrakenD
make build

# Build all services
make build-all

# Build multi-arch for production (amd64 + arm64)
make build-multiarch

# Build and push to registry
make build-push
```

## Deploying to Cloud

```bash
# GKE
kubectl apply -k k8s/overlays/gke

# EKS
kubectl apply -k k8s/overlays/eks

# AKS
kubectl apply -k k8s/overlays/aks
```

## Namespaces

| Namespace | Purpose |
|-----------|---------|
| es1-platform | Application services + KrakenD |
| es1-infrastructure | PostgreSQL, Redis |
| es1-monitoring | Metrics, logging (future) |

## Common Commands

```bash
make help        # Show all available commands
make status      # Show Kubernetes pod/service status
make ctx-local   # Switch to docker-desktop context
make clean       # Clean up Docker resources
```

## Best Practices Implemented

- **Multi-arch builds**: All images support linux/amd64 and linux/arm64
- **Non-root containers**: All services run as non-root user
- **Multi-stage builds**: Minimal production images
- **Health checks**: Liveness and readiness probes on all services
- **Cloud portability**: Kustomize overlays for GKE, EKS, AKS
- **Hot reload**: Development containers support live config updates

# ES1 Platform Kubernetes Packaging & Deployment Plan

## Overview

Create a **separate installer repository** (`es1-platform-installer`) that packages the ES1 Platform for **air-gapped deployment** to any Kubernetes cluster using **Helm Charts**. All services run self-contained within the cluster with no external cloud dependencies.

### Key Design Principles

1. **Air-Gapped / Self-Contained**: NO external cloud services (no Cloud SQL, no Memorystore, no GCS/S3). Everything runs in-cluster.
2. **Two-Namespace Architecture**:
   - `es1-infrastructure` - Open source components (PostgreSQL, Redis, Prometheus, etc.)
   - `{customer}-platform` - Licensed ES1 Platform components (license-controlled)
3. **Multi-Tenant Branding**: Platform namespace reflects customer/reseller name (BEAM, Polygraf, Rimbal)
4. **Cloud Agnostic**: Works on any K8s cluster (GKE, EKS, AKS, on-prem, air-gapped)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KUBERNETES CLUSTER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  NAMESPACE: es1-infrastructure (Open Source - No License Required)  │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │  PostgreSQL (in-cluster)    │  Redis (in-cluster)                   │    │
│  │  Prometheus                 │  Grafana                              │    │
│  │  Airflow                    │  Ollama                               │    │
│  │  n8n                        │  Langflow                             │    │
│  │  MLflow                     │  Langfuse                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  NAMESPACE: {customer}-platform (Licensed - ES1 Platform Code)      │    │
│  │             Examples: beam-platform, polygraf-platform, rimbal-platform  │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │  KrakenD API Gateway        │  Platform Manager API                 │    │
│  │  Platform Manager UI        │  Agent Router                         │    │
│  │  CrewAI Service             │  AutoGen Service                      │    │
│  │  License Validator Sidecar  │  Branding ConfigMap                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  CLUSTER NETWORKING (Cloud-Provided)                                │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │  Ingress Controller (nginx/traefik)  │  LoadBalancer Services       │    │
│  │  NetworkPolicies                     │  DNS / Service Discovery     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Storage: All PersistentVolumeClaims use cluster-provided StorageClass
         (GKE: standard-rwo, EKS: gp3, AKS: managed-premium, on-prem: local-path)
```

---

## Two-Chart Architecture

### Chart 1: es1-infrastructure (Open Source)
Deploys to `es1-infrastructure` namespace. No license required.

**Components:**
- PostgreSQL (Bitnami chart)
- Redis (Bitnami chart)
- Prometheus + Grafana (kube-prometheus-stack)
- Airflow (official Airflow chart)
- Ollama (custom chart)
- MLflow (custom chart)
- n8n (custom chart)
- Langflow (custom chart)
- Langfuse (custom chart)

### Chart 2: es1-platform (Licensed)
Deploys to `{customer}-platform` namespace. Requires valid license.

**Components:**
- KrakenD API Gateway
- Platform Manager API
- Platform Manager UI
- Agent Router Service
- CrewAI Service
- AutoGen Service
- License Validator (sidecar/init container)
- Customer Branding ConfigMap

---

## Repository Structure

```
es1-platform-installer/
├── README.md
├── CHANGELOG.md
├── LICENSE
│
├── charts/
│   │
│   ├── es1-infrastructure/              # Chart 1: Open Source Components
│   │   ├── Chart.yaml
│   │   ├── Chart.lock
│   │   ├── values.yaml                  # Defaults
│   │   ├── values-minimal.yaml          # Minimal install
│   │   ├── values-production.yaml       # Production sizing
│   │   ├── templates/
│   │   │   ├── _helpers.tpl
│   │   │   ├── namespace.yaml           # Always: es1-infrastructure
│   │   │   ├── storage-class.yaml       # Optional: if cluster needs it
│   │   │   └── network-policies.yaml
│   │   └── charts/                      # Sub-charts (dependencies)
│   │       ├── postgresql/              # Bitnami PostgreSQL
│   │       ├── redis/                   # Bitnami Redis
│   │       ├── prometheus-stack/        # kube-prometheus-stack
│   │       ├── airflow/                 # Apache Airflow
│   │       ├── ollama/                  # Ollama LLM
│   │       ├── mlflow/                  # MLflow tracking
│   │       ├── n8n/                     # n8n workflows
│   │       ├── langflow/                # Langflow
│   │       └── langfuse/                # Langfuse tracing
│   │
│   └── es1-platform/                    # Chart 2: Licensed Platform
│       ├── Chart.yaml
│       ├── values.yaml                  # Defaults
│       ├── values-production.yaml       # Production sizing
│       ├── templates/
│       │   ├── _helpers.tpl
│       │   ├── namespace.yaml           # Dynamic: {{ .Values.customer.name }}-platform
│       │   ├── license-secret.yaml      # License key secret
│       │   ├── branding-configmap.yaml  # Customer branding
│       │   ├── cross-namespace-access.yaml  # RBAC for infra access
│       │   └── network-policies.yaml
│       └── charts/                      # Sub-charts
│           ├── krakend/                 # API Gateway
│           ├── platform-manager/        # API + UI
│           ├── agent-router/            # Agent routing
│           ├── crewai/                  # CrewAI service
│           └── autogen/                 # AutoGen service
│
├── terraform/                           # CLUSTER PROVISIONING ONLY
│   ├── modules/
│   │   ├── gcp/
│   │   │   ├── gke/                     # GKE cluster creation
│   │   │   └── networking/              # VPC, firewall, NAT
│   │   ├── aws/
│   │   │   ├── eks/                     # EKS cluster creation
│   │   │   └── networking/              # VPC, subnets, security groups
│   │   ├── azure/
│   │   │   ├── aks/                     # AKS cluster creation
│   │   │   └── networking/              # VNet, NSG
│   │   └── generic/
│   │       └── kubeconfig/              # Kubeconfig generation
│   │
│   └── environments/
│       ├── gcp-dev/
│       ├── gcp-prod/
│       ├── aws-dev/
│       ├── aws-prod/
│       └── azure-dev/
│
├── scripts/
│   ├── es1-install.sh                   # Main installer
│   ├── es1-upgrade.sh                   # Upgrade script
│   ├── es1-uninstall.sh                 # Clean uninstall
│   ├── es1-status.sh                    # Health check
│   ├── es1-backup.sh                    # Backup PVCs
│   ├── es1-restore.sh                   # Restore from backup
│   ├── local-dev/
│   │   ├── setup-kind.sh
│   │   ├── setup-minikube.sh
│   │   └── load-images.sh               # Pre-load images for air-gap
│   └── airgap/
│       ├── pull-images.sh               # Pull all images to tar
│       ├── push-images.sh               # Push to private registry
│       └── image-list.txt               # All required images
│
├── docs/
│   ├── INSTALLATION.md                  # Getting started
│   ├── UPGRADE.md                       # Upgrade procedures
│   ├── CONFIGURATION.md                 # All options
│   ├── ARCHITECTURE.md                  # System design
│   ├── TROUBLESHOOTING.md
│   ├── AIR-GAPPED-DEPLOYMENT.md         # Air-gapped guide
│   ├── CLUSTER-REQUIREMENTS.md          # K8s cluster requirements
│   ├── NETWORKING.md                    # Ingress, LoadBalancer, DNS
│   ├── LICENSING.md                     # License management
│   └── cloud-guides/
│       ├── GCP-GKE.md                   # GKE-specific networking
│       ├── AWS-EKS.md                   # EKS-specific networking
│       ├── AZURE-AKS.md                 # AKS-specific networking
│       └── ON-PREMISES.md               # On-prem / bare metal
│
├── examples/
│   ├── customers/
│   │   ├── beam/                        # BEAM customer config
│   │   │   ├── values-infrastructure.yaml
│   │   │   ├── values-platform.yaml
│   │   │   └── branding/
│   │   │       ├── logo.png
│   │   │       └── theme.json
│   │   ├── polygraf/                    # Polygraf customer config
│   │   └── rimbal/                      # Rimbal customer config
│   ├── local-minimal/
│   └── production-ha/
│
└── .github/
    └── workflows/
        ├── helm-test.yml
        ├── terraform-test.yml
        └── release.yml
```

---

## Helm Chart Design

### Chart 1: es1-infrastructure

```yaml
# charts/es1-infrastructure/Chart.yaml
apiVersion: v2
name: es1-infrastructure
description: Open source infrastructure for ES1 Platform (no license required)
type: application
version: 1.0.0
appVersion: "1.0.0"

dependencies:
  - name: postgresql
    version: "14.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled

  - name: redis
    version: "18.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled

  - name: kube-prometheus-stack
    version: "55.x.x"
    repository: "https://prometheus-community.github.io/helm-charts"
    condition: monitoring.enabled
    alias: monitoring

  - name: airflow
    version: "1.x.x"
    repository: "https://airflow.apache.org"
    condition: airflow.enabled

  # Custom sub-charts for services without official Helm charts
  - name: ollama
    version: "1.0.0"
    condition: ollama.enabled

  - name: mlflow
    version: "1.0.0"
    condition: mlflow.enabled

  - name: n8n
    version: "1.0.0"
    condition: n8n.enabled

  - name: langflow
    version: "1.0.0"
    condition: langflow.enabled

  - name: langfuse
    version: "1.0.0"
    condition: langfuse.enabled
```

```yaml
# charts/es1-infrastructure/values.yaml
global:
  # Storage class - leave empty to use cluster default
  storageClass: ""

  # Image pull settings for air-gapped deployments
  imageRegistry: ""           # e.g., "my-private-registry.com"
  imagePullSecrets: []

# All services deploy to es1-infrastructure namespace
namespace: es1-infrastructure

# PostgreSQL - IN CLUSTER (not external)
postgresql:
  enabled: true
  auth:
    postgresPassword: ""      # Generate or set via --set
    database: es1_platform
  primary:
    persistence:
      enabled: true
      size: 100Gi
  # Multiple databases for services
  initdbScripts:
    create-databases.sql: |
      CREATE DATABASE airflow;
      CREATE DATABASE langflow;
      CREATE DATABASE n8n;
      CREATE DATABASE langfuse;
      CREATE DATABASE mlflow;

# Redis - IN CLUSTER (not external)
redis:
  enabled: true
  auth:
    enabled: true
    password: ""              # Generate or set via --set
  master:
    persistence:
      enabled: true
      size: 10Gi

# Monitoring
monitoring:
  enabled: true
  prometheus:
    retention: 15d
    persistence:
      enabled: true
      size: 50Gi
  grafana:
    adminPassword: ""         # Generate or set
    persistence:
      enabled: true
      size: 10Gi

# Airflow
airflow:
  enabled: true
  executor: CeleryExecutor
  # Uses PostgreSQL from this chart
  data:
    metadataConnection:
      host: "{{ .Release.Name }}-postgresql"
      db: airflow

# Ollama (LLM inference)
ollama:
  enabled: true
  persistence:
    enabled: true
    size: 100Gi             # Model storage
  resources:
    requests:
      memory: "8Gi"
    limits:
      memory: "16Gi"
  # GPU support (optional)
  gpu:
    enabled: false
    type: "nvidia"

# MLflow
mlflow:
  enabled: true
  persistence:
    enabled: true
    size: 50Gi

# n8n
n8n:
  enabled: true
  persistence:
    enabled: true
    size: 10Gi

# Langflow
langflow:
  enabled: true
  persistence:
    enabled: true
    size: 10Gi

# Langfuse
langfuse:
  enabled: true
  persistence:
    enabled: true
    size: 10Gi
```

### Chart 2: es1-platform (Licensed)

```yaml
# charts/es1-platform/Chart.yaml
apiVersion: v2
name: es1-platform
description: ES1 Platform - Licensed enterprise AI/ML platform components
type: application
version: 1.0.0
appVersion: "1.0.0"

dependencies:
  - name: krakend
    version: "1.0.0"

  - name: platform-manager
    version: "1.0.0"

  - name: agent-router
    version: "1.0.0"
    condition: agents.enabled

  - name: crewai
    version: "1.0.0"
    condition: agents.crewai.enabled

  - name: autogen
    version: "1.0.0"
    condition: agents.autogen.enabled
```

```yaml
# charts/es1-platform/values.yaml
global:
  storageClass: ""
  imageRegistry: "ghcr.io/1enterprisesight"
  imagePullSecrets: []

# CUSTOMER CONFIGURATION - Required
customer:
  name: ""                    # REQUIRED: beam, polygraf, rimbal, etc.
  displayName: ""             # Display name: "BEAM Analytics"

# Namespace will be: {customer.name}-platform
# e.g., beam-platform, polygraf-platform

# License Configuration
license:
  # License key (base64 encoded)
  key: ""
  # Or reference existing secret
  existingSecret: ""
  secretKey: "license-key"
  # License server URL (for validation)
  serverUrl: "https://license.es1platform.com"
  # Offline mode (for air-gapped, uses local validation)
  offlineMode: false

# Branding Configuration
branding:
  # Primary color (hex)
  primaryColor: "#3B82F6"
  # Logo URL (served from ConfigMap or external)
  logoUrl: ""
  # Logo data (base64, if embedding)
  logoData: ""
  # Favicon
  faviconUrl: ""
  # App title
  appTitle: "ES1 Platform"
  # Footer text
  footerText: "Powered by ES1 Platform"

# Infrastructure namespace reference
infrastructure:
  namespace: es1-infrastructure
  # Service references (auto-discovered or manual)
  postgresql:
    host: "es1-infrastructure-postgresql.es1-infrastructure.svc.cluster.local"
    port: 5432
    database: es1_platform
    existingSecret: "es1-infrastructure-postgresql"
    secretKey: "postgres-password"
  redis:
    host: "es1-infrastructure-redis-master.es1-infrastructure.svc.cluster.local"
    port: 6379
    existingSecret: "es1-infrastructure-redis"
    secretKey: "redis-password"

# KrakenD API Gateway
krakend:
  enabled: true
  replicaCount: 2
  ingress:
    enabled: true
    className: ""             # nginx, traefik, etc.
    annotations: {}
    hosts:
      - host: api.example.com
        paths: ["/"]
    tls: []

# Platform Manager
platform-manager:
  enabled: true
  api:
    replicaCount: 2
  ui:
    replicaCount: 2
    ingress:
      enabled: true
      hosts:
        - host: platform.example.com

# Agent Services
agents:
  enabled: true
  router:
    replicaCount: 2
  crewai:
    enabled: true
    replicaCount: 1
  autogen:
    enabled: true
    replicaCount: 1
```

### Customer-Specific Values Example

```yaml
# examples/customers/beam/values-platform.yaml
customer:
  name: beam
  displayName: "BEAM Analytics"

license:
  key: "BASE64_ENCODED_LICENSE_KEY_HERE"
  offlineMode: true           # Air-gapped deployment

branding:
  primaryColor: "#1E40AF"
  appTitle: "BEAM Analytics Platform"
  footerText: "© 2026 BEAM Analytics"
  logoData: "BASE64_ENCODED_LOGO_PNG"

krakend:
  ingress:
    hosts:
      - host: api.beam-analytics.com
        paths: ["/"]
    tls:
      - secretName: beam-api-tls
        hosts:
          - api.beam-analytics.com

platform-manager:
  ui:
    ingress:
      hosts:
        - host: platform.beam-analytics.com
      tls:
        - secretName: beam-platform-tls
          hosts:
            - platform.beam-analytics.com
```

---

## Cluster Requirements

### Minimum Requirements

```yaml
# docs/CLUSTER-REQUIREMENTS.md content

## Node Requirements

### Minimum (Development/Testing)
- 3 nodes
- 4 vCPU per node
- 16 GB RAM per node
- 100 GB SSD per node

### Recommended (Production)
- 5+ nodes
- 8 vCPU per node
- 32 GB RAM per node
- 500 GB SSD per node

### Node Pools (Recommended)
1. **system** (2 nodes): Kubernetes system components
2. **infrastructure** (2-3 nodes): PostgreSQL, Redis, monitoring
3. **platform** (2-3 nodes): ES1 Platform services
4. **aiml** (1-3 nodes): Ollama, MLflow (optional GPU)

## Kubernetes Version
- Minimum: 1.25
- Recommended: 1.28+

## Required Cluster Features
- PersistentVolume support (CSI driver)
- LoadBalancer service type (or MetalLB for on-prem)
- Ingress controller (nginx-ingress or traefik)
- DNS resolution (CoreDNS)
- RBAC enabled

## Storage Requirements
- StorageClass with ReadWriteOnce support
- Minimum 500 GB total persistent storage
- Recommended: SSD-backed storage

## Network Requirements
- Pod-to-pod communication
- Service discovery (ClusterIP)
- Ingress for external access
- Egress: None required (air-gapped compatible)
```

---

## Networking & Ingress

### Cloud Provider Ingress Setup

```yaml
# GKE (Google Cloud)
krakend:
  ingress:
    className: "gce"
    annotations:
      kubernetes.io/ingress.class: "gce"
      kubernetes.io/ingress.global-static-ip-name: "es1-api-ip"

# EKS (AWS)
krakend:
  ingress:
    className: "alb"
    annotations:
      kubernetes.io/ingress.class: "alb"
      alb.ingress.kubernetes.io/scheme: "internet-facing"
      alb.ingress.kubernetes.io/target-type: "ip"

# AKS (Azure)
krakend:
  ingress:
    className: "nginx"
    annotations:
      kubernetes.io/ingress.class: "nginx"

# On-Premises (nginx-ingress + MetalLB)
krakend:
  ingress:
    className: "nginx"
    annotations:
      kubernetes.io/ingress.class: "nginx"
```

### Network Policies

```yaml
# Cross-namespace access: platform -> infrastructure
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-platform-to-infrastructure
  namespace: es1-infrastructure
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              es1-role: platform
```

---

## Terraform Modules (Cluster Only)

Terraform is used **ONLY for cluster provisioning**, not for managed services.

```hcl
# terraform/modules/gcp/gke/main.tf
resource "google_container_cluster" "es1" {
  name     = var.cluster_name
  location = var.region

  # We manage our own node pools
  remove_default_node_pool = true
  initial_node_count       = 1

  # Network config
  network    = var.network
  subnetwork = var.subnetwork

  # Private cluster (recommended for security)
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = var.air_gapped
    master_ipv4_cidr_block = "172.16.0.0/28"
  }

  # NO MANAGED SERVICES - all in-cluster
}

resource "google_container_node_pool" "infrastructure" {
  name       = "infrastructure"
  cluster    = google_container_cluster.es1.name
  location   = var.region
  node_count = var.infra_node_count

  node_config {
    machine_type = "e2-standard-4"
    disk_size_gb = 200
    disk_type    = "pd-ssd"

    labels = {
      "es1-pool" = "infrastructure"
    }

    taint {
      key    = "es1-pool"
      value  = "infrastructure"
      effect = "NO_SCHEDULE"
    }
  }
}

resource "google_container_node_pool" "platform" {
  name       = "platform"
  cluster    = google_container_cluster.es1.name
  location   = var.region
  node_count = var.platform_node_count

  node_config {
    machine_type = "e2-standard-4"
    disk_size_gb = 100
    disk_type    = "pd-ssd"

    labels = {
      "es1-pool" = "platform"
    }
  }
}
```

---

## Deployment Flow

### Installation Command

```bash
# 1. Create cluster (if needed)
cd terraform/environments/gcp-prod
terraform init && terraform apply

# 2. Get kubeconfig
gcloud container clusters get-credentials es1-cluster --region us-central1

# 3. Install infrastructure (open source)
helm upgrade --install es1-infra ./charts/es1-infrastructure \
  --namespace es1-infrastructure \
  --create-namespace \
  -f values-production.yaml

# 4. Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql \
  -n es1-infrastructure --timeout=300s

# 5. Install platform for customer (licensed)
helm upgrade --install beam-platform ./charts/es1-platform \
  --namespace beam-platform \
  --create-namespace \
  -f examples/customers/beam/values-platform.yaml \
  --set license.key="$BEAM_LICENSE_KEY"
```

### Simplified Installer Script

```bash
# scripts/es1-install.sh usage
./es1-install.sh \
  --customer beam \
  --license-key "$LICENSE_KEY" \
  --domain "beam-analytics.com" \
  --values ./examples/customers/beam/
```

---

## Air-Gapped Deployment

### Image Pre-loading

```bash
# scripts/airgap/pull-images.sh
#!/bin/bash
# Pull all images and save to tar files

IMAGES=(
  "postgres:15"
  "redis:7"
  "prom/prometheus:v2.48.0"
  "grafana/grafana:10.2.0"
  "apache/airflow:2.8.0"
  "ollama/ollama:latest"
  "ghcr.io/1enterprisesight/platform-manager-api:1.0.0"
  "ghcr.io/1enterprisesight/platform-manager-ui:1.0.0"
  "ghcr.io/1enterprisesight/krakend:1.0.0"
  # ... all other images
)

for img in "${IMAGES[@]}"; do
  docker pull "$img"
done

docker save "${IMAGES[@]}" -o es1-platform-images.tar
```

### Private Registry Configuration

```yaml
# values-airgap.yaml
global:
  imageRegistry: "my-private-registry.internal:5000"
  imagePullSecrets:
    - name: registry-credentials
```

---

## Upgrade Strategy

```bash
# Upgrade infrastructure (zero-downtime for stateless, rolling for stateful)
helm upgrade es1-infra ./charts/es1-infrastructure \
  --namespace es1-infrastructure \
  -f values-production.yaml \
  --atomic \
  --timeout 15m

# Upgrade platform (rolling deployment)
helm upgrade beam-platform ./charts/es1-platform \
  --namespace beam-platform \
  -f examples/customers/beam/values-platform.yaml \
  --atomic \
  --timeout 10m
```

---

## Implementation Phases

### Phase 1: Repository Setup
- [ ] Create `es1-platform-installer` repository
- [ ] Set up directory structure
- [ ] Create base chart scaffolding
- [ ] Set up CI/CD (helm lint, template tests)

### Phase 2: Infrastructure Chart
- [ ] PostgreSQL sub-chart configuration
- [ ] Redis sub-chart configuration
- [ ] Monitoring (Prometheus/Grafana) integration
- [ ] Airflow sub-chart
- [ ] Test local deployment with kind

### Phase 3: Platform Chart
- [ ] KrakenD sub-chart (migrate from kustomize)
- [ ] Platform Manager sub-chart (API + UI)
- [ ] Agent services sub-charts
- [ ] License validation integration
- [ ] Branding ConfigMap templates

### Phase 4: Integration & Testing
- [ ] Cross-namespace communication
- [ ] Network policies
- [ ] End-to-end testing on kind
- [ ] Customer example configurations (BEAM, Polygraf, Rimbal)

### Phase 5: Terraform Modules
- [ ] GKE cluster module
- [ ] EKS cluster module
- [ ] AKS cluster module
- [ ] Networking modules (VPC, firewall)

### Phase 6: Documentation & Scripts
- [ ] Installation documentation
- [ ] Air-gapped deployment guide
- [ ] Cluster requirements documentation
- [ ] Networking guide per cloud provider
- [ ] Installer scripts

### Phase 7: Release
- [ ] End-to-end testing on GKE
- [ ] Create first release
- [ ] Customer deployment testing

---

## Critical Files to Create

1. **charts/es1-infrastructure/Chart.yaml** - Infrastructure umbrella chart
2. **charts/es1-infrastructure/values.yaml** - Default infrastructure values
3. **charts/es1-platform/Chart.yaml** - Platform umbrella chart
4. **charts/es1-platform/values.yaml** - Default platform values with customer config
5. **charts/es1-platform/templates/namespace.yaml** - Dynamic namespace template
6. **terraform/modules/gcp/gke/main.tf** - GKE cluster provisioning
7. **scripts/es1-install.sh** - Main installer
8. **docs/CLUSTER-REQUIREMENTS.md** - Cluster requirements
9. **docs/NETWORKING.md** - Network configuration guide
10. **docs/AIR-GAPPED-DEPLOYMENT.md** - Air-gapped guide

---

## Verification Steps

1. **Local Testing (kind)**
   ```bash
   kind create cluster --name es1-test
   ./scripts/es1-install.sh --provider local --customer test
   ./scripts/es1-status.sh
   ```

2. **Cloud Testing (GKE)**
   ```bash
   cd terraform/environments/gcp-dev && terraform apply
   ./scripts/es1-install.sh --provider gcp --customer beam --license-key "$KEY"
   ./scripts/es1-status.sh
   ```

3. **Air-Gapped Simulation**
   ```bash
   # Disable internet access in kind, pre-load images
   ./scripts/airgap/load-images.sh
   ./scripts/es1-install.sh --provider local --customer test --airgap
   ```

---

## GitHub CI/CD Integration

### Repository Setup

```
GitHub Organization: 1enterprisesight (or your org)
├── es1-platform              # Main platform source code
├── es1-platform-installer    # This installer repo
└── es1-platform-images       # Container image builds (optional)
```

### GitHub Actions Workflows

```yaml
# .github/workflows/helm-test.yml
name: Helm Chart Testing
on:
  push:
    branches: [main]
    paths: ['charts/**']
  pull_request:
    paths: ['charts/**']

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-helm@v3
      - run: helm lint charts/es1-infrastructure
      - run: helm lint charts/es1-platform

  template:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-helm@v3
      - run: |
          helm template es1-infra charts/es1-infrastructure \
            -f charts/es1-infrastructure/values.yaml
          helm template beam charts/es1-platform \
            -f examples/customers/beam/values-platform.yaml \
            --set customer.name=beam

  kind-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: helm/kind-action@v1
      - run: ./scripts/es1-install.sh --provider local --customer test-ci
      - run: ./scripts/es1-status.sh --wait 300
```

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Package Helm charts
      - uses: azure/setup-helm@v3
      - run: |
          helm package charts/es1-infrastructure
          helm package charts/es1-platform

      # Create GitHub release with chart artifacts
      - uses: softprops/action-gh-release@v1
        with:
          files: |
            es1-infrastructure-*.tgz
            es1-platform-*.tgz
          generate_release_notes: true

      # Optional: Push to Helm repository (OCI registry)
      - run: |
          helm push es1-infrastructure-*.tgz oci://ghcr.io/1enterprisesight/charts
          helm push es1-platform-*.tgz oci://ghcr.io/1enterprisesight/charts
```

### Container Image Registry

```yaml
# All ES1 Platform images stored in GitHub Container Registry
images:
  platform-manager-api: ghcr.io/1enterprisesight/platform-manager-api
  platform-manager-ui: ghcr.io/1enterprisesight/platform-manager-ui
  krakend: ghcr.io/1enterprisesight/krakend
  agent-router: ghcr.io/1enterprisesight/agent-router
  crewai-service: ghcr.io/1enterprisesight/crewai-service
  autogen-service: ghcr.io/1enterprisesight/autogen-service

# Third-party images (pulled from public registries or mirrored)
external_images:
  postgresql: docker.io/bitnami/postgresql:15
  redis: docker.io/bitnami/redis:7
  prometheus: quay.io/prometheus/prometheus:v2.48.0
  grafana: docker.io/grafana/grafana:10.2.0
  airflow: docker.io/apache/airflow:2.8.0
  ollama: docker.io/ollama/ollama:latest
```

---

## Additional Considerations

### 1. Secrets Management

```yaml
# Option A: Kubernetes Secrets (default)
# Secrets are created by Helm from values or --set flags
postgresql:
  auth:
    existingSecret: "es1-postgresql-secret"

# Option B: External Secrets Operator (enterprise)
# Sync from HashiCorp Vault, AWS Secrets Manager, etc.
externalSecrets:
  enabled: true
  secretStore:
    name: vault-backend
    kind: ClusterSecretStore
```

### 2. Backup & Restore

```bash
# scripts/es1-backup.sh
# Backup all PVCs using Velero or native tools

# PostgreSQL backup
kubectl exec -n es1-infrastructure es1-postgresql-0 -- \
  pg_dumpall -U postgres > backup-$(date +%Y%m%d).sql

# Redis backup (RDB snapshot)
kubectl exec -n es1-infrastructure es1-redis-master-0 -- \
  redis-cli BGSAVE

# Full PVC backup with Velero
velero backup create es1-backup-$(date +%Y%m%d) \
  --include-namespaces es1-infrastructure,beam-platform
```

### 3. Rollback Strategy

```bash
# Helm rollback to previous release
helm rollback es1-infra 1 -n es1-infrastructure
helm rollback beam-platform 1 -n beam-platform

# View release history
helm history es1-infra -n es1-infrastructure
```

### 4. Database Migrations

```yaml
# Platform Manager handles migrations on startup
platform-manager:
  api:
    migrations:
      enabled: true
      runOnStartup: true
    initContainers:
      - name: wait-for-db
        image: busybox
        command: ['sh', '-c', 'until nc -z postgresql 5432; do sleep 1; done']
```

### 5. Monitoring & Alerting

```yaml
# Alertmanager configuration in monitoring chart
alertmanager:
  enabled: true
  config:
    receivers:
      - name: 'slack'
        slack_configs:
          - channel: '#es1-alerts'
            api_url: '$SLACK_WEBHOOK_URL'
    route:
      receiver: 'slack'
      group_by: ['alertname', 'namespace']
```

### 6. Centralized Logging

```yaml
# Optional: EFK/Loki stack
logging:
  enabled: false  # Enable if needed
  loki:
    enabled: true
    persistence:
      size: 50Gi
  promtail:
    enabled: true
```

### 7. Resource Quotas

```yaml
# Per-namespace resource limits
resourceQuotas:
  infrastructure:
    hard:
      requests.cpu: "16"
      requests.memory: "64Gi"
      limits.cpu: "32"
      limits.memory: "128Gi"
  platform:
    hard:
      requests.cpu: "8"
      requests.memory: "32Gi"
      limits.cpu: "16"
      limits.memory: "64Gi"
```

### 8. Version Compatibility Matrix

| Installer Version | Infrastructure Chart | Platform Chart | K8s Version |
|-------------------|---------------------|----------------|-------------|
| 1.0.0             | 1.0.0               | 1.0.0          | 1.25-1.29   |
| 1.1.0             | 1.1.0               | 1.1.0          | 1.26-1.30   |

### 9. License Server Integration

```yaml
# License validation modes
license:
  # Online: Validate against license server
  mode: online
  serverUrl: "https://license.es1platform.com/v1/validate"

  # Offline: Use embedded license file (for air-gapped)
  # mode: offline
  # offlineLicenseFile: "/etc/es1/license.key"

  # Grace period if license server unreachable
  gracePeriodDays: 7
```

### 10. Multi-Customer on Same Cluster

```
Cluster: es1-production
├── Namespace: es1-infrastructure     (shared)
├── Namespace: beam-platform          (customer 1)
├── Namespace: polygraf-platform      (customer 2)
└── Namespace: rimbal-platform        (customer 3)

# Each customer has isolated:
# - Platform services
# - License keys
# - Branding
# - Ingress/domains

# Shared infrastructure:
# - PostgreSQL (separate databases per customer)
# - Redis (separate key prefixes)
# - Prometheus/Grafana
```

---

## Progress Tracking

### State Management

To survive context loss, we maintain:

1. **This Plan Document** - Stored in:
   - `/Users/michaelreed/projects/ES1-platform/docs/KUBERNETES-PACKAGING-PLAN.md`
   - `es1-platform-installer/docs/ARCHITECTURE.md`

2. **Implementation Checklist** - Track in GitHub Issues or Project board

3. **Version Control** - All changes committed to git with meaningful messages

4. **Release Notes** - CHANGELOG.md updated with each release

### Checklist File

```markdown
# Implementation Progress (update as we go)

## Phase 1: Repository Setup
- [ ] Create es1-platform-installer repo on GitHub
- [ ] Initialize with directory structure
- [ ] Set up GitHub Actions workflows
- [ ] Configure branch protection rules

## Phase 2: Infrastructure Chart
- [ ] Create es1-infrastructure Chart.yaml
- [ ] Configure PostgreSQL dependency
- [ ] Configure Redis dependency
- [ ] Add monitoring stack
- [ ] Add Airflow
- [ ] Add Ollama, MLflow, n8n, Langflow, Langfuse
- [ ] Test on kind cluster

## Phase 3: Platform Chart
- [ ] Create es1-platform Chart.yaml
- [ ] Create KrakenD sub-chart
- [ ] Create platform-manager sub-chart
- [ ] Create agent services sub-charts
- [ ] Add license validation
- [ ] Add branding ConfigMap
- [ ] Test cross-namespace access

## Phase 4: Integration Testing
- [ ] Full stack deployment on kind
- [ ] Network policies verified
- [ ] Customer example: BEAM
- [ ] Customer example: Polygraf
- [ ] Air-gapped simulation test

## Phase 5: Cloud Testing
- [ ] GKE deployment test
- [ ] EKS deployment test (optional)
- [ ] AKS deployment test (optional)

## Phase 6: Documentation
- [ ] INSTALLATION.md
- [ ] UPGRADE.md
- [ ] AIR-GAPPED-DEPLOYMENT.md
- [ ] CLUSTER-REQUIREMENTS.md
- [ ] NETWORKING.md

## Phase 7: Release
- [ ] First release tagged (v1.0.0)
- [ ] Helm charts published to OCI registry
- [ ] Customer deployment validated
```

---

## First Steps After Plan Approval

1. **Save this plan to ES1-platform repo**
   ```bash
   # Copy plan to docs directory
   cp /Users/michaelreed/.claude/plans/bright-skipping-barto.md \
      /Users/michaelreed/projects/ES1-platform/docs/KUBERNETES-PACKAGING-PLAN.md

   # Commit to git
   git add docs/KUBERNETES-PACKAGING-PLAN.md
   git commit -m "Add Kubernetes packaging plan for Phase 4"
   git push
   ```

2. **Create es1-platform-installer repository on GitHub**
   ```bash
   gh repo create 1enterprisesight/es1-platform-installer --private --description "ES1 Platform Kubernetes Installer"
   ```

3. **Initialize repository structure**
   - Create directory skeleton
   - Set up GitHub Actions
   - Create initial Chart.yaml files

4. **Begin Phase 2: Infrastructure Chart development**

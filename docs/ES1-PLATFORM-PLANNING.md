# ES1 Platform - Comprehensive Planning Document

**Version:** 1.0
**Last Updated:** 2026-01-24
**Project Location:** `/Users/michaelreed/projects/ES1-platform`
**GitHub:** `1enterprisesight/ES1-platform`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Vision & Goals](#2-project-vision--goals)
3. [Current State Analysis](#3-current-state-analysis)
4. [Architecture Design](#4-architecture-design)
5. [Component Inventory](#5-component-inventory)
6. [Technology Stack](#6-technology-stack)
7. [Namespace & Licensing Strategy](#7-namespace--licensing-strategy)
8. [Air-Gapped Deployment Requirements](#8-air-gapped-deployment-requirements)
9. [UI/UX Requirements](#9-uiux-requirements)
10. [Development Roadmap](#10-development-roadmap)
11. [Key Technical Decisions](#11-key-technical-decisions)
12. [Quick Reference](#12-quick-reference)

---

## 1. Executive Summary

ES1 Platform is an enterprise composable AI platform designed to provide a unified management interface for all infrastructure components. The system is built with:

- **API-first architecture** with clear frontend/backend separation
- **Component/module-based design** supporting plugins and extensibility
- **Full containerization** for deployment on any Kubernetes cluster
- **Air-gapped capability** - no external cloud dependencies required
- **Modern UI** for complete platform management

### Core Principle
The entire system must function completely within any Kubernetes cluster environment without relying on external or cloud-specific technology.

---

## 2. Project Vision & Goals

### Primary Goals

1. **Unified Management UI** - Single interface to manage all ES1 platform components:
   - KrakenD API Gateway configuration
   - Airflow DAG management and endpoint exposure
   - Langflow flow management
   - Langfuse observability
   - n8n workflow automation
   - Future AI components

2. **API Gateway Management** - Central hub for:
   - Exposing internal services via KrakenD
   - Managing API endpoints for Airflow DAGs
   - Configuring rate limiting, authentication, CORS
   - Version-controlled configuration with rollback

3. **Enterprise-Ready Deployment**:
   - Works in air-gapped environments
   - Deployable to GKE, EKS, AKS, or any K8s cluster
   - License validation via namespace separation
   - Complete data privacy and security

4. **Extensibility** - Plugin architecture to add:
   - New AI/ML tools as they emerge
   - Custom integrations
   - Additional workflow engines

### Non-Goals (Out of Scope)
- Cloud-specific features (GCP Pub/Sub, AWS SQS, etc.)
- External API dependencies during runtime
- Features requiring internet connectivity

---

## 3. Current State Analysis

### What's Built (Production-Ready)

| Component | Status | Files | Description |
|-----------|--------|-------|-------------|
| **Gateway Manager API** | Complete | 45 .py files | FastAPI backend with full CRUD |
| **Gateway Manager UI** | Complete | 43 .ts/.tsx files | React 19 + TailwindCSS frontend |
| **KrakenD Gateway** | Complete | 4 files | API Gateway with config management |
| **PostgreSQL** | Complete | 5 SQL init scripts | pgvector-enabled database |
| **Redis** | Complete | 2 files | Caching and Celery broker |
| **Docker Compose** | Complete | 6 compose files | Modular service composition |
| **Kubernetes Manifests** | Complete | 20 files | Kustomize overlays for local/GKE/EKS/AKS |
| **CI/CD Pipeline** | Complete | 1 workflow | GitHub Actions multi-arch builds |

### Uncommitted Work In Progress

The following files have been created but not yet committed:

**New Services:**
- `docker-compose.airflow.yml` - Airflow with CeleryExecutor
- `docker-compose.gateway-manager.yml` - Gateway Manager API + UI
- `docker-compose.langflow.yml` - Langflow LLM flow builder
- `docker-compose.langfuse.yml` - LLM observability

**Database Init Scripts:**
- `infrastructure/postgres/init/02-airflow.sql`
- `infrastructure/postgres/init/03-langfuse.sql`
- `infrastructure/postgres/init/04-langflow.sql`
- `infrastructure/postgres/init/05-gateway-manager.sql`

**Modified Files:**
- `Makefile` - New targets for services
- `docker-compose.yml` - Updated base config
- `services/krakend/config/krakend.json` - Service endpoints
- `services/krakend/config/settings/service-discovery.json`

### Gateway Manager Assessment

**Decision:** The existing gateway-manager has solid backend patterns but the UI is not user-friendly or extendable enough. We will:
- Build a **new ES1 Platform Manager** service
- **Migrate backend capabilities** from gateway-manager (keep patterns, database schema)
- **Build fresh UI** with modern, event-driven design

### Gateway Manager Database Schema

8 tables with full audit trail capability:

```
discovered_resources  - Resources from Airflow, K8s, Langflow
config_versions       - Configuration version history
exposures            - Tagged resources with gateway config
deployments          - Deployment tracking with rollback
approvals            - Approval workflow
event_log            - Full audit trail
exposure_changes     - Change management workflow
branding_config      - White-label support
```

### API Endpoints (Gateway Manager)

10 routers providing:
- `/api/v1/resources` - Resource discovery from external systems
- `/api/v1/exposures` - Exposure CRUD operations
- `/api/v1/exposure-changes` - Change management workflow
- `/api/v1/deployments` - Deployment tracking
- `/api/v1/integrations` - External system integrations
- `/api/v1/metrics` - Health and metrics
- `/api/v1/events` - Event log
- `/api/v1/gateway` - KrakenD operations
- `/api/v1/config-versions` - Version history
- `/api/v1/branding` - White-label configuration

---

## 4. Architecture Design

### High-Level Architecture

```
                           EXTERNAL USERS
                                 |
                                 v
                        +----------------+
                        |    KrakenD     |
                        |  API Gateway   |
                        +----------------+
                                 |
        +----------+------------+------------+-----------+
        |          |            |            |           |
        v          v            v            v           v
   +--------+ +---------+ +----------+ +--------+ +------+
   |Airflow | |Langflow | |Langfuse  | |  n8n   | |Future|
   |  API   | |  API    | |   API    | |  API   | | APIs |
   +--------+ +---------+ +----------+ +--------+ +------+
        |          |            |            |
        +----------+------------+------------+
                        |
                        v
             +--------------------+
             |  ES1 Platform      |
             |  Manager API       |
             +--------------------+
                        |
                        v
             +--------------------+
             |  ES1 Platform      |
             |  Manager UI        |
             +--------------------+
                        |
                        v
                    ADMIN USER
```

### Traffic Flow

```
External Customer Traffic:
    Customer Apps → KrakenD → [Airflow/Langflow/n8n APIs]
                              (logged, rate-limited, secured)

ES1 Platform Admin Traffic:
    Admin UI → ES1 Platform Manager API (direct, internal)
                    |
                    ├── Manages KrakenD configs
                    ├── Manages Airflow DAGs
                    ├── Manages Langflow flows
                    └── etc.

Inter-Component Traffic (for visibility):
    Airflow DAG → KrakenD → Langflow API
                  (so admins can see the call in observability)
```

### Component Communication

```
ES1 Platform Manager UI (React)
    |
    | REST API calls + SSE/WebSocket for real-time
    v
ES1 Platform Manager API (FastAPI)
    |
    |-- PostgreSQL (config, versions, audit)
    |-- Redis (caching, sessions)
    |-- KrakenD API (config deployment)
    |-- Airflow API (DAG discovery)
    |-- Langflow API (flow discovery)
    |-- Langfuse API (observability)
    |-- n8n API (workflow discovery)
    |-- Kubernetes API (pod/configmap management)
```

### Deployment Modes

| Mode | Use Case | How It Works |
|------|----------|--------------|
| **Docker** | Local development | File-based config, HTTP health checks |
| **Kubernetes** | Production | ConfigMap-based config, K8s API for rollouts |

The `DeploymentEngine` class auto-detects the environment and uses the appropriate backend.

---

## 5. Component Inventory

### Base Infrastructure (Standard Namespace)

| Component | Version | Port | Purpose |
|-----------|---------|------|---------|
| PostgreSQL | 16 (pgvector) | 5432 | Primary database |
| Redis | 7-alpine | 6379 | Cache + Celery broker |
| KrakenD | 2.6 | 8080/9091 | API Gateway |

### AI/ML Stack (Standard Namespace)

| Component | Version | Port | Purpose |
|-----------|---------|------|---------|
| Airflow | 2.8.1 | 8081 | Workflow orchestration |
| Langflow | latest | 7860 | LLM flow builder |
| Langfuse | latest | 3000 | LLM observability |
| n8n | (to add) | 5678 | Workflow automation |

### ES1 Custom Components (ES1 Namespace)

| Component | Version | Port | Purpose |
|-----------|---------|------|---------|
| ES1 Platform Manager API | 1.0.0 | 8000 | Unified backend |
| ES1 Platform Manager UI | 1.0.0 | 3001 | Admin interface |
| License Server | (to build) | TBD | License validation |
| License Validator | (to build) | TBD | License enforcement |

### Future Components to Evaluate

| Component | Category | Air-Gapped Ready | Notes |
|-----------|----------|------------------|-------|
| **Milvus** | Vector DB | Yes | Enterprise scale vectors |
| **Qdrant** | Vector DB | Yes | Lightweight, fast filtering |
| **Ollama** | Model Serving | Yes | Local LLM deployment |
| **vLLM** | Model Serving | Yes | High-throughput inference |
| **MLflow** | MLOps | Yes | Experiment tracking |
| **Kubeflow** | MLOps | Yes | K8s-native ML pipelines |
| **Label Studio** | Data Labeling | Yes | Annotation platform |

---

## 6. Technology Stack

### Backend

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Language** | Python 3.12 | FastAPI, async support, AI ecosystem |
| **Framework** | FastAPI | Async, OpenAPI auto-generation |
| **ORM** | SQLAlchemy 2.0 | Async support, migrations |
| **Validation** | Pydantic | Type safety, settings management |
| **Database** | PostgreSQL 16 | JSON support, pgvector, reliability |
| **Cache** | Redis 7 | Session, cache, Celery broker |

### Frontend

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Framework** | React 19 | Latest features, component model |
| **Language** | TypeScript 5.9 | Type safety |
| **Build** | Vite 7 | Fast HMR, modern bundling |
| **Styling** | TailwindCSS 3.4 | Utility-first, consistent design |
| **Components** | shadcn/ui | Accessible, customizable, we own the code |
| **State** | TanStack Query 5 | Server state, caching |
| **Forms** | React Hook Form 7 | Performance, validation |
| **Routing** | React Router 7 | Modern routing |
| **Icons** | Lucide React | Modern icons, shadcn/ui compatible |

### Real-Time Communication

| Technology | Use Case |
|------------|----------|
| **SSE** | Activity feed, status broadcasts, simple one-way updates |
| **WebSocket** | Long-running processes, interactive features, bidirectional needs |

Both will be implemented - SSE for general real-time updates, WebSocket for processes that need progress tracking or user interaction.

### Infrastructure

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Containers** | Docker | Universal compatibility |
| **Orchestration** | Kubernetes | Production standard |
| **Config Management** | Kustomize | GitOps-friendly overlays |
| **CI/CD** | GitHub Actions | Native GitHub integration |
| **Registry** | GHCR | GitHub integration |

---

## 7. Namespace & Licensing Strategy

### Kubernetes Namespace Architecture

```
Cluster
├── es1-infrastructure      (Standard packages)
│   ├── PostgreSQL
│   ├── Redis
│   └── KrakenD
│
├── es1-platform           (Standard packages)
│   ├── Airflow
│   ├── Langflow
│   ├── Langfuse
│   └── n8n
│
├── es1-core               (ES1 custom - licensed)
│   ├── ES1 Platform Manager API
│   ├── ES1 Platform Manager UI
│   └── License Server
│
└── es1-monitoring         (Future)
    ├── Prometheus
    ├── Grafana
    └── Alertmanager
```

### License Validation Strategy

1. **License Server** - Deployed in `es1-core` namespace
   - Validates license keys
   - Tracks feature entitlements
   - Monitors namespace usage

2. **License Validator** - Sidecar or init container
   - Validates license on service startup
   - Periodic re-validation
   - Fails gracefully if license server unreachable (grace period)

3. **Namespace-Based Enforcement**
   - Standard packages (`es1-platform`) - Free tier
   - ES1 components (`es1-core`) - Licensed features
   - Namespace presence enables/disables features

---

## 8. Air-Gapped Deployment Requirements

### Critical Requirements

1. **No External Network Calls**
   - All container images pre-pulled to local registry
   - No runtime package downloads (pip, npm, etc.)
   - No external API dependencies

2. **Local Model Serving**
   - Ollama for local LLM inference
   - Models bundled in container or mounted as volumes
   - No calls to OpenAI, Anthropic, etc.

3. **Self-Contained Database**
   - PostgreSQL with all extensions compiled in
   - No external data sources required

4. **Local Authentication**
   - LDAP/SAML integration for enterprise SSO
   - No OAuth with external providers
   - Local user database fallback

### Container Image Strategy

```bash
# Build and save images for air-gapped transfer
docker save $(docker images -q) | gzip > es1-platform-images.tar.gz

# Load on air-gapped system
gunzip -c es1-platform-images.tar.gz | docker load
```

### Air-Gapped Deployment Checklist

- [ ] All images tagged and saved
- [ ] Helm charts bundled (if using Helm)
- [ ] Python wheels for all dependencies
- [ ] npm packages cached
- [ ] LLM models downloaded and bundled
- [ ] SSL certificates pre-generated
- [ ] Documentation bundled

---

## 9. UI/UX Requirements

### Design Principles

1. **Simple & User-Friendly** - Intuitive, minimal learning curve, clear actions
2. **Transparent & Event-Driven** - User always knows what the system is doing
3. **Consistent** - Same patterns and components across all modules
4. **Modern & Extendable** - Clean architecture for adding new modules
5. **Accessible** - WCAG 2.1 AA compliance
6. **Dark Mode** - Support for dark/light themes

### Event-Driven UI Architecture

The UI must provide full transparency into system operations:

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER BAR                                                  │
│  [Logo]  [Dashboard] [Gateway] [Workflows] [AI]  [Settings] │
│                                            [Status: ● Live]  │
├─────────────────────────────────────────────────────────────┤
│                                           │ ACTIVITY FEED   │
│  MAIN CONTENT AREA                        │                 │
│                                           │ ● Deployment    │
│  Current module view                      │   started...    │
│  - Clear status indicators                │ ● Config        │
│  - Real-time updates                      │   validated     │
│  - Action buttons with feedback           │ ● Gateway       │
│                                           │   restarting... │
│                                           │ ● Health check  │
│                                           │   passed ✓      │
├─────────────────────────────────────────────────────────────┤
│  STATUS BAR                                                  │
│  [Postgres: ●] [Redis: ●] [KrakenD: ●] [Airflow: ●] ...    │
└─────────────────────────────────────────────────────────────┘
```

#### Real-Time Features
- **WebSocket/SSE connection** for live updates
- **Activity feed** showing all operations in progress
- **Toast notifications** for completed operations
- **Status indicators** for all infrastructure components
- **Progress tracking** for long-running operations (deployments, syncs)

#### Error Handling & Logging
- **Clear error messages** with actionable guidance
- **Error history** accessible from activity feed
- **Debug mode** for detailed logs
- **Copy-to-clipboard** for error details (support tickets)
- **Retry buttons** for failed operations

### Core UI Features

#### Dashboard (Home)
- System health overview (all components at a glance)
- Active operations (what's happening now)
- Recent events (last 24h summary)
- Quick actions (common tasks)
- Alerts/warnings

#### API Gateway Module
- **Endpoints View**: Simple list of all exposed endpoints
  - Status indicator (deployed, pending, error)
  - One-click to view details
  - Quick actions (enable/disable/edit)
- **Resource Discovery**: Auto-discover and expose
  - Clear "Discover" button
  - Simple checkboxes to select what to expose
  - Preview before deploy
- **Deployments**: Version history with rollback
  - Timeline view
  - One-click rollback
  - Diff view between versions

#### Workflow Module
- **Airflow DAGs**
  - List with run status
  - One-click trigger
  - View recent runs
  - Expose as API endpoint
- **n8n Workflows**
  - List with status
  - Trigger/pause controls
  - Execution history

#### AI Module
- **Langflow Flows**
  - List of available flows
  - Test/run flow
  - Expose as API endpoint
- **Langfuse Observability**
  - Trace overview
  - Cost summary
  - Performance metrics

#### Settings Module
- **System**: Component URLs, health checks
- **Integrations**: Connection settings for each service
- **Branding**: Logo, colors, theme
- **Users**: User management (Phase 5)
- **Audit Log**: Full history of all changes

---

## 10. Development Roadmap

### Phase 1: ES1 Platform Manager Foundation (CURRENT)
**Goal:** Create new ES1 Platform Manager with proper architecture

**Decision Made:** Build new `es1-platform-manager` service. Migrate backend capabilities from gateway-manager, but build fresh UI.

#### 1.1 Backend Architecture
- [ ] Create `services/es1-platform-manager/api/` structure
- [ ] Set up modular architecture:
  ```
  api/app/
  ├── core/           # Shared: config, db, auth, events
  ├── modules/
  │   ├── gateway/    # Migrate from gateway-manager
  │   ├── airflow/    # Airflow management
  │   ├── langflow/   # Langflow management
  │   ├── observability/ # Langfuse integration
  │   └── automation/ # n8n management
  └── main.py
  ```
- [ ] Implement event bus for real-time updates
- [ ] Set up WebSocket support for live status
- [ ] Migrate gateway database schema
- [ ] Create unified logging service

#### 1.2 New UI Design System
- [ ] Create `services/es1-platform-manager/ui/` structure
- [ ] Design system requirements:
  - Simple and user-friendly
  - Modern, extendable component library
  - Consistent look and feel
  - Event-driven with real-time status
  - Full transparency (what is the system doing?)
  - Clear error/failure logging
- [ ] Component library:
  ```
  ui/src/
  ├── design-system/
  │   ├── components/   # Base components (Button, Card, etc.)
  │   ├── layouts/      # Page layouts
  │   └── themes/       # Theming support
  ├── modules/
  │   ├── dashboard/    # Unified system overview
  │   ├── gateway/      # API gateway management
  │   ├── workflows/    # Airflow + n8n
  │   └── ai/           # Langflow + Langfuse
  └── shared/
      ├── hooks/        # Shared React hooks
      ├── contexts/     # Event bus, auth, theme
      └── utils/        # Helpers
  ```

#### 1.3 Event-Driven Architecture
- [ ] Backend event emitter (SSE or WebSocket)
- [ ] Frontend event listener/subscriber
- [ ] Activity feed with real-time updates
- [ ] Toast notifications for operations
- [ ] System status indicators

### Phase 2: Module Implementation
**Goal:** Implement each management module

#### 2.1 Gateway Module
- [ ] Migrate KrakenD config management
- [ ] Resource discovery (keep existing patterns)
- [ ] Exposure management (simplified UI)
- [ ] Deployment with rollback
- [ ] Real-time deployment status

#### 2.2 Workflow Module
- [ ] Airflow DAG management
  - List/view DAGs
  - Trigger DAGs
  - View DAG runs and logs
  - Expose DAG endpoints via gateway
- [ ] n8n workflow management
  - List/view workflows
  - Trigger workflows
  - View execution history

#### 2.3 AI Module
- [ ] Langflow integration
  - List/view flows
  - Test flows
  - Expose flow endpoints
- [ ] Langfuse integration
  - View traces
  - Cost tracking
  - Performance metrics

### Phase 3: Integration & Polish
**Goal:** Connect everything together

- [ ] Cross-module workflows
- [ ] Unified search across all modules
- [ ] Dashboard widgets for each module
- [ ] Bulk operations
- [ ] Export/import configurations

### Phase 4: Kubernetes & Production
**Goal:** Production-ready K8s deployment

- [ ] K8s manifests for es1-platform-manager
- [ ] Helm charts (optional)
- [ ] Production secrets management
- [ ] Health checks and probes
- [ ] Horizontal pod autoscaling
- [ ] Backup/restore procedures

### Phase 5: Enterprise Features
**Goal:** Enterprise-ready platform

- [ ] License server implementation
- [ ] License validator sidecar
- [ ] RBAC implementation
- [ ] SSO integration (SAML/LDAP)
- [ ] Multi-tenant support
- [ ] Audit compliance reports

### Phase 6: AI/ML Expansion
**Goal:** Complete AI platform

- [ ] Vector database integration (Milvus/Qdrant)
- [ ] Model serving (Ollama/vLLM)
- [ ] MLflow integration
- [ ] RAG pipeline templates
- [ ] Model registry

---

## 11. Key Technical Decisions

### Decision Log

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| D1 | FastAPI for backend | Async, OpenAPI, Python ecosystem | Initial |
| D2 | React 19 for frontend | Modern, component-based, ecosystem | Initial |
| D3 | PostgreSQL with pgvector | Vector support, JSON, reliability | Initial |
| D4 | KrakenD over Kong/Envoy | Lightweight, declarative, no DB required | Initial |
| D5 | Kustomize over Helm | Simpler, GitOps-friendly, no templating | Initial |
| D6 | CeleryExecutor for Airflow | Redis reuse, simpler than K8s executor | Initial |
| D7 | Modular Docker Compose | Flexible component selection | Initial |
| D8 | shadcn/ui for components | Accessible, customizable, we own code | 2026-01-24 |
| D9 | SSE + WebSocket for real-time | SSE for broadcasts, WS for interactive | 2026-01-24 |
| D10 | New Platform Manager over refactor | Fresh UI, better architecture | 2026-01-24 |

### Pending Decisions

| ID | Question | Options | Status |
|----|----------|---------|--------|
| P1 | Vector database choice | Milvus vs Qdrant vs pgvector | Evaluate |
| P2 | Model serving approach | Ollama vs vLLM vs Triton | Evaluate |
| P3 | Service mesh | Istio vs Linkerd vs none | Evaluate |
| P4 | Secrets management | Vault vs K8s Secrets vs Sealed Secrets | Evaluate |

---

## 12. Quick Reference

### Development Commands

```bash
# Navigate to project
cd ~/projects/ES1-platform

# Start full stack locally
make up-full

# Check logs
make logs

# View Gateway Manager logs
make logs-gateway-manager

# Stop everything
make down

# Check status
make status
```

### Service URLs (Local Development)

| Service | URL | Credentials |
|---------|-----|-------------|
| KrakenD API | http://localhost:8080 | - |
| KrakenD Metrics | http://localhost:9091 | - |
| ES1 Platform Manager API | http://localhost:8000/docs | - |
| ES1 Platform Manager UI | http://localhost:3001 | - |
| Airflow | http://localhost:8081 | airflow/airflow |
| Langflow | http://localhost:7860 | admin/admin |
| Langfuse | http://localhost:3000 | See .env |
| PostgreSQL | localhost:5432 | es1_user/es1_dev_password |
| Redis | localhost:6379 | - |

### Git Status

```bash
# Current branch: main
# Remote: origin (1enterprisesight/ES1-platform)
# Commits: 3 (Initial + 2 fixes)
# Uncommitted: 10+ files (services, compose files, SQL scripts)
```

### File Locations

| Item | Path |
|------|------|
| Project Root | `~/projects/ES1-platform` |
| Planning Doc | `~/projects/ES1-platform/docs/ES1-PLATFORM-PLANNING.md` |
| Gateway Manager (reference) | `~/projects/ES1-platform/services/gateway-manager/` |
| ES1 Platform Manager (new) | `~/projects/ES1-platform/services/es1-platform-manager/` |
| Docker Compose Files | `~/projects/ES1-platform/docker-compose*.yml` |
| K8s Manifests | `~/projects/ES1-platform/k8s/` |

---

## Session Recovery Notes

If a session crashes, reference this document to understand:

1. **Project location**: `~/projects/ES1-platform`
2. **Current phase**: Phase 1 - ES1 Platform Manager Foundation
3. **Key decision**: Building new `es1-platform-manager` service (not refactoring gateway-manager)
4. **Immediate next steps**:
   - Create the new es1-platform-manager service structure
   - Set up backend with modular architecture
   - Set up UI with shadcn/ui and event-driven design

### Key Resources

- GitHub Repo: https://github.com/1enterprisesight/ES1-platform
- Container Registry: ghcr.io/1enterprisesight/es1-platform
- Planning Doc: `docs/ES1-PLATFORM-PLANNING.md` (this file)

---

*This document should be updated as the project progresses. Keep it in sync with actual implementation.*

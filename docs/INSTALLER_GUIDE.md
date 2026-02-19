# ES1 Platform - Installer Guide

This document describes the platform structure, configurable variables, and deployment considerations for the ES1 Platform installer.

## Architecture Overview

```
ES1 Platform
├── Infrastructure Layer
│   ├── postgres          (Main PostgreSQL - port 5432)
│   ├── aiml-postgres     (AI/ML PostgreSQL with pgvector - port 5433)
│   ├── redis             (Cache/message broker - port 6379)
│   └── krakend           (API Gateway - port 8080)
│
├── Platform Services
│   ├── es1-platform-manager-api  (Backend API - port 8000)
│   └── es1-platform-manager-ui   (Frontend UI - port 3001)
│
├── Agent Frameworks
│   ├── agent-router      (Unified agent API - port 8102)
│   ├── crewai            (CrewAI API - port 8100)
│   ├── crewai-studio     (CrewAI visual builder - port 8501)
│   ├── autogen           (AutoGen API - port 8101)
│   └── autogen-studio    (AutoGen visual builder - port 8502)
│
├── AI/ML Services
│   ├── ollama            (Local LLM server - port 11434)
│   ├── ollama-webui      (Open WebUI - port 3010)
│   ├── mlflow            (Model registry - port 5050)
│   ├── langflow          (Visual LLM flows - port 7860)
│   └── langfuse          (LLM observability - port 3000)
│
├── Workflow Services
│   ├── airflow           (DAG orchestration - port 8081)
│   └── n8n               (Workflow automation - port 5678)
│
└── Monitoring
    ├── prometheus        (Metrics collection - port 9090)
    └── grafana           (Dashboards - port 3002)
```

## Docker Compose Files

The platform uses layered compose files for modularity:

| File | Description | Required |
|------|-------------|----------|
| `docker-compose.yml` | Base infrastructure (postgres, redis, krakend) | Yes |
| `docker-compose.aiml.yml` | AI/ML stack (aiml-postgres, ollama, mlflow) | Yes |
| `docker-compose.agents.yml` | Agent frameworks (crewai, autogen, router) | Yes |
| `docker-compose.es1-platform-manager.yml` | Platform Manager (API + UI) | Yes |
| `docker-compose.monitoring.yml` | Prometheus + Grafana | Recommended |
| `docker-compose.airflow.yml` | Apache Airflow | Optional |
| `docker-compose.n8n.yml` | n8n workflow automation | Optional |
| `docker-compose.langflow.yml` | Langflow visual builder | Optional |
| `docker-compose.langfuse.yml` | LLM observability | Optional |
| `docker-compose.crewai-studio.yml` | CrewAI visual builder | Optional |
| `docker-compose.autogen-studio.yml` | AutoGen visual builder | Optional |
| `docker-compose.db-migrate.yml` | Database migrations | For migrations |

### Deployment Command Example

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.aiml.yml \
  -f docker-compose.agents.yml \
  -f docker-compose.es1-platform-manager.yml \
  -f docker-compose.monitoring.yml \
  -f docker-compose.airflow.yml \
  -f docker-compose.n8n.yml \
  -f docker-compose.langfuse.yml \
  -f docker-compose.crewai-studio.yml \
  -f docker-compose.autogen-studio.yml \
  up -d
```

## Environment Variables

All credentials and URLs are configurable via environment variables for customer branding and security.

### Database Credentials

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `engine_platform` | Main database name |
| `POSTGRES_USER` | `engine_user` | Main database user |
| `POSTGRES_PASSWORD` | `engine_dev_password` | Main database password |
| `AIML_POSTGRES_DB` | `aiml` | AI/ML database name |
| `AIML_POSTGRES_USER` | `aiml_user` | AI/ML database user |
| `AIML_POSTGRES_PASSWORD` | `aiml_dev_password` | AI/ML database password |

### Service Credentials

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_ADMIN_USER` | `admin` | Grafana admin username |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | Grafana admin password |
| `GRAFANA_ROOT_URL` | `http://localhost:3002` | Grafana public URL |
| `N8N_DEFAULT_USER_EMAIL` | `admin@engine.local` | n8n default user email |
| `N8N_DEFAULT_USER_PASSWORD` | `Engineadmin!` | n8n default user password (must contain uppercase) |
| `N8N_DEFAULT_USER_FIRST_NAME` | `Engine` | n8n user first name (branding) |
| `N8N_DEFAULT_USER_LAST_NAME` | `Admin` | n8n user last name |
| `_AIRFLOW_WWW_USER_USERNAME` | `airflow` | Airflow admin username |
| `_AIRFLOW_WWW_USER_PASSWORD` | `airflow` | Airflow admin password |

### Langfuse Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGFUSE_URL` | `http://localhost:3000` | Langfuse public URL |
| `LANGFUSE_NEXTAUTH_SECRET` | dev secret | Auth secret (generate: `openssl rand -base64 32`) |
| `LANGFUSE_SALT` | dev salt | Password salt (generate: `openssl rand -base64 32`) |
| `LANGFUSE_TELEMETRY_ENABLED` | `false` | Enable/disable telemetry |
| `LANGFUSE_INIT_USER_EMAIL` | `admin@engine.local` | Default admin email |
| `LANGFUSE_INIT_USER_NAME` | `Engine Admin` | Default admin display name |
| `LANGFUSE_INIT_USER_PASSWORD` | `Engineadmin!` | Default admin password |
| `LANGFUSE_INIT_ORG_NAME` | `Engine Platform` | Organization name (branding) |
| `LANGFUSE_INIT_PROJECT_NAME` | `Engine Platform` | Default project name |
| `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` | dev key | API public key for integrations |
| `LANGFUSE_INIT_PROJECT_SECRET_KEY` | dev key | API secret key for integrations |

### UI Runtime Configuration

The Platform Manager UI uses runtime configuration injection. At container startup, `docker-entrypoint.sh` generates `/config.js` with service URLs and `/etc/nginx/conf.d/default.conf` for proxy routing.

#### Internal Service Hosts (nginx proxy targets)

These configure where nginx proxies API requests. In Kubernetes, set these to the internal service names.

| Variable | Default | Description |
|----------|---------|-------------|
| `PLATFORM_API_HOST` | `platform-manager-api` | Platform API service hostname |
| `PLATFORM_API_PORT` | `8000` | Platform API service port |
| `AGENT_ROUTER_HOST` | `agent-router` | Agent Router service hostname |
| `AGENT_ROUTER_PORT` | `8102` | Agent Router service port |

#### External Service URLs (opened in browser)

These URLs are used when the UI opens external services in new browser tabs. In Kubernetes, set these to the Ingress or LoadBalancer URLs.

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_URL` | `http://localhost:3002` | Grafana URL for UI links |
| `PROMETHEUS_URL` | `http://localhost:9090` | Prometheus URL |
| `LANGFLOW_URL` | `http://localhost:7860` | Langflow URL |
| `MLFLOW_URL` | `http://localhost:5050` | MLflow URL |
| `N8N_URL` | `http://localhost:5678` | n8n URL |
| `AIRFLOW_URL` | `http://localhost:8081` | Airflow URL |
| `LANGFUSE_URL` | `http://localhost:3000` | Langfuse URL |
| `CREWAI_URL` | `http://localhost:8100` | CrewAI API URL |
| `CREWAI_STUDIO_URL` | `http://localhost:8501` | CrewAI Studio URL |
| `AUTOGEN_URL` | `http://localhost:8101` | AutoGen API URL |
| `AUTOGEN_STUDIO_URL` | `http://localhost:8502` | AutoGen Studio URL |
| `OPEN_WEBUI_URL` | `http://localhost:3010` | Open WebUI (Ollama chat) URL |

### UI Feature Flags

Feature flags control which integrations are shown in the UI. Set to `"false"` to hide services that aren't deployed.

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_N8N` | `true` | Show n8n workflow automation links |
| `ENABLE_LANGFLOW` | `true` | Show Langflow visual builder links |
| `ENABLE_CREWAI_STUDIO` | `true` | Show CrewAI Studio button |
| `ENABLE_AUTOGEN_STUDIO` | `true` | Show AutoGen Studio button |
| `ENABLE_LANGFUSE` | `true` | Show Langfuse observability links |
| `ENABLE_MLFLOW` | `true` | Show MLflow model registry links |

## Database Migrations

The platform uses versioned SQL migrations with a Python orchestration layer.

### Migration Structure

```
infrastructure/db-migrate/
├── Dockerfile
├── migrate.py              # Migration runner
├── lib/
│   ├── version_tracker.py  # Tracks applied migrations
│   ├── executor.py         # Executes SQL files
│   └── seed_loader.py      # Loads seed data
├── migrations/
│   ├── postgres/           # Main database migrations
│   │   ├── V001__*.sql
│   │   └── V002__*.sql
│   └── aiml-postgres/      # AI/ML database migrations
│       ├── V001__*.sql
│       └── ...
└── seeds/
    ├── postgres/
    │   └── reference/      # Always applied
    └── aiml-postgres/
        ├── reference/      # Always applied (entity types, agents)
        └── sample/         # Demo data only
```

### Running Migrations

```bash
# Run all migrations with reference seeds
docker compose -f docker-compose.yml -f docker-compose.aiml.yml \
  -f docker-compose.db-migrate.yml run --rm db-migrate --all-databases --seed=reference

# Dry run (show what would be executed)
docker compose -f docker-compose.yml -f docker-compose.aiml.yml \
  -f docker-compose.db-migrate.yml run --rm db-migrate --dry-run

# Check migration status
docker compose -f docker-compose.yml -f docker-compose.aiml.yml \
  -f docker-compose.db-migrate.yml run --rm db-migrate --status
```

### Seed Modes

| Mode | Description |
|------|-------------|
| `none` | No seed data |
| `reference` | Entity types, relationship types, template agents (production) |
| `sample` | Reference + demo knowledge bases, sample data (development) |
| `full` | All seed data |

## Pre-seeded Data

### Template Agents (17 total)

**CrewAI Agents (9):**
- Research Team: Researcher, Writer, Editor
- Code Review Team: Code Reviewer, Security Analyst, Documentation Writer
- Customer Support Team: Intake Specialist, Technical Support, Quality Assurance

**AutoGen Agents (8):**
- Code Assistant, User Proxy
- Debate Team: Proponent, Opponent, Moderator
- Brainstorm Team: Ideator, Critic, Synthesizer

### Starter Knowledge Base

A default "documents" knowledge base is created for document uploads.

## Service Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                     Platform Manager UI                      │
│                        (port 3001)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Platform Manager API                      │
│                        (port 8000)                          │
└─────────────────────────────────────────────────────────────┘
           │                  │                    │
           ▼                  ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│     postgres     │  │   aiml-postgres  │  │      redis       │
│    (port 5432)   │  │    (port 5433)   │  │    (port 6379)   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │      ollama      │
                    │   (port 11434)   │
                    └──────────────────┘
```

## Startup Order

1. **Infrastructure** (postgres, aiml-postgres, redis)
2. **Database Migrations** (db-migrate job)
3. **Core Services** (ollama, platform-manager-api)
4. **Agent Services** (agent-router, crewai, autogen)
5. **UI and Monitoring** (platform-manager-ui, grafana, prometheus)
6. **Optional Services** (airflow, n8n, langfuse, studios)

## Health Checks

All services expose health endpoints:

| Service | Health Endpoint |
|---------|-----------------|
| Platform API | `GET /health` |
| Agent Router | `GET /health` |
| CrewAI | `GET /health` |
| AutoGen | `GET /health` |
| Airflow | `GET /health` |
| n8n | `GET /healthz` |
| Langfuse | `GET /api/public/health` |
| Grafana | `GET /api/health` |

## Post-Install Setup

### Default Credentials

All services have configurable default credentials. Change these for production deployments.

| Service | Username Variable | Password Variable | Defaults |
|---------|-------------------|-------------------|----------|
| **n8n** | `N8N_DEFAULT_USER_EMAIL` | `N8N_DEFAULT_USER_PASSWORD` | `admin@engine.local` / `Engineadmin!` |
| **Langfuse** | `LANGFUSE_INIT_USER_EMAIL` | `LANGFUSE_INIT_USER_PASSWORD` | `admin@engine.local` / `Engineadmin!` |
| **Grafana** | `GRAFANA_ADMIN_USER` | `GRAFANA_ADMIN_PASSWORD` | `admin` / `admin` |
| **Airflow** | `_AIRFLOW_WWW_USER_USERNAME` | `_AIRFLOW_WWW_USER_PASSWORD` | `airflow` / `airflow` |

### Verification Commands

```bash
# Check all services are healthy
docker compose ps

# Check agent registration
curl http://localhost:8102/agents | jq '.agents | length'
# Expected: 17 agents

# Check knowledge bases
docker exec engine-aiml-postgres psql -U aiml_user -d aiml \
  -c "SELECT name FROM rag.knowledge_bases;"

# Check migration status
docker exec engine-postgres psql -U engine_user -d engine_platform \
  -c "SELECT * FROM _schema_migrations;"
```

## Docker Images

### Custom Images (Built from Source)

All custom images are built locally from Dockerfiles for air-gapped deployment support:

| Image | Build Context |
|-------|---------------|
| es1-postgres | `infrastructure/postgres/` |
| es1-aiml-postgres | `infrastructure/aiml-postgres/` |
| es1-redis | `infrastructure/redis/` |
| es1-krakend | `services/krakend/` |
| es1-platform-manager-api | `services/es1-platform-manager/api/` |
| es1-platform-manager-ui | `services/es1-platform-manager/ui/` |
| es1-crewai | `services/agents/crewai/` |
| es1-autogen | `services/agents/autogen/` |
| es1-agent-router | `services/agents/router/` |
| es1-crewai-studio | `services/agents/crewai-studio/` |
| es1-autogen-studio | `services/agents/autogen-studio/` |
| es1-db-migrate | `infrastructure/db-migrate/` |
| es1-mlflow | `infrastructure/mlflow/` |

### Third-Party Images (Pulled from Registry)

For air-gapped deployments, these images must be pulled and pushed to a local registry:

| Image | Version | Purpose |
|-------|---------|---------|
| `ollama/ollama` | latest | Local LLM inference |
| `ghcr.io/open-webui/open-webui` | main | Ollama Web UI |
| `apache/airflow` | 2.8.1-python3.11 | DAG orchestration |
| `langflowai/langflow` | latest | Visual LLM flows |
| `langfuse/langfuse` | 2 | LLM observability |
| `n8nio/n8n` | latest | Workflow automation |
| `prom/prometheus` | v2.51.0 | Metrics collection |
| `grafana/grafana` | 10.4.0 | Dashboards |
| `gcr.io/cadvisor/cadvisor` | v0.49.1 | Container metrics |
| `prom/node-exporter` | v1.7.0 | Host metrics |
| `prometheuscommunity/postgres-exporter` | v0.15.0 | Postgres metrics |
| `oliver006/redis_exporter` | v1.58.0 | Redis metrics |

### Building All Images

```bash
# Build all custom images
docker compose -f docker-compose.yml \
  -f docker-compose.aiml.yml \
  -f docker-compose.agents.yml \
  -f docker-compose.es1-platform-manager.yml \
  -f docker-compose.crewai-studio.yml \
  -f docker-compose.autogen-studio.yml \
  build

# Tag and push to private registry (for air-gapped deployment)
REGISTRY=your-registry.example.com/es1
for img in postgres aiml-postgres redis krakend platform-manager-api platform-manager-ui crewai autogen agent-router crewai-studio autogen-studio mlflow; do
  docker tag es1-platform-$img:latest $REGISTRY/$img:latest
  docker push $REGISTRY/$img:latest
done
```

## Kubernetes Deployment

For Kubernetes deployment, the installer should:

1. Convert env vars to ConfigMaps/Secrets
2. Create PersistentVolumeClaims for data volumes
3. Run db-migrate as a Job before app deployment
4. Use the same image references

See `k8s/` directory for Kubernetes manifests (if available).

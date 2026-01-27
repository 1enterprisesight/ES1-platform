# Phase 6: AI/ML Platform - Detailed Implementation Plan

**Version:** 1.0
**Created:** 2026-01-26
**Last Updated:** 2026-01-26
**Status:** IN PROGRESS

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Goals & Objectives](#2-goals--objectives)
3. [Architecture Overview](#3-architecture-overview)
4. [Component Inventory](#4-component-inventory)
5. [Database Schemas](#5-database-schemas)
6. [Implementation Phases](#6-implementation-phases)
7. [Open Questions & Decisions](#7-open-questions--decisions)
8. [Session Recovery Notes](#8-session-recovery-notes)

---

## 1. Executive Summary

Phase 6 transforms ES1 Platform into a comprehensive **Agent Operating System** where:

- **Data flows** through Airflow pipelines into knowledge graphs
- **Multiple agent frameworks** (Langflow, CrewAI, AutoGen, n8n) operate on shared knowledge
- **KrakenD** provides full API visibility, security, and logging for ALL traffic
- **ES1 Platform Manager** provides unified visibility and control

### Core Principle
**Complete transparency** - every API call between infrastructure components is logged, secured, and visible from the Platform Manager UI.

---

## 2. Goals & Objectives

### Primary Goals

1. **Unified Knowledge Layer**
   - External data sources → Airflow DAGs → Knowledge Graphs in PostgreSQL
   - Vectors, documents, entities, relationships all queryable
   - Shared knowledge accessible by all agent frameworks

2. **Multi-Framework Agent Support**
   - Users choose the right tool: Langflow, CrewAI, AutoGen, or n8n
   - Agents can communicate across frameworks
   - Shared context and memory between agents

3. **Full API Transparency**
   - ALL service-to-service communication through/logged by KrakenD
   - Complete audit trail of every API call
   - Security policies enforced centrally

4. **Unified Platform Management**
   - Single UI to manage all AI/ML components
   - Real-time visibility into agent activity
   - Knowledge graph exploration and management

### Non-Goals (Out of Scope for Phase 6)

- GPU cluster management (Phase 6.8 - deferred)
- Kubernetes-native model serving like KServe (Phase 4)
- Production-grade model mesh (requires K8s)

---

## 3. Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL CLIENTS                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    KRAKEND API GATEWAY                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • Authentication (JWT, API Keys)                             │   │
│  │ • Rate Limiting (per client, per endpoint)                   │   │
│  │ • Request/Response Logging → PostgreSQL                      │   │
│  │ • Metrics → Prometheus                                       │   │
│  │ • Security Policies (CORS, IP filtering)                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  EXTERNAL ROUTES              INTERNAL ROUTES                       │
│  /api/v1/external/*           /internal/airflow/*                   │
│                               /internal/langflow/*                  │
│                               /internal/agents/*                    │
│                               /internal/knowledge/*                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     API AUDIT LOG (PostgreSQL)                      │
│  Every API call logged: source, destination, method, path,          │
│  status, latency, auth method, errors, correlation ID               │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA INGESTION LAYER                           │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    AIRFLOW DAGs                               │  │
│  │  • Source connectors (S3, databases, APIs, web scraping)     │  │
│  │  • Document processing (PDF, HTML, code, etc.)               │  │
│  │  • Chunking strategies (fixed, recursive, semantic)          │  │
│  │  • Embedding generation (via Ollama)                         │  │
│  │  • Entity extraction (NER, relationship extraction)          │  │
│  │  • Load to Knowledge Graph                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE GRAPH LAYER                            │
│                      (PostgreSQL + pgvector)                        │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  vectors.*  │  │   rag.*     │  │  graph.*    │                 │
│  │  Embeddings │  │  Documents  │  │  Entities   │                 │
│  │  Collections│  │  Chunks     │  │  Relations  │                 │
│  │             │  │  Sources    │  │  Properties │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT FRAMEWORK LAYER                            │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Langflow   │  │   CrewAI     │  │   AutoGen    │              │
│  │  Visual agent│  │  Role-based  │  │  Multi-agent │              │
│  │  building    │  │  teams       │  │  conversation│              │
│  │  :7860       │  │  :8100       │  │  :8101       │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│  ┌──────────────┐         │                 │                       │
│  │     n8n      │         │                 │                       │
│  │  Workflow    │←────────┴─────────────────┘                       │
│  │  automation  │  (can trigger any agent framework)                │
│  │  :5678       │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ↓                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                 AGENT ROUTER / MESSAGE BUS                    │  │
│  │  • Routes tasks to appropriate agent/framework                │  │
│  │  • Shared context store (Redis)                              │  │
│  │  • Cross-framework messaging (Redis Pub/Sub)                 │  │
│  │  • Agent registry and discovery                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM SERVING LAYER                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │    Ollama    │  │    MLflow    │  │   Langfuse   │              │
│  │  LLM serving │  │  Experiment  │  │  LLM tracing │              │
│  │  & embedding │  │  tracking    │  │  & observ.   │              │
│  │  :11434      │  │  :5050       │  │  :3000       │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   ES1 PLATFORM MANAGER UI                           │
│                                                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │ API Traffic│  │ Knowledge  │  │   Agent    │  │  Pipeline  │   │
│  │ & Security │  │ Graph View │  │  Monitor   │  │  Manager   │   │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘   │
│                                                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │  Service   │  │  Request   │  │   Error    │  │  Network   │   │
│  │    Map     │  │   Trace    │  │ Dashboard  │  │  Designer  │   │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Traffic Flow Patterns

```
Pattern 1: External API Request
──────────────────────────────────
Client → KrakenD → Service → Response
            │
            └→ Audit Log (PostgreSQL)

Pattern 2: Data Ingestion
──────────────────────────────────
External Source → Airflow DAG → Process → Embed (Ollama) → Knowledge Graph
                      │              │           │              │
                      └──────────────┴───────────┴──────────────┘
                                     All via KrakenD (logged)

Pattern 3: Agent Execution
──────────────────────────────────
User Request → Agent Router → [Langflow|CrewAI|AutoGen]
                    │                    │
                    │                    ├→ Query Knowledge Graph
                    │                    ├→ Call Ollama (LLM)
                    │                    ├→ Execute Tools
                    │                    └→ Message Other Agents
                    │                           │
                    └───────────────────────────┘
                           All via KrakenD (logged)

Pattern 4: Cross-Agent Communication
──────────────────────────────────
CrewAI Agent ─→ Redis Pub/Sub ─→ AutoGen Agent
      │              │                 │
      └──────────────┴─────────────────┘
              Logged to Audit
```

---

## 4. Component Inventory

### Currently Deployed (Phase 6.1-6.3)

| Component | Container | Port | Status | Purpose |
|-----------|-----------|------|--------|---------|
| AI/ML PostgreSQL | es1-aiml-postgres | 5433 | ✅ Running | Dedicated AI/ML database with pgvector |
| Ollama | es1-ollama | 11434 | ✅ Running | Local LLM inference |
| Open WebUI | es1-ollama-webui | 3010 | ✅ Running | Chat interface for Ollama |
| MLflow | es1-mlflow | 5050 | ✅ Running | Experiment tracking |

### Existing Platform Services

| Component | Container | Port | Status | Purpose |
|-----------|-----------|------|--------|---------|
| KrakenD | es1-krakend | 8080 | ✅ Running | API Gateway |
| Airflow | es1-airflow-* | 8081 | ✅ Running | Workflow orchestration |
| Langflow | es1-langflow | 7860 | ✅ Running | Visual agent builder |
| n8n | es1-n8n | 5678 | ✅ Running | Workflow automation |
| Langfuse | es1-langfuse | 3000 | ✅ Running | LLM observability |
| Platform PostgreSQL | es1-postgres | 5432 | ✅ Running | Platform database |
| Redis | es1-redis | 6379 | ✅ Running | Cache & message broker |

### To Be Added

| Component | Port | Priority | Purpose |
|-----------|------|----------|---------|
| CrewAI Service | 8100 | Phase 6.5 | Role-based agent teams |
| AutoGen Service | 8101 | Phase 6.5 | Multi-agent conversations |
| Agent Router | 8102 | Phase 6.5 | Unified agent API |

---

## 5. Database Schemas

### AI/ML Database (port 5433) - Existing

```
aiml database
├── vectors schema (✅ created)
│   ├── collections        - Embedding collection metadata
│   ├── embeddings         - 1536-dim vectors (OpenAI compatible)
│   ├── embeddings_384     - 384-dim vectors (MiniLM)
│   ├── embeddings_768     - 768-dim vectors (BERT)
│   └── embeddings_4096    - 4096-dim vectors (large models)
│
├── rag schema (✅ created)
│   ├── sources            - Data source definitions
│   ├── documents          - Ingested documents
│   ├── chunks             - Document chunks with embeddings
│   ├── knowledge_bases    - Knowledge base definitions
│   ├── knowledge_base_sources - KB to source mapping
│   └── search_history     - Search analytics
│
├── agents schema (✅ created)
│   ├── definitions        - Agent configurations
│   ├── sessions           - Conversation sessions
│   ├── messages           - Conversation history
│   ├── memory             - Agent long-term memory
│   ├── networks           - Agent network definitions
│   ├── network_members    - Network membership
│   └── executions         - Execution history
│
└── mlops schema (✅ created)
    ├── models             - Model registry
    ├── deployments        - Model deployments
    ├── inference_logs     - Inference tracking
    ├── feature_groups     - Feature definitions
    ├── feature_values     - Feature values
    └── prompts            - Prompt templates
```

### Platform Database (port 5432) - To Be Added

```
es1_platform database
└── audit schema (⏳ to create)
    ├── api_requests       - Every API call logged
    ├── service_dependencies - Service-to-service mapping
    └── security_events    - Security alerts
```

### Audit Schema Definition

```sql
-- To be added to platform database
CREATE SCHEMA IF NOT EXISTS audit;

-- Every API call logged
CREATE TABLE audit.api_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(64) NOT NULL,      -- Correlation ID for tracing
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Source
    source_service VARCHAR(100),
    source_ip INET,
    user_id VARCHAR(255),
    api_key_id UUID,

    -- Destination
    destination_service VARCHAR(100),
    method VARCHAR(10),
    path TEXT,
    query_params JSONB,

    -- Request/Response (hashed for privacy, not full body)
    request_headers JSONB,
    request_body_hash VARCHAR(64),
    request_size_bytes INTEGER,
    response_status INTEGER,
    response_body_hash VARCHAR(64),
    response_size_bytes INTEGER,

    -- Performance
    latency_ms INTEGER,

    -- Security
    auth_method VARCHAR(50),
    auth_success BOOLEAN,
    security_flags JSONB,

    -- Errors
    error_code VARCHAR(50),
    error_message TEXT,

    metadata JSONB DEFAULT '{}'
);

-- Indexes for common queries
CREATE INDEX idx_api_requests_timestamp ON audit.api_requests(timestamp);
CREATE INDEX idx_api_requests_source ON audit.api_requests(source_service);
CREATE INDEX idx_api_requests_dest ON audit.api_requests(destination_service);
CREATE INDEX idx_api_requests_status ON audit.api_requests(response_status);
CREATE INDEX idx_api_requests_request_id ON audit.api_requests(request_id);

-- Service dependency map (aggregated)
CREATE TABLE audit.service_dependencies (
    source_service VARCHAR(100),
    destination_service VARCHAR(100),
    endpoint_pattern VARCHAR(255),
    call_count BIGINT DEFAULT 0,
    avg_latency_ms FLOAT,
    error_rate FLOAT,
    last_seen TIMESTAMPTZ,
    PRIMARY KEY (source_service, destination_service, endpoint_pattern)
);

-- Security events
CREATE TABLE audit.security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(50),
    severity VARCHAR(20),
    source_ip INET,
    source_service VARCHAR(100),
    user_id VARCHAR(255),
    details JSONB,
    resolved BOOLEAN DEFAULT false
);

CREATE INDEX idx_security_events_timestamp ON audit.security_events(timestamp);
CREATE INDEX idx_security_events_type ON audit.security_events(event_type);
CREATE INDEX idx_security_events_severity ON audit.security_events(severity);
```

### Knowledge Graph Schema (To Be Added)

```sql
-- Add to aiml database for entity/relationship storage
CREATE SCHEMA IF NOT EXISTS graph;

-- Entities extracted from documents
CREATE TABLE graph.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id UUID REFERENCES rag.knowledge_bases(id),
    entity_type VARCHAR(100) NOT NULL,    -- person, organization, concept, etc.
    name VARCHAR(500) NOT NULL,
    canonical_name VARCHAR(500),          -- Normalized name for deduplication
    description TEXT,
    properties JSONB DEFAULT '{}',
    embedding_id UUID,                    -- Link to vector embedding
    source_chunk_ids UUID[],              -- Which chunks mentioned this entity
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entities_kb ON graph.entities(knowledge_base_id);
CREATE INDEX idx_entities_type ON graph.entities(entity_type);
CREATE INDEX idx_entities_name ON graph.entities(canonical_name);

-- Relationships between entities
CREATE TABLE graph.relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id UUID REFERENCES rag.knowledge_bases(id),
    source_entity_id UUID NOT NULL REFERENCES graph.entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES graph.entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,  -- works_for, located_in, related_to
    properties JSONB DEFAULT '{}',
    source_chunk_ids UUID[],
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_relationships_kb ON graph.relationships(knowledge_base_id);
CREATE INDEX idx_relationships_source ON graph.relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON graph.relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON graph.relationships(relationship_type);
```

---

## 6. Implementation Phases

### Phase 6.0: API Infrastructure Foundation
**Goal:** Full visibility into all API traffic

- [x] **6.0a** Add audit schema to platform PostgreSQL
- [x] **6.0b** Configure KrakenD logging (logstash format)
- [x] **6.0c** Add internal service routes to KrakenD (Ollama, MLflow, Knowledge, Agents, Audit)
- [ ] **6.0d** Implement service-to-service JWT authentication
- [ ] **6.0e** Add request correlation IDs across services
- [ ] **6.0f** Platform Manager API traffic dashboard

### Phase 6.5: Multi-Framework Agents
**Goal:** Support multiple agent frameworks with unified routing

- [x] **6.5a** Create CrewAI service container
- [x] **6.5b** Create AutoGen service container
- [x] **6.5c** Implement Agent Router API
- [x] **6.5d** Set up Redis pub/sub for agent messaging (built into router)
- [x] **6.5e** Shared context store for cross-agent memory (built into router)
- [ ] **6.5f** Platform Manager agent monitoring UI

### Phase 6.6: Knowledge Graph & Ingestion
**Goal:** Unified knowledge layer for all agents

- [x] **6.6a** Add graph schema to aiml database (entities, relationships, entity_types, relationship_types)
- [x] **6.6b** Create Airflow DAG templates for data ingestion
- [x] **6.6c** Implement document processing pipeline
- [x] **6.6d** Build embedding generation service (using Ollama)
- [x] **6.6e** Create entity extraction pipeline (spaCy + LLM hybrid)
- [ ] **6.6f** Knowledge base management API
- [ ] **6.6g** Platform Manager knowledge graph explorer

### Phase 6.9: Platform Manager Integration
**Goal:** Unified visibility and control

- [ ] **6.9a** API traffic visualization dashboard
- [ ] **6.9b** Service dependency map
- [ ] **6.9c** Request tracing view
- [ ] **6.9d** Agent network designer
- [ ] **6.9e** Knowledge graph explorer
- [ ] **6.9f** Pipeline management UI
- [ ] **6.9g** Security alerts dashboard

---

## 7. Open Questions & Decisions

### Resolved Decisions

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Agent frameworks to support | Langflow, CrewAI, AutoGen, n8n | Cover different use cases | 2026-01-26 |
| Knowledge graph storage | PostgreSQL (not Neo4j) | Simpler, already have pgvector | 2026-01-26 |
| API logging approach | KrakenD → PostgreSQL | Centralized, queryable | 2026-01-26 |
| LLM serving for embeddings | Ollama | Already deployed, air-gapped friendly | 2026-01-26 |
| Internal API routing | Hybrid (critical via KrakenD, others async log) | Balance visibility vs latency | 2026-01-26 |
| Agent Router | Custom FastAPI service | More control, cleaner API than n8n routing | 2026-01-26 |
| Cross-agent memory | Redis (working) + PostgreSQL (persistent) | Fast access + durable storage | 2026-01-26 |
| Entity extraction | spaCy + LLM refinement | Speed for bulk, accuracy for complex | 2026-01-26 |
| Embedding model | Configurable per knowledge base | Flexibility for different use cases | 2026-01-26 |

### Open Questions (Need Discussion)

| # | Question | Options | Impact | Status |
|---|----------|---------|--------|--------|
| 1 | Should internal services ALWAYS route through KrakenD, or only log to audit? | A) All traffic through KrakenD<br>B) Direct + async logging<br>C) Hybrid (critical through KrakenD, others logged) | Performance vs visibility | **RESOLVED: C** |
| 2 | Agent Router: build custom or use existing? | A) Custom FastAPI service<br>B) Use n8n as router<br>C) KrakenD backend routing | Complexity vs flexibility | **RESOLVED: A** |
| 3 | Cross-agent memory: Redis vs PostgreSQL? | A) Redis (fast, ephemeral)<br>B) PostgreSQL (persistent, queryable)<br>C) Both (Redis cache + PG persist) | Performance vs durability | **RESOLVED: C** |
| 4 | Entity extraction: which NER model? | A) spaCy (fast, general)<br>B) Ollama + LLM (flexible)<br>C) Both (spaCy + LLM refinement) | Accuracy vs speed | **RESOLVED: C** |
| 5 | Embedding model for knowledge graph? | A) Ollama nomic-embed-text<br>B) Ollama mxbai-embed-large<br>C) Configurable per KB | Quality vs flexibility | **RESOLVED: C** |

### Parking Lot (Future Considerations)

- **Airflow Custom Dockerfile**: Knowledge ingestion plugin requires additional packages
  (psycopg2-binary, requests, pdfplumber, spacy, PyPDF2). Currently DAGs load but will
  fail at runtime. Address during upgrade process to design as proper package with:
  - Custom Airflow image with pre-installed dependencies
  - Proper Python package structure for knowledge plugin
  - Version pinning and dependency management
  - Consider airflow-provider pattern for distribution
- Graph query language: Consider Apache AGE for Cypher support on PostgreSQL
- Vector search: Consider Qdrant for high-volume vector workloads
- Model mesh: KServe/Seldon when moving to Kubernetes
- GPU scheduling: NVIDIA device plugin for K8s

---

## 8. Session Recovery Notes

### Current State (2026-01-26)

**What's Done:**
- Phase 6.1-6.3 basic infrastructure deployed and running
- AI/ML PostgreSQL with pgvector (vectors, rag, agents, mlops schemas)
- Ollama + Open WebUI + MLflow running
- Architecture and scope documented in this file
- Phase 6.0a-c complete: Audit schema + KrakenD routes for all services
- Phase 6.6a complete: Graph schema for knowledge graph
- Phase 6.6b-e complete: Airflow knowledge ingestion pipeline (plugins + DAGs)

**What's Next:**
- Phase 6.6f-g: Knowledge base management API and UI
- Phase 6.5f: Platform Manager agent monitoring UI
- Phase 6.9: Platform Manager UI integration

**Agent Services (Phase 6.5):**
- `services/agents/crewai/` - CrewAI role-based teams (port 8100)
- `services/agents/autogen/` - AutoGen multi-agent conversations (port 8101)
- `services/agents/router/` - Unified Agent Router API (port 8102)
- `docker-compose.agents.yml` - Docker compose for agent services

**Key Files:**
- This document: `docs/PHASE-6-AIML-PLATFORM.md`
- Main planning doc: `docs/ES1-PLATFORM-PLANNING.md`
- AI/ML compose file: `docker-compose.aiml.yml`
- AI/ML database init: `infrastructure/aiml-postgres/init/`

**Airflow Knowledge Ingestion Plugin:**
- `services/airflow/plugins/knowledge/__init__.py` - Plugin entry point
- `services/airflow/plugins/knowledge/config.py` - Configuration (DB, Ollama, chunking)
- `services/airflow/plugins/knowledge/database.py` - AIMLDatabase & PlatformDatabase connectors
- `services/airflow/plugins/knowledge/embeddings.py` - OllamaEmbeddings client
- `services/airflow/plugins/knowledge/processors.py` - DocumentProcessor, FileParser, chunking strategies
- `services/airflow/plugins/knowledge/extractors.py` - EntityExtractor (spaCy + LLM hybrid)

**Airflow DAG Templates:**
- `services/airflow/dags/knowledge_ingestion/document_ingestion_dag.py` - Single document ingestion
- `services/airflow/dags/knowledge_ingestion/batch_ingestion_dag.py` - Batch document processing
- `services/airflow/dags/knowledge_ingestion/web_scraper_dag.py` - Website crawling and ingestion

**Running Containers:**
```bash
# Check AI/ML stack
docker ps --filter name=es1-aiml --filter name=es1-ollama --filter name=es1-mlflow

# Check all platform services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Quick Commands:**
```bash
# Start AI/ML stack
make up-aiml

# View AI/ML logs
make logs-aiml

# Connect to AI/ML database
docker exec -it es1-aiml-postgres psql -U aiml_user -d aiml
```

---

## Appendix A: Service URLs (Local Development)

| Service | URL | Credentials |
|---------|-----|-------------|
| Platform Manager UI | http://localhost:3001 | - |
| Platform Manager API | http://localhost:8000 | - |
| KrakenD Gateway | http://localhost:8080 | - |
| Airflow | http://localhost:8081 | airflow/airflow |
| Langflow | http://localhost:7860 | - |
| n8n | http://localhost:5678 | (setup on first run) |
| Langfuse | http://localhost:3000 | See .env |
| Ollama API | http://localhost:11434 | - |
| Open WebUI | http://localhost:3010 | - |
| MLflow | http://localhost:5050 | - |
| AI/ML PostgreSQL | localhost:5433 | aiml_user/aiml_dev_password |
| Platform PostgreSQL | localhost:5432 | es1_user/es1_dev_password |
| Grafana | http://localhost:3002 | admin/admin |
| Prometheus | http://localhost:9090 | - |

---

## Appendix B: Agent Framework Comparison

| Feature | Langflow | CrewAI | AutoGen | n8n |
|---------|----------|--------|---------|-----|
| **Best For** | Visual building, RAG | Team-based tasks | Multi-agent chat | Workflow automation |
| **Interface** | Visual drag-drop | Python code | Python code | Visual + code |
| **Agent Roles** | Single agent flows | Role-based teams | Conversable agents | Workflow nodes |
| **Memory** | Built-in | Shared crew memory | Conversation history | Workflow state |
| **Tools** | LangChain tools | Custom tools | Function calling | 400+ integrations |
| **Learning Curve** | Low | Medium | Medium | Low |
| **Flexibility** | Medium | High | High | Medium |

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-26 | 1.0 | Initial document creation |
| 2026-01-26 | 1.1 | Added Phase 6.6b-e: Airflow knowledge ingestion pipeline (plugins + DAGs) |
| 2026-01-27 | 1.2 | Added Phase 6.5a-e: Multi-framework agents (CrewAI, AutoGen, Agent Router) |

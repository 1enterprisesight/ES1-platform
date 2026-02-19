# ES1 Platform Manager - User Guide

This guide explains how to use the ES1 Platform Manager to manage your API Gateway, workflows, and AI integrations.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Gateway Management](#api-gateway-management)
3. [Workflow Management (Airflow)](#workflow-management-airflow)
4. [Automation (n8n)](#automation-n8n)
5. [AI Flows (Langflow)](#ai-flows-langflow)
6. [Observability (Langfuse)](#observability-langfuse)
7. [Integration Patterns](#integration-patterns)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Clients                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KrakenD API Gateway                           │
│                    (Port 8080)                                   │
│  Routes:                                                         │
│  - /api/airflow/*  → Airflow API                                │
│  - /api/langflow/* → Langflow API                               │
│  - /webhook/*      → n8n Webhooks                               │
│  - Custom routes   → Exposed resources                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    Airflow      │ │    Langflow     │ │      n8n        │
│  (Port 8081)    │ │  (Port 7860)    │ │  (Port 5678)    │
│                 │ │                 │ │                 │
│  - DAG Mgmt     │ │  - AI Flows     │ │  - Automation   │
│  - Scheduling   │ │  - LLM Chains   │ │  - Webhooks     │
│  - Data Pipes   │ │  - Vector DBs   │ │  - Integrations │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Langfuse (Observability)                      │
│                    (Port 3000)                                   │
│  - Traces, Sessions, Metrics                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Access Points

| Service | Direct URL | Via Gateway |
|---------|-----------|-------------|
| Platform Manager UI | http://localhost:3001 | - |
| Platform Manager API | http://localhost:8000 | - |
| KrakenD Gateway | http://localhost:8080 | - |
| Airflow UI | http://localhost:8081 | - |
| Langflow UI | http://localhost:7860 | - |
| n8n UI | http://localhost:5678 | - |
| Langfuse UI | http://localhost:3000 | - |

---

## API Gateway Management

### Understanding the Gateway Flow

```
Discovery → Exposure → Approval → Deployment
    │           │          │           │
    ▼           ▼          ▼           ▼
Find APIs    Tag for    Review &    Push to
from        exposure   approve     KrakenD
services
```

### Step 1: Viewing Current Configuration

Navigate to **Gateway → Config** tab to:

- View the current KrakenD configuration (JSON)
- See endpoint count and structure
- Browse configuration versions
- Compare versions (diff view)

### Step 2: Resource Discovery

Resources are APIs/endpoints discovered from integrated services:

1. Go to **Gateway → Resources**
2. Click **"Discover Resources"** to scan all services
3. Resources are automatically discovered from:
   - **Airflow**: DAGs become triggerable endpoints
   - **Langflow**: Flows become execution endpoints
   - **n8n**: Webhooks become callable endpoints
   - **Manual**: Add custom resources

### Step 3: Creating Exposures

An "Exposure" is a resource tagged for inclusion in the API Gateway:

1. Find a resource in the Resources tab
2. Click **"Expose"** button
3. Configure exposure settings:
   - **Endpoint path**: The URL path in the gateway
   - **Rate limiting**: Requests per second/minute
   - **Authentication**: Required auth method
   - **Timeout**: Request timeout
4. Submit for approval

### Step 4: Approval Workflow

1. Go to **Gateway → Exposures**
2. Filter by **"Pending"** status
3. Review each exposure:
   - Check endpoint configuration
   - Verify security settings
   - Review generated config
4. Click **"Approve"** or **"Reject"** (with reason)

### Step 5: Deployment

After approvals are complete:

1. Go to **Gateway → Deployments**
2. Click **"Deploy Approved Changes"**
3. Platform Manager will:
   - Generate new KrakenD config
   - Create a new config version
   - Deploy to KrakenD
   - Run health checks
4. Monitor deployment status (pending → in_progress → succeeded/failed)

### Step 6: Rollback

If something goes wrong:

1. Go to **Gateway → Deployments**
2. Find the previous working deployment
3. Click **"Rollback"** button
4. Provide a reason for rollback
5. Confirm rollback

The system will restore the previous configuration version.

### Configuration Versioning

Every deployment creates a new version:

- **Config tab** shows version history
- Click any two versions to see diff
- Active version is marked
- All changes are audited

---

## Workflow Management (Airflow)

### Managing DAGs

Navigate to **Workflows → DAGs** to:

- View all DAGs with status (active/paused)
- Trigger DAG runs manually
- Pause/unpause DAGs
- See schedule and next run time

### Viewing DAG Runs

Navigate to **Workflows → DAG Runs** to:

- See recent execution history across all DAGs
- View run status (success/failed/running)
- Check start/end times
- Runs auto-refresh every 10 seconds

### Creating New DAGs

Navigate to **Workflows → DAG Editor** to:

1. Click **"New DAG"**
2. Choose a template:
   - **Basic**: Simple task workflow
   - **HTTP API**: API calling workflow
   - **Data Pipeline**: ETL workflow (extract → transform → load)
   - **CloudSQL Query**: Database query workflow
3. Fill in:
   - DAG ID (unique identifier)
   - Description
   - Schedule (cron or preset)
   - Tags
4. Click **"Create"**

### Editing DAG Files

1. Select a DAG file from the sidebar
2. Edit the Python code
3. Click **"Save"** to update

### Managing Connections

Navigate to **Workflows → Connections** to view Airflow connections for:
- Databases
- APIs
- Cloud services

---

## Automation (n8n)

### Initial Setup

n8n requires an API key for integration:

1. Open n8n directly: http://localhost:5678
2. Go to **Settings → API**
3. Create a new API key
4. Add the key to your environment:
   ```
   N8N_API_KEY=your-api-key-here
   ```
5. Restart the Platform Manager

### Managing Workflows

Navigate to **Automation → Workflows** to:

- View all n8n workflows
- See active/inactive status
- Execute workflows manually
- Activate/deactivate workflows

### Viewing Executions

Navigate to **Automation → Executions** to:

- See execution history
- View status (success/error/running)
- Check execution details and output
- Debug failed executions

### Managing Credentials

Navigate to **Automation → Credentials** to:

- View configured credentials (secrets hidden)
- Add new credentials in n8n UI

---

## AI Flows (Langflow)

### Discovering Flows

1. Navigate to **AI → Flows**
2. Click **"Discover Flows"** to sync from Langflow
3. Flows are imported with their configurations

### Running Flows

1. Navigate to **AI → Flow Runner**
2. Select a flow from the grid
3. Enter your input text
4. Click **"Run"**
5. View the output

### Creating Flows

Flows are created in Langflow directly:

1. Open Langflow: http://localhost:7860
2. Create your flow visually
3. Save the flow
4. Discover it in Platform Manager

---

## Observability (Langfuse)

### Viewing Traces

Navigate to **Observability → Traces** to:

- See all LLM traces
- View input/output for each trace
- Check for errors
- Filter by user, session, or name

### Viewing Sessions

Navigate to **Observability → Sessions** to:

- See conversation sessions
- Group related traces
- Track user journeys

### Viewing Metrics

Navigate to **Observability → Metrics** to:

- Total traces, observations, generations
- Daily trace counts (last 14 days)
- System usage patterns

---

## Integration Patterns

### Pattern 1: Exposing an Airflow DAG via API Gateway

**Goal**: Make a DAG triggerable via external API call

```
External Call → KrakenD → Airflow API → DAG Trigger
```

Steps:
1. Create your DAG in Airflow
2. Run resource discovery in Platform Manager
3. Find your DAG in Resources
4. Create an exposure with settings:
   - Endpoint: `/api/workflows/my-dag/trigger`
   - Method: POST
   - Auth: API Key required
5. Approve and deploy

### Pattern 2: Langflow Using Airflow DAG

**Goal**: Have an AI flow trigger a data pipeline

```
User Query → Langflow → HTTP Node → Airflow API → DAG
```

Steps:
1. In Langflow, add an **HTTP Request** component
2. Configure:
   - URL: `http://airflow-webserver:8080/api/v1/dags/{dag_id}/dagRuns`
   - Method: POST
   - Headers: `Authorization: Basic <base64(airflow:airflow)>`
   - Body: `{"conf": {}}`
3. Connect to your flow logic

### Pattern 3: n8n Workflow Calling Airflow

**Goal**: Automated workflow triggers data pipeline

```
n8n Trigger → n8n Workflow → HTTP Request → Airflow API → DAG
```

Steps:
1. Create workflow in n8n
2. Add **HTTP Request** node:
   - URL: `http://airflow-webserver:8080/api/v1/dags/{dag_id}/dagRuns`
   - Method: POST
   - Authentication: Basic Auth (airflow/airflow)
3. Connect to your trigger (webhook, schedule, etc.)

### Pattern 4: Database Query from AI Agent

**Goal**: AI agent queries database via Airflow DAG

```
User Question → Langflow → Trigger DAG → CloudSQL Query → Return Results
```

Steps:
1. Use the CloudSQL Query DAG template
2. Configure Airflow Variables for connection
3. In Langflow, trigger the DAG and poll for results
4. Parse XCom data for query results

### Pattern 5: Webhook-Triggered Pipeline

**Goal**: External system triggers full processing pipeline

```
External Event → n8n Webhook → n8n Workflow → Airflow DAG → Process
```

Steps:
1. Create n8n workflow with Webhook trigger
2. Expose webhook via Platform Manager:
   - Endpoint: `/webhook/my-pipeline`
3. n8n workflow calls Airflow API to trigger DAG
4. Monitor execution in Platform Manager

---

## Troubleshooting

### Service Shows "Offline"

1. Check if the container is running: `docker ps`
2. Check container logs: `docker logs es1-<service>`
3. Verify network connectivity

### n8n Shows "Setup Required"

1. API key not configured
2. Follow n8n setup steps above

### Gateway Config Empty

1. Check KrakenD container has config mounted
2. Verify config path in docker-compose
3. Restart Platform Manager after config changes

### DAG Runs Not Showing

1. Verify Airflow is healthy
2. Check that DAGs exist and are not paused
3. Trigger a DAG manually to create a run

### Resource Discovery Returns Empty

1. Check service connections
2. Verify services have data (DAGs exist, flows exist)
3. Check Platform Manager logs for errors

---

## Quick Reference

### Restart Services

```bash
# Restart all services
docker compose -f docker-compose.yml \
  -f docker-compose.airflow.yml \
  -f docker-compose.es1-platform-manager.yml \
  restart

# Restart single service
docker compose restart platform-manager-api
```

### View Logs

```bash
# Platform Manager API
docker logs -f platform-manager-api

# KrakenD
docker logs -f es1-krakend

# Airflow
docker logs -f es1-airflow-webserver
```

### Check API Health

```bash
# Platform Manager
curl http://localhost:8000/health

# Gateway status
curl http://localhost:8000/api/v1/gateway/status

# System status
curl http://localhost:8000/api/v1/system/status
```

# Sentinel: Workspace-Scoped Data Architecture

## Status: IN PROGRESS

## Overview

Rearchitect Sentinel so that **workspaces are the top-level scope** for all data,
analysis, and UI state. No more global datasets or views.

## Design Decisions

- **Workspaces are shared** (all users can access any workspace they're a member of)
- **Datasets belong to a workspace** (upload always targets the active workspace)
- **Tiles and silos are shared per-workspace** (all users see the same insights)
- **Interactions are per-user within a workspace** (thumbs up/down, engagement tracking)
- **DuckDB uses namespace prefixing** (`ws_{workspace_id}_{table}`) for isolation
- **Join config is explicit** — system suggests joins, validates before accepting, stores in workspace settings
- **User creates workspace first, then uploads data** — no auto-naming from datasets

## Data Scoping Model

| Concept        | Scoped to          |
|----------------|---------------------|
| Workspaces     | Shared (all users)  |
| Datasets       | Workspace           |
| DuckDB tables  | Workspace (prefixed)|
| Join config    | Workspace           |
| Tiles          | Workspace (shared)  |
| Silos          | Workspace (shared)  |
| Interactions   | Workspace + User    |
| Sessions       | User                |

## Implementation Phases

### Phase 1: Database Migration [ ]
- [ ] New migration `V011__workspace_scoped_datasets.sql`
- [ ] Workspaces: drop `user_id`, add `created_by` (audit only)
- [ ] Add `workspace_members` table: `(workspace_id, user_id, role)`
- [ ] Add `workspace_id` FK to `sentinel.datasets` (cascade delete)
- [ ] Add `user_id` to `workspace_interactions`
- [ ] Store `join_config` in workspace `settings` JSONB

### Phase 2: DuckDB Namespace Isolation [ ]
- [ ] Prefix tables as `ws_{workspace_id}_{tablename}`
- [ ] New: `load_workspace_datasets(workspace_id, datasets)`
- [ ] New: `unload_workspace(workspace_id)`
- [ ] New: `get_workspace_tables(workspace_id)`
- [ ] `get_data_profile(workspace_id)` — cache per workspace
- [ ] `run_query` workspace_id param, validate table prefix
- [ ] Startup: init empty DuckDB, load lazily on workspace activate

### Phase 3: Backend API Changes [ ]
- [ ] Datasets: all CRUD scoped to active workspace
- [ ] New: `POST /workspaces/{id}/join-config` (save confirmed join)
- [ ] New: `POST /workspaces/{id}/validate-join` (test before saving)
- [ ] Datasources: filter to active workspace tables
- [ ] Tile/Silo stores: workspace-keyed dictionaries (not global singletons)
- [ ] Agent loop: one per active workspace, lifecycle managed
- [ ] SSE stream: workspace-scoped subscriptions
- [ ] Ask route: scoped to active workspace's DuckDB tables
- [ ] Interactions: add user_id to all interaction writes/reads

### Phase 4: Frontend Changes [ ]
- [ ] DataManager.jsx: workspace-scoped dataset list, empty state
- [ ] WorkspaceSwitcher.jsx: show all accessible workspaces, loading overlay
- [ ] New JoinConfigPanel.jsx: suggest/validate/confirm join columns
- [ ] SSE: reconnect with workspace context on switch
- [ ] api.js: workspace-aware API calls
- [ ] Clear workspace indicator in UI

### Phase 5: Startup Simplification [ ]
- [ ] Remove global dataset loading from main.py
- [ ] Remove global silo discovery and agent start
- [ ] init_db() creates empty DuckDB only
- [ ] Everything spins up per-workspace on activate

### Phase 6: Data Migration [ ]
- [ ] Create default workspace for existing datasets
- [ ] Backfill workspace_id on existing dataset rows
- [ ] Move file-based caches into PG workspace tables

## Risks & Mitigations

- **DuckDB concurrency**: Single writer lock fine at current scale; consider per-workspace connections later
- **Memory**: LRU eviction for idle workspace tables (unload after N min with no subscribers)
- **Join validation on large CSVs**: Use LIMIT + EXPLAIN, not full execution
- **Agent loop proliferation**: Global rate limiter, increase cycle time for low-activity workspaces

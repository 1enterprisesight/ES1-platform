# Sentinel: Data Linking & Workspace Activation Plan

**Branch:** `feature/sentinel-workspace-scoped-data`
**Status:** In progress
**Last commit:** `3db3b08` fix(sentinel): login crash

## Context

Sentinel workspaces contain 1-3 CSV files loaded as separate DuckDB tables.
When a workspace has multiple tables, the user must explicitly link them
(configure join keys) before the workspace can be activated and the agent
can run. This ensures the agent writes correct JOINs and the data is
treated as one logical dataset.

## Core Principles

- **Robust, reliable, repeatable production system**
- User-driven workflow — no automatic assumptions about data
- Max 3 CSV files per workspace
- All tables must be connected before activation
- Agent only runs on activated workspaces

## Design

### Data States

```
EMPTY        → no files uploaded
UPLOADING    → 1+ files, user may upload more (max 3)
LINKING      → 2+ files, user configuring join keys
READY        → all links confirmed, user can activate
ACTIVE       → user clicked Activate, agent can run
```

### Rules

| Files | Links needed | Activate enabled |
|-------|-------------|-----------------|
| 0     | —           | No              |
| 1     | 0           | Yes             |
| 2     | 1           | After link confirmed |
| 3     | 2           | After all links confirmed, all tables connected |

### join_config Schema (workspace settings)

```json
{
  "join_config": [
    {
      "left_table": "orders",
      "right_table": "customers",
      "left_column": "customer_id",
      "right_column": "customer_id",
      "matched_rows": 1250
    }
  ],
  "data_activated": true
}
```

### Connectivity Check

All tables must be reachable from any other table through the links.
With 3 tables (A, B, C), need at least 2 links such that the graph
is connected (A-B + B-C, or A-B + A-C, etc.).

## Implementation Steps

### Step 1: Backend — Data Readiness Function ✅ TODO
**File:** `services/sentinel/backend/app/routes/workspaces.py`

Add `is_workspace_data_ready(workspace_id) -> dict` that returns:
```python
{
    "ready": bool,
    "reason": "no_data" | "join_required" | None,
    "table_count": int,
    "tables": ["table_a", "table_b"],
    "links": [...],           # current confirmed links
    "links_needed": int,      # how many links still needed
    "data_activated": bool,   # has user clicked Activate
    "can_activate": bool,     # all links satisfied
}
```

### Step 2: Backend — Upload Enforces 3-File Limit ✅ TODO
**File:** `services/sentinel/backend/app/routes/datasets.py`

In `upload_dataset()`: check current dataset count for workspace.
Reject with 400 if already at 3.

### Step 3: Backend — Join Config Becomes a List ✅ TODO
**File:** `services/sentinel/backend/app/routes/datasets.py`

- `save_join_config` accepts and stores a list of links
- Each link validated individually (matched_rows > 0)
- Connectivity check: all tables reachable through links
- Existing single-link config migrated to list format on read

### Step 4: Backend — Activate-Data Endpoint ✅ TODO
**File:** `services/sentinel/backend/app/routes/workspaces.py`

New `POST /workspaces/{id}/activate-data`:
- Checks `can_activate` (all links satisfied OR single table)
- Sets `data_activated: true` in workspace settings
- Returns workspace readiness status

### Step 5: Backend — Agent Checks Activation ✅ TODO
**File:** `services/sentinel/backend/app/agent.py`

In `_agent_loop`, after subscriber check and silo check:
- Check `data_activated` flag from workspace settings
- If not activated, broadcast `data_not_ready` status, sleep, continue
- Don't run any queries until workspace is activated

### Step 6: Backend — Agent Uses Join Config in Prompts ✅ TODO
**File:** `services/sentinel/backend/app/agent.py`

- Load join config from workspace settings on agent start
- Include link definitions in `_build_system_prompt()` and `_generate_sql()`
- e.g. "Tables are linked: orders.customer_id = customers.customer_id"
- Agent uses these known links instead of guessing join keys

### Step 7: Backend — Activate Response Includes Readiness ✅ TODO
**File:** `services/sentinel/backend/app/routes/workspaces.py`

`activate_workspace` response includes `data_ready` status so frontend
knows whether to show the dashboard or the data setup flow.

### Step 8: Backend — Fix Activate Clobber of Shared State ✅ TODO
**File:** `services/sentinel/backend/app/routes/workspaces.py`

`activate_workspace` currently calls `tile_store.load_tiles()` every time,
replacing live in-memory tiles with PG snapshot. Fix:
- Only load from PG if tile store is empty (first activation)
- If tiles already in memory (agent running, other users viewing),
  return the live state instead
- Same for silos — don't overwrite if already loaded

Interactions are per-user so always load the requesting user's from PG,
but don't clobber the store (merge, don't replace).

### Step 9: Backend — InteractionStore Per-User ✅ TODO
**File:** `services/sentinel/backend/app/tiles.py`

Current InteractionStore is one dict per workspace keyed by tile_id.
Needs to be keyed by (tile_id, user_id) or separate stores per user.
This supports:
- Multiple users viewing same workspace without clobbering
- Per-user interest tracking for future agent personalization
- Correct persist/load on workspace switch

### Step 10: Backend — get_stored_profiles Workspace Scoped ✅ TODO
**File:** `services/sentinel/backend/app/dataset_profiler.py`

`get_stored_profiles()` currently queries ALL datasets globally.
Add `workspace_id` parameter, filter by workspace.

### Step 11: Frontend — Data Setup Flow ✅ TODO
**Files:** `services/sentinel/frontend/src/components/DataManager.jsx`,
          `services/sentinel/frontend/src/components/JoinConfigPanel.jsx`

- Show uploaded files with status indicators
- Enforce 3-file limit in UI
- When 2+ files: show linking interface
  - User selects two tables to link
  - System suggests matching column names
  - User picks/confirms the join key
  - Validate button tests the join
  - Confirm button saves the link
  - Repeat for additional pairs if 3 files
- Visual connectivity indicator (which tables are linked)
- Activate button: disabled until can_activate is true
- After activation: transition to dashboard view

### Step 12: Frontend — Workspace Switch Shows Correct State ✅ TODO
**File:** `services/sentinel/frontend/src/App.jsx`

On workspace switch, check `data_activated`:
- If activated: show dashboard with tiles/agent
- If not activated: show data setup flow
- Don't force full remount if workspace is already live in memory

## Existing Bugs Fixed Before This Work

- [x] `3db3b08` Login crash — session_id vs token in set_session_workspace

## Notes

- Workspace is the central entity, not the user
- Multiple users can view the same workspace simultaneously
- Agent runs per-workspace, tied to SSE subscriber count
- Tiles are shared state; interactions are per-user
- DuckDB tables stay separate per file, joined at query time via configured links

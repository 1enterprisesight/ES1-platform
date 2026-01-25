# ES1 Platform Manager - Next Steps Plan

## Current Issues to Address

### 1. UI Navigation Visibility
The DAG Editor and Config tabs exist but may not be visible due to:
- User needs to click on "Workflows" in sidebar to see DAG Editor tab
- User needs to click on "Gateway" in sidebar to see Config tab
- **Action**: Verify UI build is updated, improve discoverability

### 2. KrakenD Config Shows Empty
The Config view shows no config because no deployments have been made yet.
- **Action**: Create a base KrakenD config or improve empty state UI

---

## New Features Requested

### 1. Package Enable/Disable UI
Allow administrators to enable/disable integrations (packages) from the UI.

**Packages to manage:**
- Airflow (Workflows)
- Langflow (AI Flows)
- Langfuse (Observability)
- n8n (Automation)

**Implementation:**
- Add Settings > Integrations page
- Toggle switches for each package
- Show connection status for each
- Store settings in database
- API updates to check enabled status

### 2. UI Branding/White-labeling
Allow customers to customize branding.

**Customizable elements:**
- Logo (sidebar, login page)
- Application name (currently "ES1 Platform")
- Primary color theme
- Favicon
- Company name in footer

**Implementation:**
- Add Settings > Branding page
- Store branding config in database
- Load branding on app startup
- CSS variables for theme colors
- Logo upload capability

### 3. n8n Integration Setup
Add n8n to the platform for workflow automation.

**Tasks:**
- Add n8n to docker-compose
- Create n8n module in backend (client, routes, schemas)
- Create n8n UI module
- Add n8n health check to dashboard
- Enable n8n in settings

### 4. Practical CloudSQL DAG Example
Create a real-world DAG that:
- Connects to GCP CloudSQL
- Extracts data
- Exposes via KrakenD endpoint

**Components:**
- Airflow connection for CloudSQL
- DAG template for database queries
- Auto-generate KrakenD endpoint for the DAG

---

## Implementation Priority

### Phase 1: Fix Current Issues (Immediate)
1. [ ] Rebuild and verify UI containers
2. [ ] Create base KrakenD config so Config view works
3. [ ] Fix toast API inconsistency
4. [ ] Improve empty states with clear CTAs

### Phase 2: Core Functionality (High Priority)
1. [ ] Add Integrations settings page with enable/disable toggles
2. [ ] Add Branding settings page
3. [ ] Create CloudSQL DAG template
4. [ ] Add "Deploy" button to dashboard

### Phase 3: n8n Integration (Medium Priority)
1. [ ] Add n8n docker-compose config
2. [ ] Create n8n backend module
3. [ ] Create n8n UI module
4. [ ] Integration testing

### Phase 4: Polish (Lower Priority)
1. [ ] Improve DAG editor with syntax highlighting
2. [ ] Add config diff visualization
3. [ ] Add deployment preview
4. [ ] Add audit logging

---

## Database Schema Updates Needed

### branding_config table (already exists but needs fields)
```sql
- logo_url: TEXT
- app_name: VARCHAR(100) DEFAULT 'ES1 Platform'
- primary_color: VARCHAR(7) DEFAULT '#3B82F6'
- company_name: VARCHAR(100)
- favicon_url: TEXT
```

### integration_settings table (new)
```sql
CREATE TABLE integration_settings (
  id UUID PRIMARY KEY,
  integration_name VARCHAR(50) NOT NULL UNIQUE,
  enabled BOOLEAN DEFAULT true,
  config JSONB DEFAULT '{}',
  health_status VARCHAR(20),
  last_health_check TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints Needed

### Branding
- GET /api/v1/settings/branding - Get branding config
- PUT /api/v1/settings/branding - Update branding config
- POST /api/v1/settings/branding/logo - Upload logo

### Integrations
- GET /api/v1/settings/integrations - List all integrations
- PUT /api/v1/settings/integrations/{name} - Update integration settings
- POST /api/v1/settings/integrations/{name}/test - Test connection

---

## Questions to Decide

1. Should branding be stored in database or environment variables?
2. Should n8n be required or optional?
3. What CloudSQL connection method to use (Cloud SQL Auth Proxy vs direct)?
4. Should we add RBAC for who can change branding/settings?

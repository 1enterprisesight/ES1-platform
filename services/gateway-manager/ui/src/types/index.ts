// Resource types - Matches backend API schema
export type ResourceType = 'workflow' | 'connection' | 'service';
export type ResourceStatus = 'active' | 'inactive';

export interface Resource {
  id: string;
  type: string;
  source: string;
  source_id: string;                    // Backend field name
  resource_metadata: Record<string, any>; // Backend field name (JSONB column)
  discovered_at: string;                 // Backend field name (ISO datetime)
  last_updated: string;                  // Backend field name (ISO datetime)
  status: string;
}

// Paginated list response
export interface ResourceListResponse {
  items: Resource[];
  total: number;
  page: number;
  page_size: number;
}

// Exposure types - Matches backend API schema
export type ExposureStatus = 'approved' | 'deployed' | 'removed';

export interface ExposureResource {
  id: string;
  type: string;
  source: string;
  source_id: string;
  name: string;
  metadata: Record<string, any>;
}

export interface Exposure {
  id: string;
  resource_id: string;
  settings: Record<string, any>;
  generated_config: Record<string, any>;
  status: ExposureStatus;
  created_by: string;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  resource?: ExposureResource;
}

export interface ExposureListResponse {
  items: Exposure[];
  total: number;
  page: number;
  page_size: number;
}

// Deployment types - Matches backend API schema
export type DeploymentStatus = 'in_progress' | 'succeeded' | 'failed' | 'rolled_back';

export interface Deployment {
  id: string;
  version_id: string;
  status: DeploymentStatus;
  deployed_by: string;
  deployed_at: string;
  completed_at: string | null;
  health_check_passed: boolean | null;
  error_message: string | null;
}

// Branding types
export interface BrandingConfig {
  companyName: string;
  productName: string;
  logoUrl: string;
  faviconUrl: string;
  colors: {
    primary: string;
    primaryHover: string;
    secondary: string;
    secondaryHover: string;
    accent: string;
    danger: string;
    success: string;
    warning: string;
    info: string;
  };
  fonts: {
    heading: string;
    body: string;
    mono: string;
  };
  terminology: {
    workflow: string;
    workflows: string;
    connection: string;
    connections: string;
    service: string;
    services: string;
    gateway: string;
    orchestrator: string;
    exposure: string;
    exposures: string;
    pushToGateway: string;
    approve: string;
    reject: string;
    deploy: string;
    deployment: string;
    rollback: string;
  };
}

// Activity types
export interface Activity {
  id: string;
  type: 'push' | 'approve' | 'reject' | 'deploy' | 'rollback';
  user: string;
  timestamp: string;
  description: string;
  resourceName?: string;
}

// Gateway Health types
export interface GatewayHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  podCount: number;
  lastDeploy: string;
  failedHealthChecks: number;
}

// Metrics types
export interface Metrics {
  totalEndpoints: number;
  activeEndpoints: number;
  pendingApprovals: number;
  failedDeployments: number;
  weeklyGrowth: {
    endpoints: number;
    deployments: number;
  };
}

// Exposure Change types - Matches backend API schema
export type ExposureChangeType = 'add' | 'modify' | 'remove';
export type ExposureChangeStatus = 'draft' | 'pending_approval' | 'approved' | 'rejected' | 'deployed';

export interface ExposureChange {
  id: string;
  exposure_id: string | null;
  resource_id: string;
  change_type: ExposureChangeType;
  settings_before: Record<string, any> | null;
  settings_after: Record<string, any> | null;
  status: ExposureChangeStatus;
  batch_id: string | null;
  requested_by: string;
  requested_at: string;
  submitted_for_approval_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  rejected_by: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  deployed_in_version_id: string | null;
  deployed_at: string | null;
}

export interface ExposureChangeListResponse {
  items: ExposureChange[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExposureChangeCreateRequest {
  resource_id: string;
  change_type: ExposureChangeType;
  exposure_id?: string | null;
  settings_before?: Record<string, any> | null;
  settings_after: Record<string, any>;
  requested_by: string;
}

// Config Version types
export interface ActiveConfig {
  version_id: string;
  version: number;
  deployed_at: string;
  deployed_by: string;
  endpoint_count: number;
  config_snapshot: Record<string, any>;
}

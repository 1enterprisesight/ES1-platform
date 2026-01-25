import type { Metrics, GatewayHealth, Activity } from '../types';

export const mockMetrics: Metrics = {
  totalEndpoints: 148,
  activeEndpoints: 145,
  pendingApprovals: 3,
  failedDeployments: 0,
  weeklyGrowth: {
    endpoints: 12,
    deployments: 9,
  },
};

export const mockGatewayHealth: GatewayHealth = {
  status: 'healthy',
  podCount: 2,
  lastDeploy: '2025-10-31T14:30:00Z',
  failedHealthChecks: 0,
};

export const mockActivities: Activity[] = [
  {
    id: '1',
    type: 'push',
    user: 'john@company.com',
    timestamp: '2025-10-31T14:28:00Z',
    description: 'Pushed workflow',
    resourceName: 'customer_onboarding',
  },
  {
    id: '2',
    type: 'deploy',
    user: 'admin@company.com',
    timestamp: '2025-10-31T14:15:00Z',
    description: 'Deployed 3 endpoints',
  },
  {
    id: '3',
    type: 'approve',
    user: 'admin@company.com',
    timestamp: '2025-10-31T09:00:00Z',
    description: 'Approved exposure',
    resourceName: 'daily_report_generator',
  },
  {
    id: '4',
    type: 'push',
    user: 'sarah@company.com',
    timestamp: '2025-10-30T16:00:00Z',
    description: 'Pushed connection',
    resourceName: 'postgres_analytics',
  },
  {
    id: '5',
    type: 'deploy',
    user: 'admin@company.com',
    timestamp: '2025-10-30T09:15:00Z',
    description: 'Deployed 5 endpoints',
  },
];

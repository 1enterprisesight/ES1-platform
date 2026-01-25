import type { Deployment } from '../types';

export const mockDeployments: Deployment[] = [
  {
    id: '1',
    version_id: 'v1.0.3',
    status: 'succeeded',
    deployed_by: 'admin@company.com',
    deployed_at: '2025-10-31T14:30:15Z',
    completed_at: '2025-10-31T14:31:02Z',
    health_check_passed: true,
    error_message: null,
  },
  {
    id: '2',
    version_id: 'v1.0.2',
    status: 'succeeded',
    deployed_by: 'admin@company.com',
    deployed_at: '2025-10-30T09:15:00Z',
    completed_at: '2025-10-30T09:15:52Z',
    health_check_passed: true,
    error_message: null,
  },
  {
    id: '3',
    version_id: 'v1.0.1',
    status: 'failed',
    deployed_by: 'sarah@company.com',
    deployed_at: '2025-10-29T16:45:00Z',
    completed_at: '2025-10-29T16:47:30Z',
    health_check_passed: false,
    error_message: 'Pod krakend-7d8f9b-def34 failed readiness probe - Configuration syntax error',
  },
];

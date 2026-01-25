import type { Exposure } from '../types';

// Mock exposures - Updated to match backend API schema
export const mockExposures: Exposure[] = [
  {
    id: '1',
    resource_id: '1',
    settings: { rate_limit: 50 },
    generated_config: {
      endpoint: '/gateway/v1/workflows/trigger/customer_onboarding',
      method: 'POST',
    },
    status: 'deployed',
    created_by: 'john@company.com',
    created_at: '2025-10-31T10:00:00Z',
    approved_by: 'admin@company.com',
    approved_at: '2025-10-31T10:15:00Z',
    rejection_reason: null,
  },
  {
    id: '2',
    resource_id: '4',
    settings: { rate_limit: 10 },
    generated_config: {
      endpoint: '/gateway/v1/workflows/trigger/daily_report_generator',
      method: 'POST',
    },
    status: 'approved',
    created_by: 'jane@company.com',
    created_at: '2025-10-30T16:00:00Z',
    approved_by: 'admin@company.com',
    approved_at: '2025-10-31T09:00:00Z',
    rejection_reason: null,
  },
  {
    id: '3',
    resource_id: '6',
    settings: { rate_limit: 50 },
    generated_config: {
      endpoint: '/gateway/v1/workflows/trigger/invoice_processor',
      method: 'POST',
    },
    status: 'deployed',
    created_by: 'admin@company.com',
    created_at: '2025-10-29T11:00:00Z',
    approved_by: 'admin@company.com',
    approved_at: '2025-10-29T11:05:00Z',
    rejection_reason: null,
  },
];

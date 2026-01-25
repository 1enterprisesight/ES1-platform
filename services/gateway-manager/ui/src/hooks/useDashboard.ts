import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

/**
 * Dashboard metrics response
 */
export interface DashboardMetrics {
  total_endpoints: number;
  active_endpoints: number;
  pending_approvals: number;
  failed_deployments: number;
  total_resources: number;
  active_resources: number;
}

/**
 * Gateway health response
 */
export interface GatewayHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  pod_count: number;
  running_pods: number;
  last_deploy: string | null;
  failed_health_checks: number;
}

/**
 * Event/Activity response
 */
export interface Event {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  user_id: string | null;
  event_metadata: Record<string, any> | null;
  created_at: string;
}

/**
 * Hook to fetch dashboard metrics
 */
export function useDashboardMetrics() {
  return useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: () => apiFetch<DashboardMetrics>('/metrics/dashboard'),
  });
}

/**
 * Hook to fetch gateway health
 */
export function useGatewayHealth() {
  return useQuery({
    queryKey: ['gateway', 'health'],
    queryFn: () => apiFetch<GatewayHealth>('/gateway/health'),
  });
}

/**
 * Hook to fetch recent activity/events
 */
export function useRecentActivity(limit: number = 20) {
  return useQuery({
    queryKey: ['events', limit],
    queryFn: () => apiFetch<Event[]>(`/events?limit=${limit}`),
  });
}

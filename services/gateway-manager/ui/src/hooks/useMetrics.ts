import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

interface GatewayHealth {
  status: string;
  uptime_available: boolean | null;
  goroutines: number | null;
  memory_bytes: number | null;
  total_requests: number | null;
  metrics_count: number | null;
  error: string | null;
}

interface GatewayRequests {
  total_requests: number | null;
  by_status_code: Record<string, number> | null;
  success_rate: number | null;
  error: string | null;
}

interface EndpointMetric {
  endpoint: string;
  total_requests: number;
  success_requests: number;
  error_requests: number;
  error_rate: number;
}

interface TopEndpoints {
  endpoints: EndpointMetric[];
  total_endpoints: number;
  error: string | null;
}

/**
 * Hook to fetch KrakenD gateway health metrics
 */
export function useGatewayHealth() {
  return useQuery({
    queryKey: ['gateway-health'],
    queryFn: () => apiFetch<GatewayHealth>('/metrics/gateway/health'),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Hook to fetch KrakenD gateway request metrics
 */
export function useGatewayRequests() {
  return useQuery({
    queryKey: ['gateway-requests'],
    queryFn: () => apiFetch<GatewayRequests>('/metrics/gateway/requests'),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Hook to fetch top endpoints by request count
 */
export function useTopEndpoints(limit: number = 10) {
  return useQuery({
    queryKey: ['top-endpoints', limit],
    queryFn: () => apiFetch<TopEndpoints>(`/metrics/endpoints/top?limit=${limit}`),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

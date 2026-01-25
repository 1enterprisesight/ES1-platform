import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

/**
 * Resource info embedded in exposure response
 */
export interface ResourceInfo {
  id: string;
  type: string;
  source: string;
  source_id: string;
  name: string;
  metadata: Record<string, any>;
}

/**
 * Exposure response from API (matches backend schema)
 */
export interface ExposureResponse {
  id: string;
  resource_id: string;
  settings: Record<string, any>;
  generated_config: Record<string, any>;
  status: 'pending' | 'approved' | 'deployed' | 'rejected';
  created_by: string;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  resource: ResourceInfo | null;
}

/**
 * Paginated exposure list response
 */
export interface ExposureListResponse {
  items: ExposureResponse[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Hook to fetch exposures with pagination and filtering
 */
export function useExposures(
  page: number = 1,
  pageSize: number = 50,
  status?: string
) {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  if (status) {
    params.append('status', status);
  }

  return useQuery({
    queryKey: ['exposures', page, pageSize, status],
    queryFn: () => apiFetch<ExposureListResponse>(`/exposures?${params.toString()}`),
  });
}

/**
 * Hook to fetch a single exposure by ID
 */
export function useExposure(exposureId: string) {
  return useQuery({
    queryKey: ['exposures', exposureId],
    queryFn: () => apiFetch<ExposureResponse>(`/exposures/${exposureId}`),
    enabled: !!exposureId,
  });
}

/**
 * Hook to approve an exposure
 */
export function useApproveExposure() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (exposureId: string) =>
      apiFetch<ExposureResponse>(`/exposures/${exposureId}/approve`, {
        method: 'POST',
      }),
    onSuccess: () => {
      // Invalidate and refetch exposures list
      queryClient.invalidateQueries({ queryKey: ['exposures'] });
      // Also invalidate dashboard metrics (pending approvals count)
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] });
    },
  });
}

/**
 * Hook to reject an exposure
 */
export function useRejectExposure() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ exposureId, reason }: { exposureId: string; reason: string }) =>
      apiFetch<ExposureResponse>(`/exposures/${exposureId}/reject?reason=${encodeURIComponent(reason)}`, {
        method: 'POST',
      }),
    onSuccess: () => {
      // Invalidate and refetch exposures list
      queryClient.invalidateQueries({ queryKey: ['exposures'] });
      // Also invalidate dashboard metrics (pending approvals count)
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'metrics'] });
    },
  });
}

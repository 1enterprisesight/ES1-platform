import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';
import type { ResourceListResponse } from '../types';

/**
 * Hook to fetch resources from the API
 */
export function useResources() {
  return useQuery({
    queryKey: ['resources'],
    queryFn: () => apiFetch<ResourceListResponse>('/resources'),
  });
}

/**
 * Hook to sync resources from Airflow
 */
export function useSyncAirflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiFetch('/integrations/airflow/sync', { method: 'POST' }),
    onSuccess: () => {
      // Refetch resources after successful sync
      queryClient.invalidateQueries({ queryKey: ['resources'] });
    },
  });
}

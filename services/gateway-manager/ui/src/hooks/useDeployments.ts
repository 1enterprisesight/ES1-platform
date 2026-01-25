import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';
import type { Deployment } from '../types';

/**
 * Hook to fetch deployments history
 */
export function useDeployments(limit: number = 20) {
  return useQuery({
    queryKey: ['deployments', limit],
    queryFn: () => apiFetch<Deployment[]>(`/deployments?limit=${limit}`),
  });
}

/**
 * Hook to fetch a single deployment by ID
 */
export function useDeployment(deploymentId: string) {
  return useQuery({
    queryKey: ['deployments', deploymentId],
    queryFn: () => apiFetch<Deployment>(`/deployments/${deploymentId}`),
    enabled: !!deploymentId,
  });
}

/**
 * Hook to deploy approved changes
 */
export function useDeployChanges() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deployedBy, commitMessage }: { deployedBy: string; commitMessage?: string }) =>
      apiFetch('/deployments/deploy-changes', {
        method: 'POST',
        body: JSON.stringify({
          deployed_by: deployedBy,
          commit_message: commitMessage,
        }),
      }),
    onSuccess: () => {
      // Invalidate queries to refetch data
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      queryClient.invalidateQueries({ queryKey: ['exposure-changes'] });
      queryClient.invalidateQueries({ queryKey: ['exposures'] });
    },
  });
}

/**
 * Hook to redeploy an existing config version
 */
export function useRedeployConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ versionId, deployedBy }: { versionId: string; deployedBy: string }) =>
      apiFetch(`/deployments/redeploy/${versionId}`, {
        method: 'POST',
        body: JSON.stringify({
          deployed_by: deployedBy,
          commit_message: `Redeploy config version`,
        }),
      }),
    onSuccess: () => {
      // Invalidate queries to refetch data
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      queryClient.invalidateQueries({ queryKey: ['config-versions'] });
      queryClient.invalidateQueries({ queryKey: ['exposures'] });
    },
  });
}

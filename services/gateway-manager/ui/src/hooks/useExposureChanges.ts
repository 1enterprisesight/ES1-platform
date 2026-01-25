import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';
import type {
  ExposureListResponse,
  ExposureChangeListResponse,
  ExposureChangeCreateRequest,
  ExposureChange,
} from '../types';

/**
 * Hook to fetch all exposures
 */
export function useExposures() {
  return useQuery({
    queryKey: ['exposures'],
    queryFn: () => apiFetch<ExposureListResponse>('/exposures'),
  });
}

/**
 * Hook to fetch exposure changes with optional filters
 */
export function useExposureChanges(params?: {
  status?: string;
  batch_id?: string;
}) {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.batch_id) queryParams.append('batch_id', params.batch_id);

  const queryString = queryParams.toString();
  const url = queryString ? `/exposure-changes?${queryString}` : '/exposure-changes';

  return useQuery({
    queryKey: ['exposure-changes', params],
    queryFn: () => apiFetch<ExposureChangeListResponse>(url),
  });
}

/**
 * Hook to create a new exposure change (draft)
 */
export function useCreateExposureChange() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ExposureChangeCreateRequest) =>
      apiFetch<ExposureChange>('/exposure-changes', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      // Invalidate queries to refetch data
      queryClient.invalidateQueries({ queryKey: ['exposure-changes'] });
      queryClient.invalidateQueries({ queryKey: ['exposures'] });
    },
  });
}

/**
 * Hook to delete an exposure change (drafts only)
 */
export function useDeleteExposureChange() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (changeId: string) =>
      apiFetch(`/exposure-changes/${changeId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-changes'] });
    },
  });
}

/**
 * Hook to submit a batch of draft changes for approval
 */
export function useSubmitBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (changeIds: string[]) =>
      apiFetch('/exposure-changes/submit-batch', {
        method: 'POST',
        body: JSON.stringify({ change_ids: changeIds }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-changes'] });
    },
  });
}

/**
 * Hook to approve a batch of pending changes
 */
export function useApproveBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ batchId, approvedBy }: { batchId: string; approvedBy: string }) =>
      apiFetch(`/exposure-changes/batch/${batchId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approved_by: approvedBy }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-changes'] });
    },
  });
}

/**
 * Hook to reject a batch of pending changes
 */
export function useRejectBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ batchId, rejectedBy, reason }: { batchId: string; rejectedBy: string; reason: string }) =>
      apiFetch(`/exposure-changes/batch/${batchId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ rejected_by: rejectedBy, reason }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-changes'] });
    },
  });
}

/**
 * Hook to fetch complete config preview for a batch
 */
export function useBatchConfigPreview(batchId: string | null) {
  return useQuery({
    queryKey: ['batch-config-preview', batchId],
    queryFn: () =>
      apiFetch<{ batch_id: string; config_snapshot: any; summary: any }>(
        `/exposure-changes/batch/${batchId}/preview`,
        { method: 'POST' }
      ),
    enabled: !!batchId, // Only fetch when batchId is provided
    staleTime: 60000, // Cache for 1 minute
  });
}

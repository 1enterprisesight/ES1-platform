import { useQuery } from '@tanstack/react-query';

const API_BASE = '/api/v1';

interface ActiveConfig {
  version_id: string;
  version: number;
  deployed_at: string;
  deployed_by: string;
  endpoint_count: number;
  config_snapshot: Record<string, any>;
}

export const useActiveConfig = () => {
  return useQuery<ActiveConfig>({
    queryKey: ['config-versions', 'active'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/config-versions/active`);
      if (!response.ok) {
        throw new Error('Failed to fetch active config');
      }
      return response.json();
    },
    staleTime: 30000, // Cache for 30 seconds
  });
};

export const useConfigVersion = (versionId: string | null) => {
  return useQuery<ActiveConfig>({
    queryKey: ['config-versions', versionId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/config-versions/${versionId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch config version');
      }
      return response.json();
    },
    enabled: !!versionId, // Only fetch when versionId is provided
    staleTime: 60000, // Cache for 1 minute
  });
};

export const usePendingConfigVersions = () => {
  return useQuery<ActiveConfig[]>({
    queryKey: ['config-versions', 'pending'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/config-versions/pending`);
      if (!response.ok) {
        throw new Error('Failed to fetch pending config versions');
      }
      return response.json();
    },
    staleTime: 10000, // Cache for 10 seconds (more dynamic than active config)
  });
};

export const useApprovedConfigVersions = () => {
  return useQuery<ActiveConfig[]>({
    queryKey: ['config-versions', 'approved'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/config-versions/approved`);
      if (!response.ok) {
        throw new Error('Failed to fetch approved config versions');
      }
      return response.json();
    },
    staleTime: 10000, // Cache for 10 seconds
  });
};

import { useQuery } from '@tanstack/react-query';

const API_BASE = '/api/v1';

interface Event {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  user_id: string | null;
  event_metadata: Record<string, any> | null;
  created_at: string;
}

export const useEvents = (limit: number = 10) => {
  return useQuery<Event[]>({
    queryKey: ['events', limit],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/events?limit=${limit}`);
      if (!response.ok) {
        throw new Error('Failed to fetch events');
      }
      return response.json();
    },
    staleTime: 30000, // Cache for 30 seconds
    refetchInterval: 60000, // Refetch every minute
  });
};

/**
 * Centralized API client for ES1 Platform Manager
 *
 * Provides typed API access with automatic URL construction from config.
 * Eliminates hardcoded URLs throughout the codebase.
 */

import { config, apiUrl, agentRouterUrl } from '@/config';
import { getStoredApiKey } from '@/shared/contexts/AuthContext';

// =============================================================================
// Types
// =============================================================================

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

export interface FetchOptions extends RequestInit {
  /** Skip automatic JSON parsing of response */
  raw?: boolean;
}

// =============================================================================
// Base fetch wrapper
// =============================================================================

/**
 * Base fetch function with error handling
 */
async function baseFetch<T>(url: string, options: FetchOptions = {}): Promise<T> {
  const { raw, ...fetchOptions } = options;

  // Inject API key header if available
  const apiKey = getStoredApiKey();
  const authHeaders: Record<string, string> = apiKey ? { 'X-API-Key': apiKey } : {};

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...fetchOptions.headers,
    },
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }

    const error: ApiError = {
      status: response.status,
      message: response.statusText,
      detail,
    };
    throw error;
  }

  if (raw) {
    return response as unknown as T;
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return null as unknown as T;
  }

  return JSON.parse(text);
}

// =============================================================================
// Platform API Client
// =============================================================================

/**
 * Platform Manager API client
 *
 * @example
 * // GET /api/v1/agents
 * const agents = await platformApi.get<Agent[]>('agents');
 *
 * // POST /api/v1/agents
 * const agent = await platformApi.post<Agent>('agents', { name: 'New Agent' });
 */
export const platformApi = {
  get<T>(path: string, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(apiUrl(path), { ...options, method: 'GET' });
  },

  post<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(apiUrl(path), {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  put<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(apiUrl(path), {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(apiUrl(path), {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  delete<T>(path: string, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(apiUrl(path), { ...options, method: 'DELETE' });
  },
};

// =============================================================================
// Agent Router API Client
// =============================================================================

/**
 * Agent Router API client
 *
 * @example
 * // GET /agent-router/agents
 * const agents = await agentRouterApi.get<Agent[]>('agents');
 *
 * // POST /agent-router/tasks
 * const task = await agentRouterApi.post<Task>('tasks', { ... });
 */
export const agentRouterApi = {
  get<T>(path: string, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(agentRouterUrl(path), { ...options, method: 'GET' });
  },

  post<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(agentRouterUrl(path), {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  put<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(agentRouterUrl(path), {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(agentRouterUrl(path), {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  delete<T>(path: string, options?: FetchOptions): Promise<T> {
    return baseFetch<T>(agentRouterUrl(path), { ...options, method: 'DELETE' });
  },
};

// =============================================================================
// External Service URL Helpers
// =============================================================================

/**
 * Open an external service in a new browser tab
 *
 * @example
 * openExternalService('grafana');
 * openExternalService('crewaiStudio');
 */
export function openExternalService(
  service: keyof typeof config extends () => infer R
    ? R extends { services: infer S }
      ? keyof S
      : never
    : never
): void {
  const cfg = config();
  const url = cfg.services[service as keyof typeof cfg.services];
  if (url) {
    window.open(url, '_blank');
  }
}

/**
 * Get the URL for an external service
 *
 * @example
 * const grafanaUrl = getExternalServiceUrl('grafana');
 * // Returns 'http://localhost:3002' or production URL
 */
export function getExternalServiceUrl(
  service: keyof ReturnType<typeof config>['services']
): string {
  return config().services[service];
}

/**
 * Check if a feature is enabled
 *
 * @example
 * if (isFeatureEnabled('enableN8n')) {
 *   // Show n8n integration
 * }
 */
export function isFeatureEnabled(
  feature: keyof ReturnType<typeof config>['features']
): boolean {
  return config().features[feature];
}

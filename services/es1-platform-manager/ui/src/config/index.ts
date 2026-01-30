import type { RuntimeConfig } from './types';
import { defaultConfig } from './defaults';

export type { RuntimeConfig } from './types';
export { defaultConfig } from './defaults';

/**
 * Deep merge helper for config objects
 */
function deepMerge<T extends Record<string, unknown>>(
  target: T,
  source: Partial<T>
): T {
  const result = { ...target };

  for (const key in source) {
    if (Object.prototype.hasOwnProperty.call(source, key)) {
      const sourceValue = source[key];
      const targetValue = target[key];

      if (
        sourceValue &&
        typeof sourceValue === 'object' &&
        !Array.isArray(sourceValue) &&
        targetValue &&
        typeof targetValue === 'object' &&
        !Array.isArray(targetValue)
      ) {
        result[key] = deepMerge(
          targetValue as Record<string, unknown>,
          sourceValue as Record<string, unknown>
        ) as T[Extract<keyof T, string>];
      } else if (sourceValue !== undefined) {
        result[key] = sourceValue as T[Extract<keyof T, string>];
      }
    }
  }

  return result;
}

/**
 * Get the runtime configuration
 *
 * Merges window.__ES1_CONFIG__ (injected at runtime) with defaults.
 * This allows partial overrides - you don't need to specify all values.
 *
 * @example
 * // In a component
 * import { getConfig } from '@/config';
 *
 * const config = getConfig();
 * window.open(config.services.grafana, '_blank');
 */
export function getConfig(): RuntimeConfig {
  const runtimeConfig = window.__ES1_CONFIG__ || {};
  return deepMerge(defaultConfig, runtimeConfig as Partial<RuntimeConfig>);
}

/**
 * Singleton config instance for convenience
 * Use getConfig() if you need fresh values (rare)
 */
let _configInstance: RuntimeConfig | null = null;

export function config(): RuntimeConfig {
  if (!_configInstance) {
    _configInstance = getConfig();
  }
  return _configInstance;
}

/**
 * Helper to build full API URLs
 *
 * @example
 * // Returns '/api/v1/agents'
 * apiUrl('agents')
 *
 * // Returns '/api/v1/agents/123/tasks'
 * apiUrl('agents', '123', 'tasks')
 */
export function apiUrl(...segments: string[]): string {
  const baseUrl = config().api.platform;
  const path = segments.filter(Boolean).join('/');
  return path ? `${baseUrl}/${path}` : baseUrl;
}

/**
 * Helper to build Agent Router API URLs
 *
 * @example
 * // Returns '/agent-router/agents'
 * agentRouterUrl('agents')
 *
 * // Returns '/agent-router/networks/123'
 * agentRouterUrl('networks', '123')
 */
export function agentRouterUrl(...segments: string[]): string {
  const baseUrl = config().api.agentRouter;
  const path = segments.filter(Boolean).join('/');
  return path ? `${baseUrl}/${path}` : baseUrl;
}

/**
 * Get external service URL by name
 *
 * @example
 * // Returns 'http://localhost:3002' (or production URL)
 * serviceUrl('grafana')
 */
export function serviceUrl(
  service: keyof RuntimeConfig['services']
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
  feature: keyof RuntimeConfig['features']
): boolean {
  return config().features[feature];
}

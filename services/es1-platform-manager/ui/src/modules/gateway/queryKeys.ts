/**
 * Centralized React Query key factory for the gateway module.
 *
 * Keys are hierarchical — invalidating a parent prefix clears all children.
 * e.g. `queryClient.invalidateQueries({ queryKey: gatewayKeys.versions.all })`
 * clears both `versions.list` and `versions.pending`.
 */
export const gatewayKeys = {
  all: ['gateway'] as const,

  health: ['gateway', 'health'] as const,

  config: {
    all: ['gateway', 'config'] as const,
    state: ['gateway', 'config', 'state'] as const,
    current: ['gateway', 'config', 'current'] as const,
    diff: (a: number | null, b: number | null) =>
      ['gateway', 'config', 'diff', a, b] as const,
  },

  versions: {
    all: ['gateway', 'versions'] as const,
    list: ['gateway', 'versions', 'list'] as const,
    pending: ['gateway', 'versions', 'pending'] as const,
  },

  deployments: {
    all: ['gateway', 'deployments'] as const,
    list: (page: number) => ['gateway', 'deployments', 'list', page] as const,
    recent: ['gateway', 'deployments', 'recent'] as const,
  },

  changeSets: {
    all: ['gateway', 'changeSets'] as const,
    detail: (id: string | null) =>
      ['gateway', 'changeSets', 'detail', id] as const,
    submitted: ['gateway', 'changeSets', 'submitted'] as const,
  },

  resources: {
    all: ['gateway', 'resources'] as const,
    list: (page: number) => ['gateway', 'resources', 'list', page] as const,
    available: ['gateway', 'resources', 'available'] as const,
  },

  exposures: {
    all: ['gateway', 'exposures'] as const,
    list: (page: number, status: string | null) =>
      ['gateway', 'exposures', 'list', page, status] as const,
  },
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, Globe, Shield, Zap, Filter, Edit } from 'lucide-react'
import { Button, Card, CardHeader, CardTitle, CardContent, Badge } from '@/design-system/components'
import { StatusIndicator } from '@/design-system/components/StatusIndicator'

interface RouteInfo {
  endpoint: string
  method: string
  managed_by: string
  backend_host?: string
  url_pattern?: string
  description?: string
  resource_type?: string
  resource_source?: string
  resource_name?: string
  exposure_id?: string
  settings?: Record<string, unknown>
}

interface ConfigState {
  active_version: number | null
  deployed_at: string | null
  deployed_by: string | null
  global_config: Record<string, unknown>
  base_routes: RouteInfo[]
  dynamic_routes: RouteInfo[]
  total_endpoints: number
  base_endpoint_count: number
  dynamic_endpoint_count: number
}

interface GatewayHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  mode: string
  pod_count: number
  running_pods: number
}

export function CurrentStateView() {
  const navigate = useNavigate()
  const [routeFilter, setRouteFilter] = useState<'all' | 'base' | 'dynamic'>('all')
  const [methodFilter, setMethodFilter] = useState<string>('')

  const { data: state, isLoading, refetch } = useQuery<ConfigState>({
    queryKey: ['gateway-config-state'],
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/config/state')
      if (!res.ok) throw new Error('Failed to fetch config state')
      return res.json()
    },
  })

  const { data: health } = useQuery<GatewayHealth>({
    queryKey: ['gateway-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/health')
      if (!res.ok) throw new Error('Failed to fetch health')
      return res.json()
    },
    refetchInterval: 10000,
  })

  const allRoutes = [
    ...(state?.base_routes || []),
    ...(state?.dynamic_routes || []),
  ]

  const filteredRoutes = allRoutes.filter((route) => {
    if (routeFilter === 'base' && route.managed_by !== 'base') return false
    if (routeFilter === 'dynamic' && route.managed_by !== 'platform-manager') return false
    if (methodFilter && route.method !== methodFilter) return false
    return true
  })

  const uniqueMethods = [...new Set(allRoutes.map((r) => r.method).filter(Boolean))]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold">Gateway Overview</h2>
          <p className="text-sm text-muted-foreground">
            Complete view of the running gateway configuration
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button size="sm" onClick={() => navigate('/gateway/edit')}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Configuration
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : (
        <>
          {/* Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Gateway Status</CardTitle>
                <Shield className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <StatusIndicator status={health?.status || 'unhealthy'} />
                  <span className="text-2xl font-bold capitalize">
                    {health?.status || 'Unknown'}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {health?.mode === 'docker' ? 'Docker Compose' : 'Kubernetes'} &middot;{' '}
                  {health?.running_pods ?? 0}/{health?.pod_count ?? 0} pods
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Active Version</CardTitle>
                <Globe className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {state?.active_version != null ? `v${state.active_version}` : 'None'}
                </div>
                {state?.deployed_at && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Deployed {new Date(state.deployed_at).toLocaleString()}
                    {state.deployed_by && ` by ${state.deployed_by}`}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Total Endpoints</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{state?.total_endpoints ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {state?.base_endpoint_count ?? 0} base + {state?.dynamic_endpoint_count ?? 0} dynamic
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Dynamic Routes</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{state?.dynamic_endpoint_count ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  User-configured exposure routes
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Global Config */}
          {state?.global_config && Object.keys(state.global_config).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Global Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  {state.global_config.timeout && (
                    <div>
                      <span className="text-muted-foreground">Timeout:</span>{' '}
                      <span className="font-medium">{String(state.global_config.timeout)}</span>
                    </div>
                  )}
                  {state.global_config.cache_ttl && (
                    <div>
                      <span className="text-muted-foreground">Cache TTL:</span>{' '}
                      <span className="font-medium">{String(state.global_config.cache_ttl)}</span>
                    </div>
                  )}
                  {state.global_config.output_encoding && (
                    <div>
                      <span className="text-muted-foreground">Encoding:</span>{' '}
                      <span className="font-medium">{String(state.global_config.output_encoding)}</span>
                    </div>
                  )}
                  {state.global_config.port && (
                    <div>
                      <span className="text-muted-foreground">Port:</span>{' '}
                      <span className="font-medium">{String(state.global_config.port)}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Route Table */}
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-sm font-medium">
                  All Routes ({filteredRoutes.length})
                </CardTitle>
                <div className="flex gap-2 items-center">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <div className="flex border rounded overflow-hidden text-xs">
                    {(['all', 'base', 'dynamic'] as const).map((f) => (
                      <button
                        key={f}
                        className={`px-2 py-1 ${routeFilter === f ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}
                        onClick={() => setRouteFilter(f)}
                      >
                        {f === 'all' ? 'All' : f === 'base' ? 'Base' : 'Dynamic'}
                      </button>
                    ))}
                  </div>
                  {uniqueMethods.length > 0 && (
                    <select
                      className="text-xs border rounded px-2 py-1 bg-background"
                      value={methodFilter}
                      onChange={(e) => setMethodFilter(e.target.value)}
                    >
                      <option value="">All Methods</option>
                      {uniqueMethods.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 pr-4 font-medium text-muted-foreground">Endpoint</th>
                      <th className="pb-2 pr-4 font-medium text-muted-foreground">Method</th>
                      <th className="pb-2 pr-4 font-medium text-muted-foreground">Type</th>
                      <th className="pb-2 pr-4 font-medium text-muted-foreground">Backend</th>
                      <th className="pb-2 font-medium text-muted-foreground">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRoutes.map((route, i) => (
                      <tr key={`${route.endpoint}-${route.method}-${i}`} className="border-b last:border-0">
                        <td className="py-2 pr-4 font-mono text-xs">{route.endpoint}</td>
                        <td className="py-2 pr-4">
                          <Badge variant="secondary" className="text-xs">
                            {route.method}
                          </Badge>
                        </td>
                        <td className="py-2 pr-4">
                          <Badge
                            variant={route.managed_by === 'base' ? 'secondary' : 'info'}
                            className="text-xs"
                          >
                            {route.managed_by === 'base' ? 'Base' : 'Dynamic'}
                          </Badge>
                        </td>
                        <td className="py-2 pr-4 text-xs text-muted-foreground">
                          {route.backend_host || route.resource_name || '-'}
                        </td>
                        <td className="py-2 text-xs text-muted-foreground">
                          {route.resource_source || route.description || '-'}
                        </td>
                      </tr>
                    ))}
                    {filteredRoutes.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-muted-foreground">
                          No routes match the current filter.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

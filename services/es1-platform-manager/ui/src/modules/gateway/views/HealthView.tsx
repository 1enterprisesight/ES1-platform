import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Server, Activity, Cpu, HardDrive } from 'lucide-react'
import { gatewayKeys } from '../queryKeys'
import { Button, Card, CardHeader, CardTitle, CardContent } from '@/design-system/components'
import { StatusIndicator } from '@/design-system/components/StatusIndicator'

interface GatewayHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  mode: string
  pod_count: number
  running_pods: number
  failed_health_checks: number
  error?: string
}

export function HealthView() {
  const { data, isLoading, refetch, dataUpdatedAt } = useQuery<GatewayHealth>({
    queryKey: gatewayKeys.health,
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/health')
      if (!res.ok) throw new Error('Failed to fetch gateway health')
      return res.json()
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold">Gateway Health</h2>
          <p className="text-sm text-muted-foreground">
            Last updated: {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : 'Never'}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Overall Status</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <StatusIndicator status={data?.status || 'unhealthy'} />
                <span className="text-2xl font-bold capitalize">
                  {data?.status || 'Unknown'}
                </span>
              </div>
              {data?.error && (
                <p className="text-sm text-red-500 mt-2">{data.error}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Runtime Mode</CardTitle>
              <Server className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold capitalize">
                {data?.mode || 'Unknown'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {data?.mode === 'docker' ? 'Docker Compose' : 'Kubernetes'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Pod Count</CardTitle>
              <Cpu className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {data?.running_pods ?? 0} / {data?.pod_count ?? 0}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Running / Total
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Failed Checks</CardTitle>
              <HardDrive className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {data?.failed_health_checks ?? 0}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Health check failures
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Health Details */}
      <Card>
        <CardHeader>
          <CardTitle>Health Details</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="bg-muted p-4 rounded-md overflow-auto text-sm">
            {JSON.stringify(data, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  )
}

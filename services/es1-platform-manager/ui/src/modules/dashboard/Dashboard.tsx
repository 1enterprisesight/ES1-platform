import { useQuery } from '@tanstack/react-query'
import { Network, Workflow, Brain, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/design-system/components'
import { StatusIndicator } from '@/design-system/components/StatusIndicator'

interface GatewayStatus {
  health: {
    status: 'healthy' | 'degraded' | 'unhealthy'
    mode: string
    pod_count: number
    running_pods: number
  }
  active_version: number | null
  pending_approvals: number
  ready_to_deploy: number
}

export function Dashboard() {
  const { data: gatewayStatus, isLoading } = useQuery<GatewayStatus>({
    queryKey: ['gateway-status'],
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/status')
      if (!res.ok) throw new Error('Failed to fetch gateway status')
      return res.json()
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your ES1 Platform</p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Gateway Status</CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-2xl font-bold">...</div>
            ) : (
              <div className="flex items-center gap-2">
                <StatusIndicator
                  status={gatewayStatus?.health.status || 'unhealthy'}
                />
                <span className="text-2xl font-bold capitalize">
                  {gatewayStatus?.health.status || 'Unknown'}
                </span>
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Mode: {gatewayStatus?.health.mode || 'unknown'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Active Version</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {gatewayStatus?.active_version ? `v${gatewayStatus.active_version}` : 'None'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Currently deployed configuration
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pending Approvals</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {gatewayStatus?.pending_approvals ?? 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Exposures awaiting approval
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Ready to Deploy</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {gatewayStatus?.ready_to_deploy ?? 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Approved exposures ready for deployment
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="hover:border-primary/50 transition-colors cursor-pointer">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="p-3 rounded-lg bg-blue-100 dark:bg-blue-900/20">
              <Network className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 className="font-semibold">API Gateway</h3>
              <p className="text-sm text-muted-foreground">
                Manage endpoints and deployments
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/50 transition-colors cursor-pointer opacity-50">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="p-3 rounded-lg bg-green-100 dark:bg-green-900/20">
              <Workflow className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h3 className="font-semibold">Workflows</h3>
              <p className="text-sm text-muted-foreground">
                Airflow DAGs and pipelines
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/50 transition-colors cursor-pointer opacity-50">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="p-3 rounded-lg bg-purple-100 dark:bg-purple-900/20">
              <Brain className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="font-semibold">AI Flows</h3>
              <p className="text-sm text-muted-foreground">
                Langflow integrations
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

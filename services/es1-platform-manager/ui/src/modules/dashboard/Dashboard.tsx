import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Network, Workflow, Brain, Zap, Activity,
  CheckCircle, Clock, AlertCircle, Settings,
  BarChart3, Server, Database, HardDrive
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Skeleton, SkeletonServiceCard } from '@/design-system/components'
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

interface ServiceHealth {
  status: 'healthy' | 'unhealthy' | 'setup_required' | 'disabled'
  message?: string | null
  error?: string | null
}

function ServiceStatusCard({
  name,
  icon: Icon,
  health,
  isLoading,
  href,
  description,
  colorClass
}: {
  name: string
  icon: React.ComponentType<{ className?: string }>
  health: ServiceHealth | undefined
  isLoading: boolean
  href: string
  description: string
  colorClass: string
}) {
  if (isLoading) {
    return <SkeletonServiceCard />
  }

  const getStatusDisplay = () => {
    if (!health) return { status: 'error' as const, text: 'Error' }

    switch (health.status) {
      case 'healthy':
        return { status: 'success' as const, text: 'Connected' }
      case 'setup_required':
        return { status: 'warning' as const, text: 'Setup Required' }
      case 'disabled':
        return { status: 'neutral' as const, text: 'Disabled' }
      default:
        return { status: 'error' as const, text: 'Offline' }
    }
  }

  const statusDisplay = getStatusDisplay()

  return (
    <Link to={href}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">{name}</CardTitle>
          <Icon className={`h-4 w-4 ${colorClass}`} />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <StatusIndicator status={statusDisplay.status} />
            <span className="font-semibold">{statusDisplay.text}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        </CardContent>
      </Card>
    </Link>
  )
}

export function Dashboard() {
  // Gateway status
  const { data: gatewayStatus, isLoading: gatewayLoading } = useQuery<GatewayStatus>({
    queryKey: ['gateway-status'],
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/status')
      if (!res.ok) throw new Error('Failed to fetch gateway status')
      return res.json()
    },
    refetchInterval: 10000,
  })

  // Airflow health
  const { data: airflowHealth, isLoading: airflowLoading } = useQuery<ServiceHealth>({
    queryKey: ['airflow-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/airflow/health')
      if (!res.ok) return { status: 'unhealthy', error: 'Failed to connect' }
      return res.json()
    },
    refetchInterval: 30000,
  })

  // Langflow health
  const { data: langflowHealth, isLoading: langflowLoading } = useQuery<ServiceHealth>({
    queryKey: ['langflow-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/langflow/health')
      if (!res.ok) return { status: 'unhealthy', error: 'Failed to connect' }
      return res.json()
    },
    refetchInterval: 30000,
  })

  // n8n health
  const { data: n8nHealth, isLoading: n8nLoading } = useQuery<ServiceHealth>({
    queryKey: ['n8n-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/n8n/health')
      if (!res.ok) return { status: 'unhealthy', error: 'Failed to connect' }
      return res.json()
    },
    refetchInterval: 30000,
  })

  // Langfuse/Observability health
  const { data: langfuseHealth, isLoading: langfuseLoading } = useQuery<ServiceHealth>({
    queryKey: ['observability-health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/observability/health')
      if (!res.ok) return { status: 'unhealthy', error: 'Failed to connect' }
      return res.json()
    },
    refetchInterval: 30000,
  })

  const gatewayHealth: ServiceHealth = gatewayStatus
    ? { status: gatewayStatus.health.status as 'healthy' | 'unhealthy' }
    : { status: 'unhealthy' }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
      </div>

      {/* Service Health Overview */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Service Health</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <ServiceStatusCard
            name="API Gateway"
            icon={Network}
            health={gatewayHealth}
            isLoading={gatewayLoading}
            href="/gateway"
            description="KrakenD"
            colorClass="text-blue-500"
          />
          <ServiceStatusCard
            name="Workflows"
            icon={Workflow}
            health={airflowHealth}
            isLoading={airflowLoading}
            href="/workflows"
            description="Apache Airflow"
            colorClass="text-green-500"
          />
          <ServiceStatusCard
            name="AI Flows"
            icon={Brain}
            health={langflowHealth}
            isLoading={langflowLoading}
            href="/ai"
            description="Langflow"
            colorClass="text-purple-500"
          />
          <ServiceStatusCard
            name="Automation"
            icon={Zap}
            health={n8nHealth}
            isLoading={n8nLoading}
            href="/automation"
            description="n8n"
            colorClass="text-orange-500"
          />
          <ServiceStatusCard
            name="Observability"
            icon={Activity}
            health={langfuseHealth}
            isLoading={langfuseLoading}
            href="/observability"
            description="Langfuse"
            colorClass="text-cyan-500"
          />
        </div>
      </div>

      {/* Gateway Stats */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Gateway Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Gateway Status</CardTitle>
              <Network className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {gatewayLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-24" />
                  <Skeleton className="h-3 w-40" />
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <StatusIndicator
                      status={gatewayStatus?.health.status || 'unhealthy'}
                    />
                    <span className="text-2xl font-bold capitalize">
                      {gatewayStatus?.health.status || 'Unknown'}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Mode: {gatewayStatus?.health.mode || 'unknown'} |
                    Pods: {gatewayStatus?.health.running_pods || 0}/{gatewayStatus?.health.pod_count || 0}
                  </p>
                </>
              )}
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
      </div>

      {/* System Monitoring */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">System Monitoring</h2>
          <Link
            to="/monitoring"
            className="text-sm text-primary hover:underline flex items-center gap-1"
          >
            <BarChart3 className="h-4 w-4" />
            View Dashboards
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link to="/monitoring/system-overview">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">System Overview</CardTitle>
                <BarChart3 className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  All services health at a glance
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link to="/monitoring/containers">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Containers</CardTitle>
                <Server className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Docker container metrics
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link to="/monitoring/postgresql">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">PostgreSQL</CardTitle>
                <Database className="h-4 w-4 text-purple-500" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Database performance
                </p>
              </CardContent>
            </Card>
          </Link>
          <Link to="/monitoring/redis">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Redis</CardTitle>
                <HardDrive className="h-4 w-4 text-orange-500" />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Cache performance
                </p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link to="/gateway/resources">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardContent className="flex items-center gap-4 p-6">
                <div className="p-3 rounded-lg bg-blue-100 dark:bg-blue-900/20">
                  <Network className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h3 className="font-semibold">Discover Resources</h3>
                  <p className="text-sm text-muted-foreground">
                    Find and expose new APIs
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link to="/gateway/config">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardContent className="flex items-center gap-4 p-6">
                <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/20">
                  <Settings className="h-6 w-6 text-slate-600 dark:text-slate-400" />
                </div>
                <div>
                  <h3 className="font-semibold">View Config</h3>
                  <p className="text-sm text-muted-foreground">
                    See current KrakenD config
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link to="/workflows/dags">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardContent className="flex items-center gap-4 p-6">
                <div className="p-3 rounded-lg bg-green-100 dark:bg-green-900/20">
                  <Workflow className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <h3 className="font-semibold">Manage DAGs</h3>
                  <p className="text-sm text-muted-foreground">
                    View and trigger workflows
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link to="/ai/flows">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardContent className="flex items-center gap-4 p-6">
                <div className="p-3 rounded-lg bg-purple-100 dark:bg-purple-900/20">
                  <Brain className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold">AI Flows</h3>
                  <p className="text-sm text-muted-foreground">
                    Run Langflow pipelines
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>
    </div>
  )
}

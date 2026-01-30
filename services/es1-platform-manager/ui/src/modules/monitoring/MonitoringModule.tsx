import { useState } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Container,
  Server,
  Database,
  HardDrive,
  Network,
  ExternalLink,
  RefreshCw,
} from 'lucide-react'
import { cn } from '@/shared/utils/cn'
import { Button } from '@/design-system/components/Button'
import { serviceUrl } from '@/config'

const dashboards = [
  {
    id: 'system-overview',
    uid: 'es1-system-overview',
    name: 'System Overview',
    icon: LayoutDashboard,
    description: 'All services health status at a glance',
  },
  {
    id: 'containers',
    uid: 'es1-docker-containers',
    name: 'Containers',
    icon: Container,
    description: 'Docker container metrics via cAdvisor',
  },
  {
    id: 'node',
    uid: 'es1-node-resources',
    name: 'Host Resources',
    icon: Server,
    description: 'Host CPU, memory, disk, and network',
  },
  {
    id: 'postgresql',
    uid: 'es1-postgresql',
    name: 'PostgreSQL',
    icon: Database,
    description: 'Database connections, queries, cache',
  },
  {
    id: 'redis',
    uid: 'es1-redis',
    name: 'Redis',
    icon: HardDrive,
    description: 'Cache memory, commands, hit ratio',
  },
  {
    id: 'krakend',
    uid: 'es1-krakend',
    name: 'API Gateway',
    icon: Network,
    description: 'KrakenD request rate, latency, errors',
  },
]

export function MonitoringModule() {
  const grafanaUrl = serviceUrl('grafana')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Monitoring</h1>
          <p className="text-muted-foreground">
            System metrics and performance dashboards
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => window.open(grafanaUrl, '_blank')}
        >
          <ExternalLink className="h-4 w-4 mr-2" />
          Open Grafana
        </Button>
      </div>

      {/* Dashboard Navigation */}
      <div className="flex gap-2 flex-wrap">
        {dashboards.map((dashboard) => (
          <NavLink
            key={dashboard.id}
            to={`/monitoring/${dashboard.id}`}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm border transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-card hover:bg-accent border-border'
              )
            }
          >
            <dashboard.icon className="h-4 w-4" />
            {dashboard.name}
          </NavLink>
        ))}
      </div>

      {/* Dashboard Content */}
      <Routes>
        <Route index element={<DashboardSelector />} />
        {dashboards.map((dashboard) => (
          <Route
            key={dashboard.id}
            path={dashboard.id}
            element={<GrafanaDashboard dashboard={dashboard} />}
          />
        ))}
      </Routes>
    </div>
  )
}

function DashboardSelector() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {dashboards.map((dashboard) => (
        <NavLink
          key={dashboard.id}
          to={`/monitoring/${dashboard.id}`}
          className="p-6 rounded-lg border bg-card hover:bg-accent transition-colors group"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-md bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
              <dashboard.icon className="h-5 w-5" />
            </div>
            <h3 className="font-semibold">{dashboard.name}</h3>
          </div>
          <p className="text-sm text-muted-foreground">{dashboard.description}</p>
        </NavLink>
      ))}
    </div>
  )
}

interface GrafanaDashboardProps {
  dashboard: (typeof dashboards)[0]
}

function GrafanaDashboard({ dashboard }: GrafanaDashboardProps) {
  const [refreshKey, setRefreshKey] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const grafanaUrl = serviceUrl('grafana')
  const prometheusUrl = serviceUrl('prometheus')

  // Build the Grafana embed URL
  // Using solo mode (kiosk=1) for clean embedding
  const embedUrl = `${grafanaUrl}/d/${dashboard.uid}?orgId=1&refresh=30s&kiosk=1&theme=dark`

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <dashboard.icon className="h-5 w-5 text-primary" />
          <div>
            <h2 className="text-lg font-semibold">{dashboard.name}</h2>
            <p className="text-sm text-muted-foreground">{dashboard.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setIsLoading(true)
              setRefreshKey((k) => k + 1)
            }}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open(`${grafanaUrl}/d/${dashboard.uid}`, '_blank')}
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Full Screen
          </Button>
        </div>
      </div>

      {/* Embedded Grafana Dashboard */}
      <div className="relative rounded-lg border bg-card overflow-hidden" style={{ height: 'calc(100vh - 320px)', minHeight: '500px' }}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-card z-10">
            <div className="flex flex-col items-center gap-2">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">Loading dashboard...</span>
            </div>
          </div>
        )}
        <iframe
          key={refreshKey}
          src={embedUrl}
          className="w-full h-full border-0"
          title={dashboard.name}
          onLoad={() => setIsLoading(false)}
        />
      </div>

      {/* Quick Links */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <a
          href={`${grafanaUrl}/d/${dashboard.uid}`}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-foreground flex items-center gap-1"
        >
          <ExternalLink className="h-3 w-3" />
          Edit in Grafana
        </a>
        <a
          href={prometheusUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-foreground flex items-center gap-1"
        >
          <ExternalLink className="h-3 w-3" />
          Prometheus
        </a>
      </div>
    </div>
  )
}

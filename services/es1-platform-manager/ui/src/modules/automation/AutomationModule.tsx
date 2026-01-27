import { Routes, Route, NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle, XCircle, AlertTriangle, ExternalLink } from 'lucide-react'
import { N8NWorkflowsView } from './views/N8NWorkflowsView'
import { N8NExecutionsView } from './views/N8NExecutionsView'
import { N8NCredentialsView } from './views/N8NCredentialsView'

interface N8NHealth {
  status: string  // healthy, unhealthy, disabled, setup_required
  message: string | null
  error: string | null
  setup_url: string | null
}

async function fetchN8NHealth(): Promise<N8NHealth> {
  const res = await fetch('/api/v1/n8n/health')
  if (!res.ok) throw new Error('Failed to check n8n health')
  return res.json()
}

function HealthIndicator() {
  const { data, isLoading } = useQuery({
    queryKey: ['n8n-health'],
    queryFn: fetchN8NHealth,
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1.5 text-muted-foreground text-sm">
        <span className="w-2 h-2 rounded-full bg-muted-foreground animate-pulse" />
        Checking...
      </span>
    )
  }

  if (!data || data.status === 'unhealthy') {
    return (
      <span className="inline-flex items-center gap-1.5 text-destructive text-sm">
        <XCircle className="w-4 h-4" />
        n8n Offline
      </span>
    )
  }

  if (data.status === 'disabled') {
    return (
      <span className="inline-flex items-center gap-1.5 text-amber-600 text-sm">
        <AlertTriangle className="w-4 h-4" />
        n8n Disabled
      </span>
    )
  }

  if (data.status === 'setup_required') {
    return (
      <span className="inline-flex items-center gap-1.5 text-amber-600 text-sm">
        <AlertTriangle className="w-4 h-4" />
        Setup Required
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1.5 text-green-600 text-sm">
      <CheckCircle className="w-4 h-4" />
      n8n Connected
    </span>
  )
}

export function AutomationModule() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Automation</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Workflow automation powered by n8n
          </p>
        </div>
        <div className="flex items-center gap-4">
          <HealthIndicator />
          <a
            href="http://localhost:5678"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <ExternalLink className="w-4 h-4" />
            Open n8n
          </a>
        </div>
      </div>

      <nav className="flex space-x-4 border-b border-border">
        <NavLink
          to="/automation"
          end
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Workflows
        </NavLink>
        <NavLink
          to="/automation/executions"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Executions
        </NavLink>
        <NavLink
          to="/automation/credentials"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Credentials
        </NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<N8NWorkflowsView />} />
        <Route path="/executions" element={<N8NExecutionsView />} />
        <Route path="/credentials" element={<N8NCredentialsView />} />
      </Routes>
    </div>
  )
}

import { Routes, Route, NavLink } from 'react-router-dom'
import { ExternalLink, KeyRound } from 'lucide-react'
import { TracesView } from './TracesView'
import { SessionsView } from './SessionsView'
import { MetricsView } from './MetricsView'
import { Button } from '@/design-system/components/Button'
import { config, serviceUrl, isFeatureEnabled } from '@/config'

export function ObservabilityModule() {
  const openLangfuse = () => {
    window.open(serviceUrl('langfuse'), '_blank')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Observability</h1>
        {isFeatureEnabled('enableLangfuse') && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <KeyRound className="h-3 w-3" />
              <code className="bg-muted px-1 rounded">{config().credentials.langfuse.email}</code>
              <span>/</span>
              <code className="bg-muted px-1 rounded">{config().credentials.langfuse.password}</code>
            </div>
            <Button variant="outline" size="sm" onClick={openLangfuse}>
              <ExternalLink className="h-4 w-4 mr-2" />
              Open Langfuse
            </Button>
          </div>
        )}
      </div>

      <nav className="flex space-x-4 border-b border-border">
        <NavLink
          to="/observability"
          end
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Traces
        </NavLink>
        <NavLink
          to="/observability/sessions"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Sessions
        </NavLink>
        <NavLink
          to="/observability/metrics"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Metrics
        </NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<TracesView />} />
        <Route path="/sessions" element={<SessionsView />} />
        <Route path="/metrics" element={<MetricsView />} />
      </Routes>
    </div>
  )
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Button, Badge, StatusIndicator } from '../../design-system/components'
import { useTheme } from '../../shared/contexts/ThemeContext'
import { useToast } from '../../shared/contexts/ToastContext'

interface SystemStatus {
  name: string
  version: string
  runtime_mode: string
  scheduler: {
    running: boolean
    discovery_enabled: boolean
    interval_seconds: number
    last_discovery: Record<string, string | null>
  }
  integrations: {
    airflow: boolean
    langflow: boolean
    langfuse: boolean
    n8n: boolean
  }
}

interface ConfigResponse {
  runtime_mode: string
  api_prefix: string
  discovery: {
    enabled: boolean
    interval_seconds: number
  }
  krakend: {
    url: string
    config_path: string
  }
  airflow: {
    enabled: boolean
    url: string
  }
  langflow: {
    enabled: boolean
    url: string
  }
  langfuse: {
    enabled: boolean
    url: string
  }
  n8n: {
    enabled: boolean
    url: string
  }
}

async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch('/api/v1/system/status')
  if (!res.ok) throw new Error('Failed to fetch system status')
  return res.json()
}

async function fetchConfig(): Promise<ConfigResponse> {
  const res = await fetch('/api/v1/system/config')
  if (!res.ok) throw new Error('Failed to fetch config')
  return res.json()
}

async function runDiscovery(): Promise<{ results: any; message: string }> {
  const res = await fetch('/api/v1/system/discovery/run', {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to run discovery')
  return res.json()
}

export function SettingsModule() {
  const { theme, setTheme } = useTheme()
  const { addToast } = useToast()
  const queryClient = useQueryClient()

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['system', 'status'],
    queryFn: fetchSystemStatus,
    refetchInterval: 10000,
  })

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['system', 'config'],
    queryFn: fetchConfig,
  })

  const discoveryMutation = useMutation({
    mutationFn: runDiscovery,
    onSuccess: (result) => {
      addToast({ type: 'success', message: result.message })
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Settings</h1>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Theme Settings */}
        <Card className="p-6">
          <h2 className="text-lg font-medium mb-4">Appearance</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground block mb-2">
                Theme
              </label>
              <div className="flex gap-2">
                {(['light', 'dark', 'system'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTheme(t)}
                    className={`px-4 py-2 rounded-md border transition-colors capitalize ${
                      theme === t
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* System Status */}
        <Card className="p-6">
          <h2 className="text-lg font-medium mb-4">System Status</h2>
          {statusLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : status ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Version</span>
                <Badge variant="secondary">{status.version}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Runtime Mode</span>
                <Badge variant="outline">{status.runtime_mode}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Scheduler</span>
                <StatusIndicator status={status.scheduler.running ? 'success' : 'neutral'} />
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">Failed to load status</p>
          )}
        </Card>

        {/* Integrations */}
        <Card className="p-6">
          <h2 className="text-lg font-medium mb-4">Integrations</h2>
          {statusLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : status ? (
            <div className="space-y-3">
              {Object.entries(status.integrations).map(([name, enabled]) => (
                <div key={name} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{name}</span>
                  <StatusIndicator status={enabled ? 'success' : 'neutral'} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">Failed to load integrations</p>
          )}
        </Card>

        {/* Discovery */}
        <Card className="p-6">
          <h2 className="text-lg font-medium mb-4">Resource Discovery</h2>
          <div className="space-y-4">
            {status && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Interval</span>
                  <span className="text-sm">
                    {status.scheduler.interval_seconds}s
                  </span>
                </div>
                <div className="space-y-2">
                  <span className="text-sm text-muted-foreground block">Last Discovery</span>
                  {Object.entries(status.scheduler.last_discovery).map(([service, time]) => (
                    <div key={service} className="flex items-center justify-between text-sm">
                      <span className="capitalize">{service}</span>
                      <span className="text-muted-foreground">
                        {time ? new Date(time).toLocaleString() : 'Never'}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
            <Button
              onClick={() => discoveryMutation.mutate()}
              disabled={discoveryMutation.isPending}
              className="w-full"
            >
              {discoveryMutation.isPending ? 'Running...' : 'Run Discovery Now'}
            </Button>
          </div>
        </Card>
      </div>

      {/* Configuration Details */}
      <Card className="p-6">
        <h2 className="text-lg font-medium mb-4">Configuration</h2>
        {configLoading ? (
          <p className="text-muted-foreground">Loading...</p>
        ) : config ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div>
              <h3 className="text-sm font-medium mb-2">KrakenD</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>URL: {config.krakend.url}</p>
                <p>Config: {config.krakend.config_path}</p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-2">Airflow</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Enabled: {config.airflow.enabled ? 'Yes' : 'No'}</p>
                <p>URL: {config.airflow.url}</p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-2">Langflow</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Enabled: {config.langflow.enabled ? 'Yes' : 'No'}</p>
                <p>URL: {config.langflow.url}</p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-2">Langfuse</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Enabled: {config.langfuse.enabled ? 'Yes' : 'No'}</p>
                <p>URL: {config.langfuse.url}</p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-2">n8n</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Enabled: {config.n8n.enabled ? 'Yes' : 'No'}</p>
                <p>URL: {config.n8n.url}</p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground">Failed to load configuration</p>
        )}
      </Card>
    </div>
  )
}

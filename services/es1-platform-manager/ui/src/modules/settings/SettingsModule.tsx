import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Palette, Plug, Settings2, RefreshCw, Save, ToggleLeft, ToggleRight } from 'lucide-react'
import { Card, Button, Badge } from '@/design-system/components'
import { StatusIndicator } from '@/design-system/components/StatusIndicator'
import { useTheme } from '@/shared/contexts/ThemeContext'
import { useToast } from '@/shared/contexts/ToastContext'
import { useBranding, BrandingConfig } from '@/shared/contexts/BrandingContext'

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

interface FeatureFlags {
  gateway_enabled: boolean
  workflows_enabled: boolean
  ai_flows_enabled: boolean
  observability_enabled: boolean
  automation_enabled: boolean
  dark_mode_enabled: boolean
  api_docs_enabled: boolean
}

const tabs = [
  { id: 'branding', label: 'Branding', icon: Palette },
  { id: 'integrations', label: 'Integrations', icon: Plug },
  { id: 'system', label: 'System', icon: Settings2 },
]

export function SettingsModule() {
  const [activeTab, setActiveTab] = useState('branding')
  const { theme, setTheme } = useTheme()
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  const { branding, updateBranding, isUpdating } = useBranding()

  // Local state for branding form
  const [brandingForm, setBrandingForm] = useState<Partial<BrandingConfig>>({})

  const { data: status, isLoading: statusLoading } = useQuery<SystemStatus>({
    queryKey: ['system', 'status'],
    queryFn: async () => {
      const res = await fetch('/api/v1/system/status')
      if (!res.ok) throw new Error('Failed to fetch status')
      return res.json()
    },
    refetchInterval: 10000,
  })

  const { data: featureFlags } = useQuery<FeatureFlags>({
    queryKey: ['feature-flags'],
    queryFn: async () => {
      const res = await fetch('/api/v1/settings/features/flags')
      if (!res.ok) throw new Error('Failed to fetch feature flags')
      return res.json()
    },
  })

  const featureFlagsMutation = useMutation({
    mutationFn: async (updates: Partial<FeatureFlags>) => {
      const res = await fetch('/api/v1/settings/features/flags', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (!res.ok) throw new Error('Failed to update')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feature-flags'] })
      addToast({ type: 'success', title: 'Feature flags updated' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Update failed', description: err.message })
    },
  })

  const discoveryMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/system/discovery/run', { method: 'POST' })
      if (!res.ok) throw new Error('Failed to run discovery')
      return res.json()
    },
    onSuccess: (result: { message: string }) => {
      addToast({ type: 'success', title: result.message })
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Discovery failed', description: err.message })
    },
  })

  const handleBrandingSave = async () => {
    if (Object.keys(brandingForm).length === 0) return
    try {
      await updateBranding(brandingForm)
      setBrandingForm({})
      addToast({ type: 'success', title: 'Branding updated' })
    } catch (err) {
      addToast({ type: 'error', title: 'Failed to update branding', description: String(err) })
    }
  }

  const handleBrandingChange = (field: keyof BrandingConfig, value: string) => {
    setBrandingForm((prev) => ({ ...prev, [field]: value }))
  }

  const toggleFeature = (flag: keyof FeatureFlags) => {
    if (!featureFlags) return
    featureFlagsMutation.mutate({ [flag]: !featureFlags[flag] })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Settings</h1>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-1 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Branding Tab */}
      {activeTab === 'branding' && (
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-medium">Brand Identity</h2>
                <p className="text-sm text-muted-foreground">
                  Customize the look and feel of your platform
                </p>
              </div>
              <Button
                onClick={handleBrandingSave}
                disabled={isUpdating || Object.keys(brandingForm).length === 0}
              >
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium block mb-2">Platform Name</label>
                <input
                  type="text"
                  value={brandingForm.name ?? branding.name}
                  onChange={(e) => handleBrandingChange('name', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="My Platform"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Tagline</label>
                <input
                  type="text"
                  value={brandingForm.tagline ?? branding.tagline ?? ''}
                  onChange={(e) => handleBrandingChange('tagline', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="Your platform tagline"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Logo URL (Light Mode)</label>
                <input
                  type="text"
                  value={brandingForm.logo_url ?? branding.logo_url ?? ''}
                  onChange={(e) => handleBrandingChange('logo_url', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="https://example.com/logo.png"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Logo URL (Dark Mode)</label>
                <input
                  type="text"
                  value={brandingForm.logo_dark_url ?? branding.logo_dark_url ?? ''}
                  onChange={(e) => handleBrandingChange('logo_dark_url', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="https://example.com/logo-dark.png"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Favicon URL</label>
                <input
                  type="text"
                  value={brandingForm.favicon_url ?? branding.favicon_url ?? ''}
                  onChange={(e) => handleBrandingChange('favicon_url', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="https://example.com/favicon.ico"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Footer Text</label>
                <input
                  type="text"
                  value={brandingForm.footer_text ?? branding.footer_text ?? ''}
                  onChange={(e) => handleBrandingChange('footer_text', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="© 2024 Your Company"
                />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-medium mb-4">Colors</h2>
            <div className="grid gap-6 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium block mb-2">Primary Color</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={brandingForm.primary_color ?? branding.primary_color}
                    onChange={(e) => handleBrandingChange('primary_color', e.target.value)}
                    className="w-12 h-10 border rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={brandingForm.primary_color ?? branding.primary_color}
                    onChange={(e) => handleBrandingChange('primary_color', e.target.value)}
                    className="flex-1 px-3 py-2 border rounded bg-background font-mono text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Secondary Color</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={brandingForm.secondary_color ?? branding.secondary_color}
                    onChange={(e) => handleBrandingChange('secondary_color', e.target.value)}
                    className="w-12 h-10 border rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={brandingForm.secondary_color ?? branding.secondary_color}
                    onChange={(e) => handleBrandingChange('secondary_color', e.target.value)}
                    className="flex-1 px-3 py-2 border rounded bg-background font-mono text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Accent Color</label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={brandingForm.accent_color ?? branding.accent_color}
                    onChange={(e) => handleBrandingChange('accent_color', e.target.value)}
                    className="w-12 h-10 border rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={brandingForm.accent_color ?? branding.accent_color}
                    onChange={(e) => handleBrandingChange('accent_color', e.target.value)}
                    className="flex-1 px-3 py-2 border rounded bg-background font-mono text-sm"
                  />
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-medium mb-4">Support & Documentation</h2>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium block mb-2">Support Email</label>
                <input
                  type="email"
                  value={brandingForm.support_email ?? branding.support_email ?? ''}
                  onChange={(e) => handleBrandingChange('support_email', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="support@example.com"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Support URL</label>
                <input
                  type="url"
                  value={brandingForm.support_url ?? branding.support_url ?? ''}
                  onChange={(e) => handleBrandingChange('support_url', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="https://support.example.com"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Documentation URL</label>
                <input
                  type="url"
                  value={brandingForm.docs_url ?? branding.docs_url ?? ''}
                  onChange={(e) => handleBrandingChange('docs_url', e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                  placeholder="https://docs.example.com"
                />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-medium mb-4">Appearance</h2>
            <div>
              <label className="text-sm font-medium block mb-2">Theme</label>
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
          </Card>
        </div>
      )}

      {/* Integrations Tab */}
      {activeTab === 'integrations' && (
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-lg font-medium mb-6">Feature Modules</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Enable or disable platform modules. Disabled modules will be hidden from the UI.
            </p>
            <div className="space-y-4">
              {featureFlags && (
                <>
                  <FeatureToggle
                    label="Gateway"
                    description="API Gateway management and endpoint exposure"
                    enabled={featureFlags.gateway_enabled}
                    onToggle={() => toggleFeature('gateway_enabled')}
                    disabled={featureFlagsMutation.isPending}
                  />
                  <FeatureToggle
                    label="Workflows (Airflow)"
                    description="Manage and trigger Apache Airflow DAGs"
                    enabled={featureFlags.workflows_enabled}
                    onToggle={() => toggleFeature('workflows_enabled')}
                    disabled={featureFlagsMutation.isPending}
                  />
                  <FeatureToggle
                    label="AI Flows (Langflow)"
                    description="Manage Langflow LLM pipelines"
                    enabled={featureFlags.ai_flows_enabled}
                    onToggle={() => toggleFeature('ai_flows_enabled')}
                    disabled={featureFlagsMutation.isPending}
                  />
                  <FeatureToggle
                    label="Observability (Langfuse)"
                    description="LLM observability and tracing"
                    enabled={featureFlags.observability_enabled}
                    onToggle={() => toggleFeature('observability_enabled')}
                    disabled={featureFlagsMutation.isPending}
                  />
                  <FeatureToggle
                    label="Automation (n8n)"
                    description="Workflow automation with n8n"
                    enabled={featureFlags.automation_enabled}
                    onToggle={() => toggleFeature('automation_enabled')}
                    disabled={featureFlagsMutation.isPending}
                  />
                </>
              )}
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-medium mb-6">Integration Status</h2>
            {statusLoading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : status ? (
              <div className="space-y-4">
                {Object.entries(status.integrations).map(([name, connected]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between p-3 bg-muted/30 rounded"
                  >
                    <div className="flex items-center gap-3">
                      <StatusIndicator status={connected ? 'healthy' : 'unhealthy'} />
                      <span className="font-medium capitalize">{name}</span>
                    </div>
                    <Badge variant={connected ? 'success' : 'secondary'}>
                      {connected ? 'Connected' : 'Disconnected'}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">Failed to load</p>
            )}
          </Card>
        </div>
      )}

      {/* System Tab */}
      {activeTab === 'system' && (
        <div className="grid gap-6 md:grid-cols-2">
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
                  <StatusIndicator status={status.scheduler.running ? 'healthy' : 'inactive'} />
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">Failed to load</p>
            )}
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-medium mb-4">Resource Discovery</h2>
            <div className="space-y-4">
              {status && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Interval</span>
                    <span className="text-sm">{status.scheduler.interval_seconds}s</span>
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
                <RefreshCw className={`h-4 w-4 mr-2 ${discoveryMutation.isPending ? 'animate-spin' : ''}`} />
                {discoveryMutation.isPending ? 'Running...' : 'Run Discovery Now'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

function FeatureToggle({
  label,
  description,
  enabled,
  onToggle,
  disabled,
}: {
  label: string
  description: string
  enabled: boolean
  onToggle: () => void
  disabled?: boolean
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-muted/30 rounded">
      <div>
        <p className="font-medium">{label}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <button
        onClick={onToggle}
        disabled={disabled}
        className={`p-1 rounded transition-colors ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-accent'}`}
      >
        {enabled ? (
          <ToggleRight className="h-8 w-8 text-green-500" />
        ) : (
          <ToggleLeft className="h-8 w-8 text-muted-foreground" />
        )}
      </button>
    </div>
  )
}

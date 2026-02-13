import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, FileJson, Copy, Check, ChevronDown, ChevronRight, GitCompare } from 'lucide-react'
import { gatewayKeys } from '../queryKeys'
import { Button, Card, Badge } from '@/design-system/components'
import { useToast } from '@/shared/contexts/ToastContext'

interface CurrentConfig {
  config: Record<string, unknown> | null
  config_path: string | null
  mode: string
  has_config: boolean
  endpoint_count: number
}

interface ConfigVersion {
  id: string
  version: number
  config_snapshot: Record<string, unknown>
  created_by: string
  created_at: string
  commit_message: string | null
  is_active: boolean
  deployed_to_gateway_at: string | null
}

interface ConfigVersionListResponse {
  items: ConfigVersion[]
  total: number
  page: number
  page_size: number
}

interface ConfigDiff {
  version_a: number
  version_b: number
  diff: Array<{
    type: 'added' | 'removed' | 'modified'
    endpoint: string
    config?: Record<string, unknown>
    before?: Record<string, unknown>
    after?: Record<string, unknown>
  }>
  added_endpoints: string[]
  removed_endpoints: string[]
  modified_endpoints: string[]
}

export function ConfigView() {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['endpoints']))
  const [copied, setCopied] = useState(false)
  const [compareVersionA, setCompareVersionA] = useState<number | null>(null)
  const [compareVersionB, setCompareVersionB] = useState<number | null>(null)
  const { addToast } = useToast()

  const { data: currentConfig, isLoading, refetch } = useQuery<CurrentConfig>({
    queryKey: gatewayKeys.config.current,
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/config/current')
      if (!res.ok) throw new Error('Failed to fetch current config')
      return res.json()
    },
  })

  const { data: versions } = useQuery<ConfigVersionListResponse>({
    queryKey: gatewayKeys.versions.list,
    queryFn: async () => {
      const res = await fetch('/api/v1/config-versions?page_size=50')
      if (!res.ok) throw new Error('Failed to fetch config versions')
      return res.json()
    },
  })

  const { data: diffResult, isLoading: diffLoading } = useQuery<ConfigDiff>({
    queryKey: gatewayKeys.config.diff(compareVersionA, compareVersionB),
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/config/diff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version_a: compareVersionA, version_b: compareVersionB }),
      })
      if (!res.ok) throw new Error('Failed to compare configs')
      return res.json()
    },
    enabled: compareVersionA !== null && compareVersionB !== null,
  })

  const copyConfig = async () => {
    if (currentConfig?.config) {
      await navigator.clipboard.writeText(JSON.stringify(currentConfig.config, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      addToast({ type: 'success', title: 'Configuration copied to clipboard' })
    }
  }

  const toggleSection = (section: string) => {
    const newSections = new Set(expandedSections)
    if (newSections.has(section)) {
      newSections.delete(section)
    } else {
      newSections.add(section)
    }
    setExpandedSections(newSections)
  }

  const renderValue = (value: unknown, depth = 0): JSX.Element => {
    if (value === null) return <span className="text-gray-500">null</span>
    if (typeof value === 'boolean') return <span className="text-purple-600 dark:text-purple-400">{String(value)}</span>
    if (typeof value === 'number') return <span className="text-blue-600 dark:text-blue-400">{value}</span>
    if (typeof value === 'string') return <span className="text-green-600 dark:text-green-400">"{value}"</span>
    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-gray-500">[]</span>
      return (
        <div className="ml-4">
          {value.map((item, i) => (
            <div key={i} className="flex">
              <span className="text-gray-400 mr-2">{i}:</span>
              {renderValue(item, depth + 1)}
            </div>
          ))}
        </div>
      )
    }
    if (typeof value === 'object') {
      const entries = Object.entries(value as Record<string, unknown>)
      if (entries.length === 0) return <span className="text-gray-500">{'{}'}</span>
      return (
        <div className="ml-4">
          {entries.map(([key, val]) => (
            <div key={key} className="flex flex-wrap">
              <span className="text-yellow-600 dark:text-yellow-400 mr-1">"{key}":</span>
              {renderValue(val, depth + 1)}
            </div>
          ))}
        </div>
      )
    }
    return <span>{String(value)}</span>
  }

  const renderConfigSection = (key: string, value: unknown) => {
    const isExpanded = expandedSections.has(key)
    const isArray = Array.isArray(value)
    const isObject = typeof value === 'object' && value !== null && !isArray
    const canExpand = isArray || isObject

    return (
      <div key={key} className="border-b border-border last:border-b-0">
        <button
          className="w-full flex items-center gap-2 py-2 px-3 hover:bg-accent/50 transition-colors text-left"
          onClick={() => canExpand && toggleSection(key)}
        >
          {canExpand ? (
            isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )
          ) : (
            <span className="w-4" />
          )}
          <span className="font-medium text-yellow-600 dark:text-yellow-400">"{key}"</span>
          {!canExpand && (
            <span className="ml-2">{renderValue(value)}</span>
          )}
          {isArray && (
            <Badge variant="secondary" className="ml-2">
              {(value as unknown[]).length} items
            </Badge>
          )}
        </button>
        {canExpand && isExpanded && (
          <div className="pb-3 px-3 bg-muted/30">
            <pre className="text-sm font-mono overflow-x-auto p-2">
              {renderValue(value)}
            </pre>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Current Config Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Current Configuration</h2>
          {currentConfig && (
            <Badge variant={currentConfig.has_config ? 'success' : 'warning'}>
              {currentConfig.has_config ? 'Active' : 'No Config'}
            </Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={copyConfig} disabled={!currentConfig?.config}>
            {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Config Info */}
      {isLoading ? (
        <Card className="p-8 text-center text-muted-foreground">Loading configuration...</Card>
      ) : !currentConfig?.config ? (
        <Card className="p-8 text-center">
          <FileJson className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No configuration deployed to gateway yet.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Create and approve exposures, then deploy to generate a configuration.
          </p>
        </Card>
      ) : (
        <>
          {/* Config Stats */}
          <div className="grid grid-cols-3 gap-4">
            <Card className="p-4">
              <p className="text-sm text-muted-foreground">Mode</p>
              <p className="text-xl font-semibold capitalize">{currentConfig.mode}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-muted-foreground">Endpoints</p>
              <p className="text-xl font-semibold">{currentConfig.endpoint_count}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-muted-foreground">Config Path</p>
              <p className="text-sm font-mono truncate" title={currentConfig.config_path || ''}>
                {currentConfig.config_path || 'N/A'}
              </p>
            </Card>
          </div>

          {/* Config Content */}
          <Card>
            <div className="p-3 border-b bg-muted/50">
              <h3 className="font-medium flex items-center gap-2">
                <FileJson className="h-4 w-4" />
                krakend.json
              </h3>
            </div>
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {Object.entries(currentConfig.config).map(([key, value]) =>
                renderConfigSection(key, value)
              )}
            </div>
          </Card>
        </>
      )}

      {/* Version Comparison */}
      {versions && versions.items.length > 1 && (
        <Card className="p-4">
          <h3 className="font-medium mb-4 flex items-center gap-2">
            <GitCompare className="h-4 w-4" />
            Compare Versions
          </h3>
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="text-sm text-muted-foreground block mb-1">Version A</label>
              <select
                className="w-full border rounded px-3 py-2 bg-background"
                value={compareVersionA ?? ''}
                onChange={(e) => setCompareVersionA(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Select version...</option>
                {versions.items.map((v) => (
                  <option key={v.version} value={v.version}>
                    v{v.version} {v.is_active ? '(active)' : ''}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-sm text-muted-foreground block mb-1">Version B</label>
              <select
                className="w-full border rounded px-3 py-2 bg-background"
                value={compareVersionB ?? ''}
                onChange={(e) => setCompareVersionB(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Select version...</option>
                {versions.items.map((v) => (
                  <option key={v.version} value={v.version}>
                    v{v.version} {v.is_active ? '(active)' : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Diff Results */}
          {diffLoading && (
            <div className="mt-4 text-center text-muted-foreground">Comparing...</div>
          )}
          {diffResult && (
            <div className="mt-4 space-y-3">
              <div className="flex gap-4 text-sm">
                <span className="text-green-600">+{diffResult.added_endpoints.length} added</span>
                <span className="text-red-600">-{diffResult.removed_endpoints.length} removed</span>
                <span className="text-yellow-600">~{diffResult.modified_endpoints.length} modified</span>
              </div>
              {diffResult.diff.length > 0 ? (
                <div className="border rounded divide-y max-h-80 overflow-y-auto">
                  {diffResult.diff.map((d, i) => (
                    <div key={i} className="p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge
                          variant={
                            d.type === 'added' ? 'success' : d.type === 'removed' ? 'warning' : 'info'
                          }
                        >
                          {d.type}
                        </Badge>
                        <span className="font-mono text-sm">{d.endpoint}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No differences found.</p>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

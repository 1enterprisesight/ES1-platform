import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Plus, Minus, Eye, GitCompare, Send, ArrowLeft } from 'lucide-react'
import { Button, Card, CardHeader, CardTitle, CardContent, Badge } from '@/design-system/components'
import { useToast } from '@/shared/contexts/ToastContext'

interface Resource {
  id: string
  type: string
  source: string
  source_id: string
  metadata: Record<string, unknown>
  status: string
}

interface ResourceListResponse {
  items: Resource[]
  total: number
  page: number
  page_size: number
}

interface DynamicRoute {
  endpoint: string
  method: string
  resource_type?: string
  resource_source?: string
  resource_id?: string
  resource_name?: string
  exposure_id?: string
  managed_by: string
  backend_host?: string
}

interface ConfigState {
  active_version: number | null
  dynamic_routes: DynamicRoute[]
  base_routes: unknown[]
  total_endpoints: number
  base_endpoint_count: number
  dynamic_endpoint_count: number
}

interface ChangeSet {
  id: string
  base_version_id: string | null
  status: string
  created_by: string
  created_at: string
  description: string | null
  changes: ExposureChange[]
}

interface ExposureChange {
  id: string
  exposure_id: string | null
  resource_id: string
  change_type: string
  settings_before: Record<string, unknown> | null
  settings_after: Record<string, unknown> | null
  status: string
}

interface DiffResponse {
  change_set_id: string
  added: Array<Record<string, unknown>>
  removed: Array<Record<string, unknown>>
  modified: Array<Record<string, unknown>>
  total_changes: number
}

export function EditConfigView() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const baseVersion = searchParams.get('base') || 'current'
  const [changeSetId, setChangeSetId] = useState<string | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [diffOpen, setDiffOpen] = useState(false)
  const [previewData, setPreviewData] = useState<Record<string, unknown> | null>(null)
  const [diffData, setDiffData] = useState<DiffResponse | null>(null)

  // Fetch current config state (source of truth for what's deployed)
  const { data: configState } = useQuery<ConfigState>({
    queryKey: ['gateway-config-state'],
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/config/state')
      if (!res.ok) throw new Error('Failed to fetch config state')
      return res.json()
    },
  })

  // Fetch available resources (not yet exposed)
  const { data: resources } = useQuery<ResourceListResponse>({
    queryKey: ['resources-available'],
    queryFn: async () => {
      const res = await fetch('/api/v1/resources?page_size=100')
      if (!res.ok) throw new Error('Failed to fetch resources')
      return res.json()
    },
  })

  // Fetch change set details if we have one
  const { data: changeSet, refetch: refetchChangeSet } = useQuery<ChangeSet>({
    queryKey: ['change-set', changeSetId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/gateway/change-sets/${changeSetId}`)
      if (!res.ok) throw new Error('Failed to fetch change set')
      return res.json()
    },
    enabled: !!changeSetId,
  })

  // Create change set on mount
  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/gateway/change-sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base: baseVersion,
          created_by: 'admin',
          description: `Configuration changes from ${baseVersion === 'current' ? 'current config' : `version ${baseVersion}`}`,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to create change set')
      }
      return res.json()
    },
    onSuccess: (data: ChangeSet) => {
      setChangeSetId(data.id)
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Error', description: err.message })
    },
  })

  // Auto-create change set on mount
  useEffect(() => {
    if (!changeSetId && !createMutation.isPending) {
      createMutation.mutate()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Add resource mutation
  const addMutation = useMutation({
    mutationFn: async (resourceId: string) => {
      const res = await fetch(`/api/v1/gateway/change-sets/${changeSetId}/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resource_id: resourceId,
          settings: {},
          user: 'admin',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to add resource')
      }
      return res.json()
    },
    onSuccess: () => {
      refetchChangeSet()
      addToast({ type: 'success', title: 'Resource added to change set' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Error', description: err.message })
    },
  })

  // Remove dynamic route mutation (by resource_id)
  const removeMutation = useMutation({
    mutationFn: async (resourceId: string) => {
      const res = await fetch(`/api/v1/gateway/change-sets/${changeSetId}/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resource_id: resourceId,
          user: 'admin',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to remove route')
      }
      return res.json()
    },
    onSuccess: () => {
      refetchChangeSet()
      addToast({ type: 'success', title: 'Route marked for removal' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Error', description: err.message })
    },
  })

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/v1/gateway/change-sets/${changeSetId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: 'admin' }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to submit')
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config-versions'] })
      addToast({ type: 'success', title: 'Change set submitted for approval' })
      navigate('/gateway/review')
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Error', description: err.message })
    },
  })

  // Preview handler
  const handlePreview = async () => {
    try {
      const res = await fetch(`/api/v1/gateway/change-sets/${changeSetId}/preview`)
      if (!res.ok) throw new Error('Failed to preview')
      const data = await res.json()
      setPreviewData(data.config)
      setPreviewOpen(true)
    } catch (err) {
      addToast({ type: 'error', title: 'Preview failed', description: String(err) })
    }
  }

  // Diff handler
  const handleDiff = async () => {
    try {
      const res = await fetch(`/api/v1/gateway/change-sets/${changeSetId}/diff`)
      if (!res.ok) throw new Error('Failed to get diff')
      const data = await res.json()
      setDiffData(data)
      setDiffOpen(true)
    } catch (err) {
      addToast({ type: 'error', title: 'Diff failed', description: String(err) })
    }
  }

  // Get IDs of resources already added in this change set
  const addedResourceIds = new Set(
    changeSet?.changes
      .filter((c) => c.change_type === 'add')
      .map((c) => c.resource_id) || []
  )

  // Get resource_ids marked for removal in this change set
  const removedResourceIds = new Set(
    changeSet?.changes
      .filter((c) => c.change_type === 'remove')
      .map((c) => c.resource_id)
      .filter(Boolean) || []
  )

  // Currently deployed dynamic routes (from config state)
  const deployedRoutes = configState?.dynamic_routes || []

  // Set of resource_ids that are already in the deployed config
  const deployedResourceIds = new Set(
    deployedRoutes
      .map((dr) => dr.resource_id)
      .filter(Boolean)
  )

  // Resources available to add: active, not already in config, not already added in this change set
  const availableResources = (resources?.items || []).filter(
    (r) => {
      if (r.status !== 'active') return false
      // Already added in this change set
      if (addedResourceIds.has(r.id)) return false
      // Already deployed in the config (unless marked for removal in this change set)
      if (deployedResourceIds.has(r.id) && !removedResourceIds.has(r.id)) return false
      return true
    }
  )

  const changeCount = changeSet?.changes.length || 0

  const typeColors: Record<string, 'warning' | 'info' | 'success' | 'secondary'> = {
    workflow: 'warning',
    flow: 'info',
    connection: 'success',
    service: 'secondary',
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/gateway')}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <h2 className="text-lg font-semibold">Edit Configuration</h2>
            <p className="text-sm text-muted-foreground">
              Starting from: {baseVersion === 'current' ? 'Current running config' : `Version ${baseVersion}`}
              {changeSet && (
                <> &middot; Change set: <span className="font-mono text-xs">{changeSet.id.slice(0, 8)}</span></>
              )}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handlePreview} disabled={!changeSetId}>
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>
          <Button variant="outline" size="sm" onClick={handleDiff} disabled={!changeSetId}>
            <GitCompare className="h-4 w-4 mr-2" />
            View Diff
          </Button>
          <Button
            size="sm"
            onClick={() => submitMutation.mutate()}
            disabled={!changeSetId || changeCount === 0 || submitMutation.isPending}
          >
            <Send className="h-4 w-4 mr-2" />
            Submit for Approval ({changeCount})
          </Button>
        </div>
      </div>

      {/* Change Summary */}
      {changeCount > 0 && (
        <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
          <CardContent className="py-3">
            <div className="flex items-center gap-4 text-sm">
              <span className="font-medium">Changes:</span>
              {changeSet?.changes.filter((c) => c.change_type === 'add').length ? (
                <Badge variant="success">
                  +{changeSet.changes.filter((c) => c.change_type === 'add').length} added
                </Badge>
              ) : null}
              {changeSet?.changes.filter((c) => c.change_type === 'remove').length ? (
                <Badge variant="destructive">
                  -{changeSet.changes.filter((c) => c.change_type === 'remove').length} removed
                </Badge>
              ) : null}
              {changeSet?.changes.filter((c) => c.change_type === 'modify').length ? (
                <Badge variant="warning">
                  ~{changeSet.changes.filter((c) => c.change_type === 'modify').length} modified
                </Badge>
              ) : null}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Currently Exposed (from active config version snapshot, minus removals, plus additions) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Currently Exposed ({deployedRoutes.filter((r) => !r.resource_id || !removedResourceIds.has(r.resource_id)).length + addedResourceIds.size})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {deployedRoutes.length === 0 && addedResourceIds.size === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No resources are currently exposed through the gateway.
            </p>
          ) : (
            <div className="space-y-2">
              {deployedRoutes
                .filter((route) => !route.resource_id || !removedResourceIds.has(route.resource_id))
                .map((route) => (
                <div
                  key={route.endpoint}
                  className="flex items-center justify-between p-3 border rounded"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={typeColors[route.resource_type || ''] || 'secondary'}>
                      {route.resource_type || 'unknown'}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium">
                        {route.resource_name || 'Unknown'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {route.resource_source} &middot;{' '}
                        <span className="font-mono">{route.method} {route.endpoint}</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {route.resource_id ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => removeMutation.mutate(route.resource_id!)}
                        disabled={removeMutation.isPending}
                      >
                        <Minus className="h-4 w-4 mr-1" />
                        Remove
                      </Button>
                    ) : (
                      <Badge variant="secondary">Legacy route</Badge>
                    )}
                  </div>
                </div>
              ))}
              {/* Show resources added in this change set */}
              {(resources?.items || [])
                .filter((r) => addedResourceIds.has(r.id))
                .map((resource) => (
                  <div
                    key={resource.id}
                    className="flex items-center justify-between p-3 border rounded bg-green-50 dark:bg-green-950/20 border-green-200"
                  >
                    <div className="flex items-center gap-3">
                      <Badge variant={typeColors[resource.type] || 'secondary'}>
                        {resource.type}
                      </Badge>
                      <div>
                        <p className="text-sm font-medium">
                          {(resource.metadata as Record<string, string>)?.name || resource.source_id}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {resource.source} &middot; {resource.source_id}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="success">Added</Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => removeMutation.mutate(resource.id)}
                        disabled={removeMutation.isPending}
                      >
                        <Minus className="h-4 w-4 mr-1" />
                        Undo
                      </Button>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available Resources */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Available Resources ({availableResources.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {availableResources.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              All discovered resources are already exposed or no resources have been discovered yet.
            </p>
          ) : (
            <div className="space-y-2">
              {availableResources.map((resource) => (
                <div
                  key={resource.id}
                  className={`flex items-center justify-between p-3 border rounded ${
                    addedResourceIds.has(resource.id) ? 'bg-green-50 dark:bg-green-950/20 border-green-200' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={typeColors[resource.type] || 'secondary'}>
                      {resource.type}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium">
                        {(resource.metadata as Record<string, string>)?.name || resource.source_id}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {resource.source} &middot; {resource.source_id}
                      </p>
                    </div>
                  </div>
                  {addedResourceIds.has(resource.id) ? (
                    <Badge variant="success">Added</Badge>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => addMutation.mutate(resource.id)}
                      disabled={addMutation.isPending || !changeSetId}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add to Gateway
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Preview Modal */}
      {previewOpen && previewData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-[800px] max-h-[80vh] flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Full Config Preview</CardTitle>
              <Button variant="outline" size="sm" onClick={() => setPreviewOpen(false)}>
                Close
              </Button>
            </CardHeader>
            <CardContent className="overflow-auto flex-1">
              <pre className="bg-muted p-4 rounded-md text-xs overflow-auto">
                {JSON.stringify(previewData, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Diff Modal */}
      {diffOpen && diffData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-[800px] max-h-[80vh] flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Changes vs Baseline</CardTitle>
              <Button variant="outline" size="sm" onClick={() => setDiffOpen(false)}>
                Close
              </Button>
            </CardHeader>
            <CardContent className="overflow-auto flex-1 space-y-4">
              <p className="text-sm text-muted-foreground">
                {diffData.total_changes} total changes
              </p>

              {diffData.added.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-green-600 mb-2">
                    Added ({diffData.added.length})
                  </h3>
                  {diffData.added.map((item, i) => (
                    <div key={i} className="bg-green-50 dark:bg-green-950/20 border border-green-200 rounded p-3 mb-2 text-sm">
                      <p className="font-medium">{String(item.resource_name)}</p>
                      <p className="text-xs text-muted-foreground">
                        {String(item.resource_type)} from {String(item.resource_source)}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {diffData.removed.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-red-600 mb-2">
                    Removed ({diffData.removed.length})
                  </h3>
                  {diffData.removed.map((item, i) => (
                    <div key={i} className="bg-red-50 dark:bg-red-950/20 border border-red-200 rounded p-3 mb-2 text-sm">
                      <p className="font-medium">{String(item.resource_name)}</p>
                      <p className="text-xs text-muted-foreground">
                        {String(item.resource_type)} from {String(item.resource_source)}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {diffData.modified.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-yellow-600 mb-2">
                    Modified ({diffData.modified.length})
                  </h3>
                  {diffData.modified.map((item, i) => (
                    <div key={i} className="bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 rounded p-3 mb-2 text-sm">
                      <p className="font-medium">{String(item.resource_name)}</p>
                      <div className="grid grid-cols-2 gap-2 mt-2">
                        <div>
                          <p className="text-xs font-medium text-muted-foreground">Before:</p>
                          <pre className="text-xs bg-muted rounded p-1 mt-1">
                            {JSON.stringify(item.settings_before, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-muted-foreground">After:</p>
                          <pre className="text-xs bg-muted rounded p-1 mt-1">
                            {JSON.stringify(item.settings_after, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {diffData.total_changes === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  No changes from baseline.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, CheckCircle, XCircle, Clock, RotateCcw, Rocket, History, AlertTriangle } from 'lucide-react'
import { gatewayKeys } from '../queryKeys'
import { Button, Card, Badge } from '@/design-system/components'
import { useToast } from '@/shared/contexts/ToastContext'

interface Deployment {
  id: string
  version_id: string
  status: string
  deployed_by: string
  deployed_at: string
  completed_at?: string
  health_check_passed?: boolean
  error_message?: string
}

interface DeploymentListResponse {
  items: Deployment[]
  total: number
  page: number
  page_size: number
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

export function DeploymentsView() {
  const [page, setPage] = useState(1)
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<ConfigVersion | null>(null)
  const [rollbackReason, setRollbackReason] = useState('')
  const [viewMode, setViewMode] = useState<'deployments' | 'versions'>('deployments')
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const { data, isLoading, refetch } = useQuery<DeploymentListResponse>({
    queryKey: gatewayKeys.deployments.list(page),
    queryFn: async () => {
      const res = await fetch(`/api/v1/deployments?page=${page}&page_size=20`)
      if (!res.ok) throw new Error('Failed to fetch deployments')
      return res.json()
    },
  })

  const { data: versions, isLoading: versionsLoading } = useQuery<ConfigVersionListResponse>({
    queryKey: gatewayKeys.versions.list,
    queryFn: async () => {
      const res = await fetch('/api/v1/config-versions?page_size=50')
      if (!res.ok) throw new Error('Failed to fetch config versions')
      return res.json()
    },
  })

  const rollbackMutation = useMutation({
    mutationFn: async () => {
      if (!selectedVersion) throw new Error('No version selected')
      const res = await fetch('/api/v1/deployments/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          version: selectedVersion.version,
          deployed_by: 'admin',
          reason: rollbackReason || 'Manual rollback',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Rollback failed')
      }
      return res.json()
    },
    onSuccess: () => {
      setRollbackDialogOpen(false)
      setSelectedVersion(null)
      setRollbackReason('')
      queryClient.invalidateQueries({ queryKey: gatewayKeys.deployments.all })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.versions.all })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.config.state })
      addToast({ type: 'success', title: 'Rollback successful', description: `Rolled back to v${selectedVersion?.version}` })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Rollback failed', description: err.message })
    },
  })

  const deployMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/deployments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deployed_by: 'admin',
          commit_message: 'Manual deployment from UI',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Deployment failed')
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gatewayKeys.deployments.all })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.versions.all })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.config.state })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.exposures.all })
      addToast({ type: 'success', title: 'Deployment started' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Deployment failed', description: err.message })
    },
  })

  const statusIcons: Record<string, React.ReactNode> = {
    succeeded: <CheckCircle className="h-4 w-4 text-green-500" />,
    failed: <XCircle className="h-4 w-4 text-red-500" />,
    in_progress: <Clock className="h-4 w-4 text-blue-500 animate-spin" />,
    pending: <Clock className="h-4 w-4 text-yellow-500" />,
    rolled_back: <RotateCcw className="h-4 w-4 text-orange-500" />,
  }

  const statusColors: Record<string, 'success' | 'destructive' | 'warning' | 'info' | 'secondary'> = {
    succeeded: 'success',
    failed: 'destructive',
    in_progress: 'info',
    pending: 'warning',
    rolled_back: 'secondary',
  }

  const formatDuration = (start: string, end?: string) => {
    if (!end) return 'In progress...'
    const startTime = new Date(start).getTime()
    const endTime = new Date(end).getTime()
    const duration = (endTime - startTime) / 1000
    if (duration < 60) return `${duration.toFixed(1)}s`
    return `${Math.floor(duration / 60)}m ${Math.floor(duration % 60)}s`
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold">Deployments</h2>
          <div className="flex border rounded overflow-hidden">
            <button
              className={`px-3 py-1 text-sm ${viewMode === 'deployments' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}
              onClick={() => setViewMode('deployments')}
            >
              History
            </button>
            <button
              className={`px-3 py-1 text-sm ${viewMode === 'versions' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}
              onClick={() => setViewMode('versions')}
            >
              Versions
            </button>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => deployMutation.mutate()}
            disabled={deployMutation.isPending}
          >
            <Rocket className="h-4 w-4 mr-2" />
            Deploy Approved
          </Button>
        </div>
      </div>

      {viewMode === 'deployments' ? (
        <>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : data?.items.length === 0 ? (
            <Card className="p-8 text-center">
              <p className="text-muted-foreground">No deployments yet.</p>
              <p className="text-sm text-muted-foreground mt-2">
                Deploy approved exposures to create a deployment.
              </p>
            </Card>
          ) : (
            <div className="space-y-2">
              {data?.items.map((deployment) => (
                <Card key={deployment.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {statusIcons[deployment.status]}
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">
                            Deployment #{deployment.id.slice(0, 8)}
                          </p>
                          <Badge variant={statusColors[deployment.status] || 'secondary'}>
                            {deployment.status.replace('_', ' ')}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          By {deployment.deployed_by} on{' '}
                          {new Date(deployment.deployed_at).toLocaleString()}
                        </p>
                        {deployment.error_message && (
                          <p className="text-sm text-red-500 mt-1">
                            Error: {deployment.error_message}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">
                        Duration: {formatDuration(deployment.deployed_at, deployment.completed_at)}
                      </p>
                      {deployment.health_check_passed !== null && (
                        <p className="text-xs text-muted-foreground">
                          Health check: {deployment.health_check_passed ? 'Passed' : 'Failed'}
                        </p>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Pagination */}
          {data && data.total > data.page_size && (
            <div className="flex justify-center gap-2 mt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span className="px-4 py-2 text-sm">
                Page {page} of {Math.ceil(data.total / data.page_size)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= Math.ceil(data.total / data.page_size)}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      ) : (
        <>
          {versionsLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : versions?.items.length === 0 ? (
            <Card className="p-8 text-center">
              <p className="text-muted-foreground">No configuration versions yet.</p>
              <p className="text-sm text-muted-foreground mt-2">
                Versions are created when you deploy approved exposures.
              </p>
            </Card>
          ) : (
            <div className="space-y-2">
              {versions?.items.map((version) => (
                <Card key={version.id} className={`p-4 ${version.is_active ? 'border-green-500 border-2' : ''}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <History className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">Version {version.version}</p>
                          {version.is_active && (
                            <Badge variant="success">Active</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {version.commit_message || 'No commit message'}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          By {version.created_by} on {new Date(version.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {(version.config_snapshot as { endpoints?: unknown[] })?.endpoints?.length || 0} endpoints
                      </span>
                      {!version.is_active && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setSelectedVersion(version)
                            setRollbackDialogOpen(true)
                          }}
                        >
                          <RotateCcw className="h-4 w-4 mr-1" />
                          Rollback
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* Rollback Dialog */}
      {rollbackDialogOpen && selectedVersion && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-[480px] p-6">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="h-6 w-6 text-yellow-500" />
              <h2 className="text-lg font-semibold">Rollback Configuration</h2>
            </div>
            <p className="text-muted-foreground mb-4">
              Are you sure you want to rollback to <strong>Version {selectedVersion.version}</strong>?
              This will replace the current gateway configuration.
            </p>
            <div className="bg-muted/50 rounded p-3 mb-4 text-sm">
              <p><strong>Created:</strong> {new Date(selectedVersion.created_at).toLocaleString()}</p>
              <p><strong>By:</strong> {selectedVersion.created_by}</p>
              <p><strong>Message:</strong> {selectedVersion.commit_message || 'No message'}</p>
              <p><strong>Endpoints:</strong> {(selectedVersion.config_snapshot as { endpoints?: unknown[] })?.endpoints?.length || 0}</p>
            </div>
            <div className="mb-4">
              <label className="text-sm font-medium block mb-1">Rollback Reason (optional)</label>
              <input
                type="text"
                value={rollbackReason}
                onChange={(e) => setRollbackReason(e.target.value)}
                placeholder="Why are you rolling back?"
                className="w-full px-3 py-2 border rounded bg-background"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setRollbackDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={rollbackMutation.isPending}
                onClick={() => rollbackMutation.mutate()}
              >
                {rollbackMutation.isPending ? 'Rolling back...' : 'Confirm Rollback'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

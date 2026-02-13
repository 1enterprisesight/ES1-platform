import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, History, RotateCcw, Play, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react'
import { gatewayKeys } from '../queryKeys'
import { Button, Card, Badge } from '@/design-system/components'
import { useToast } from '@/shared/contexts/ToastContext'

interface ConfigVersion {
  id: string
  version: number
  config_snapshot: Record<string, unknown>
  created_by: string
  created_at: string
  commit_message: string | null
  is_active: boolean
  deployed_to_gateway_at: string | null
  status: string | null
}

interface ConfigVersionListResponse {
  items: ConfigVersion[]
  total: number
  page: number
  page_size: number
}

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

export function HistoryView() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { addToast } = useToast()
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null)
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<ConfigVersion | null>(null)
  const [rollbackReason, setRollbackReason] = useState('')

  const { data: versions, isLoading, refetch } = useQuery<ConfigVersionListResponse>({
    queryKey: gatewayKeys.versions.list,
    queryFn: async () => {
      const res = await fetch('/api/v1/config-versions?page_size=50')
      if (!res.ok) throw new Error('Failed to fetch config versions')
      return res.json()
    },
  })

  const { data: deployments } = useQuery<DeploymentListResponse>({
    queryKey: gatewayKeys.deployments.recent,
    queryFn: async () => {
      const res = await fetch('/api/v1/deployments?page_size=50')
      if (!res.ok) throw new Error('Failed to fetch deployments')
      return res.json()
    },
  })

  // Filter to deployed/active versions
  const deployedVersions = (versions?.items || []).filter(
    (v) => v.deployed_to_gateway_at || v.is_active || v.status === 'deployed'
  )

  // Get deployment info for a version
  const getDeploymentForVersion = (versionId: string) => {
    return deployments?.items.find((d) => d.version_id === versionId)
  }

  const rollbackMutation = useMutation({
    mutationFn: async () => {
      if (!selectedVersion) throw new Error('No version selected')
      const res = await fetch('/api/v1/deployments/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          version: selectedVersion.version,
          deployed_by: 'admin',
          reason: rollbackReason || 'Manual rollback from history',
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
      queryClient.invalidateQueries({ queryKey: gatewayKeys.versions.all })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.deployments.all })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.config.state })
      addToast({ type: 'success', title: 'Rollback successful' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Rollback failed', description: err.message })
    },
  })

  const statusBadge = (version: ConfigVersion) => {
    if (version.is_active) return <Badge variant="success">Active</Badge>
    if (version.status === 'deployed') return <Badge variant="secondary">Previously Deployed</Badge>
    if (version.status === 'approved') return <Badge variant="info">Approved</Badge>
    if (version.status === 'rejected') return <Badge variant="destructive">Rejected</Badge>
    if (version.status === 'pending_approval') return <Badge variant="warning">Pending</Badge>
    return null
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold">Deployment History</h2>
          <p className="text-sm text-muted-foreground">
            All deployed config versions &middot; pick any as a starting point for new changes
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : deployedVersions.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">No deployment history yet.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Deploy a configuration to start building history.
          </p>
        </Card>
      ) : (
        <div className="space-y-2">
          {deployedVersions.map((version) => {
            const deployment = getDeploymentForVersion(version.id)
            const isExpanded = expandedVersionId === version.id
            const endpoints = (version.config_snapshot as { endpoints?: unknown[] })?.endpoints || []

            return (
              <Card
                key={version.id}
                className={`overflow-hidden ${version.is_active ? 'border-green-500 border-2' : ''}`}
              >
                <div className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <History className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">Version {version.version}</p>
                          {statusBadge(version)}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {version.commit_message || 'No description'}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          By {version.created_by} on{' '}
                          {new Date(version.deployed_to_gateway_at || version.created_at).toLocaleString()}
                          {' '}&middot;{' '}{endpoints.length} endpoints
                          {deployment && (
                            <>
                              {' '}&middot;{' '}
                              {deployment.health_check_passed ? 'Health: Passed' : deployment.status === 'failed' ? 'Health: Failed' : ''}
                            </>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpandedVersionId(isExpanded ? null : version.id)}
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/gateway/edit?base=${version.version}`)}
                      >
                        <Play className="h-4 w-4 mr-1" />
                        Use as Starting Point
                      </Button>
                      {!version.is_active && (
                        <Button
                          variant="outline"
                          size="sm"
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
                </div>

                {/* Expandable config view */}
                {isExpanded && (
                  <div className="border-t bg-muted/50 p-4">
                    <h4 className="text-sm font-medium mb-2">Endpoints ({endpoints.length})</h4>
                    <div className="space-y-1 mb-4">
                      {endpoints.map((ep, i) => {
                        const endpoint = ep as Record<string, unknown>
                        return (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <Badge variant="secondary" className="text-xs min-w-[50px] text-center">
                              {String(endpoint.method || 'GET')}
                            </Badge>
                            <span className="font-mono">{String(endpoint.endpoint || '')}</span>
                            {endpoint['@managed_by'] === 'platform-manager' && (
                              <Badge variant="info" className="text-xs">dynamic</Badge>
                            )}
                          </div>
                        )
                      })}
                    </div>
                    <details>
                      <summary className="text-xs text-muted-foreground cursor-pointer">
                        Full JSON config
                      </summary>
                      <pre className="text-xs overflow-auto max-h-64 mt-2 bg-background p-2 rounded">
                        {JSON.stringify(version.config_snapshot, null, 2)}
                      </pre>
                    </details>
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}

      {/* Rollback Dialog */}
      {rollbackDialogOpen && selectedVersion && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-[480px] p-6">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="h-6 w-6 text-yellow-500" />
              <h2 className="text-lg font-semibold">Rollback to Version {selectedVersion.version}</h2>
            </div>
            <p className="text-muted-foreground mb-4">
              This will replace the current gateway configuration with Version {selectedVersion.version}.
            </p>
            <div className="bg-muted/50 rounded p-3 mb-4 text-sm">
              <p><strong>Created:</strong> {new Date(selectedVersion.created_at).toLocaleString()}</p>
              <p><strong>By:</strong> {selectedVersion.created_by}</p>
              <p><strong>Message:</strong> {selectedVersion.commit_message || 'None'}</p>
              <p><strong>Endpoints:</strong> {((selectedVersion.config_snapshot as { endpoints?: unknown[] })?.endpoints || []).length}</p>
            </div>
            <div className="mb-4">
              <label className="text-sm font-medium block mb-1">Reason (optional)</label>
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

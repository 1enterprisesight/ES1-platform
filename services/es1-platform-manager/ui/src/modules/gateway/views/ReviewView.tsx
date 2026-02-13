import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, CheckCircle, XCircle, Rocket, Clock, ChevronDown, ChevronUp } from 'lucide-react'
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

interface ChangeSet {
  id: string
  base_version_id: string | null
  status: string
  created_by: string
  created_at: string
  description: string | null
  config_version_id: string | null
  changes: ExposureChange[]
}

interface ExposureChange {
  id: string
  change_type: string
  resource_id: string
  settings_before: Record<string, unknown> | null
  settings_after: Record<string, unknown> | null
  status: string
}

interface ChangeSetListResponse {
  items: ChangeSet[]
  total: number
  page: number
  page_size: number
}

export function ReviewView() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { addToast } = useToast()
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null)
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false)
  const [rejectVersionId, setRejectVersionId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  // Fetch pending config versions
  const { data: versions, isLoading, refetch } = useQuery<ConfigVersionListResponse>({
    queryKey: ['config-versions-pending'],
    queryFn: async () => {
      const res = await fetch('/api/v1/config-versions?page_size=50')
      if (!res.ok) throw new Error('Failed to fetch config versions')
      return res.json()
    },
  })

  // Fetch change sets to get extra context
  const { data: changeSets } = useQuery<ChangeSetListResponse>({
    queryKey: ['change-sets-submitted'],
    queryFn: async () => {
      const res = await fetch('/api/v1/gateway/change-sets?status=submitted&page_size=50')
      if (!res.ok) throw new Error('Failed to fetch change sets')
      return res.json()
    },
  })

  // Filter to only pending_approval versions
  const pendingVersions = (versions?.items || []).filter(
    (v) => v.status === 'pending_approval'
  )

  // Also show recently approved (ready to deploy)
  const approvedVersions = (versions?.items || []).filter(
    (v) => v.status === 'approved'
  )

  // Find the change set for a config version
  const getChangeSetForVersion = (versionId: string) => {
    return changeSets?.items.find((cs) => cs.config_version_id === versionId)
  }

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: async (versionId: string) => {
      const res = await fetch(`/api/v1/gateway/config-versions/${versionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: 'admin' }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to approve')
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config-versions-pending'] })
      queryClient.invalidateQueries({ queryKey: ['change-sets-submitted'] })
      addToast({ type: 'success', title: 'Config version approved' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Approval failed', description: err.message })
    },
  })

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: async () => {
      if (!rejectVersionId) throw new Error('No version selected')
      const res = await fetch(`/api/v1/gateway/config-versions/${rejectVersionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rejected_by: 'admin',
          reason: rejectReason || 'Rejected',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to reject')
      }
      return res.json()
    },
    onSuccess: () => {
      setRejectDialogOpen(false)
      setRejectVersionId(null)
      setRejectReason('')
      queryClient.invalidateQueries({ queryKey: ['config-versions-pending'] })
      queryClient.invalidateQueries({ queryKey: ['change-sets-submitted'] })
      addToast({ type: 'success', title: 'Config version rejected' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Rejection failed', description: err.message })
    },
  })

  // Deploy mutation
  const deployMutation = useMutation({
    mutationFn: async (versionId: string) => {
      const res = await fetch(`/api/v1/gateway/config-versions/${versionId}/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deployed_by: 'admin' }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Deployment failed')
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config-versions-pending'] })
      queryClient.invalidateQueries({ queryKey: ['config-versions'] })
      queryClient.invalidateQueries({ queryKey: ['deployments'] })
      queryClient.invalidateQueries({ queryKey: ['gateway-config-state'] })
      addToast({ type: 'success', title: 'Deployment started' })
      navigate('/gateway/history')
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Deployment failed', description: err.message })
    },
  })

  const renderVersionCard = (version: ConfigVersion, type: 'pending' | 'approved') => {
    const changeSet = getChangeSetForVersion(version.id)
    const isExpanded = expandedVersionId === version.id
    const endpoints = (version.config_snapshot as { endpoints?: unknown[] })?.endpoints || []

    return (
      <Card key={version.id} className="overflow-hidden">
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Clock className="h-5 w-5 text-muted-foreground" />
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium">Version {version.version}</p>
                  <Badge variant={type === 'pending' ? 'warning' : 'success'}>
                    {type === 'pending' ? 'Pending Approval' : 'Approved'}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Submitted by {version.created_by} on{' '}
                  {new Date(version.created_at).toLocaleString()}
                </p>
                {version.commit_message && (
                  <p className="text-sm mt-1">{version.commit_message}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                {endpoints.length} endpoints
              </span>
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
              {type === 'pending' && (
                <>
                  <Button
                    size="sm"
                    onClick={() => approveMutation.mutate(version.id)}
                    disabled={approveMutation.isPending}
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setRejectVersionId(version.id)
                      setRejectDialogOpen(true)
                    }}
                  >
                    <XCircle className="h-4 w-4 mr-1" />
                    Reject
                  </Button>
                </>
              )}
              {type === 'approved' && (
                <Button
                  size="sm"
                  onClick={() => deployMutation.mutate(version.id)}
                  disabled={deployMutation.isPending}
                >
                  <Rocket className="h-4 w-4 mr-1" />
                  Deploy Now
                </Button>
              )}
            </div>
          </div>

          {/* Change set details */}
          {changeSet && (
            <div className="mt-3 flex gap-2 text-xs">
              {changeSet.changes.filter((c) => c.change_type === 'add').length > 0 && (
                <Badge variant="success">
                  +{changeSet.changes.filter((c) => c.change_type === 'add').length} added
                </Badge>
              )}
              {changeSet.changes.filter((c) => c.change_type === 'remove').length > 0 && (
                <Badge variant="destructive">
                  -{changeSet.changes.filter((c) => c.change_type === 'remove').length} removed
                </Badge>
              )}
              {changeSet.changes.filter((c) => c.change_type === 'modify').length > 0 && (
                <Badge variant="warning">
                  ~{changeSet.changes.filter((c) => c.change_type === 'modify').length} modified
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* Expandable config view */}
        {isExpanded && (
          <div className="border-t bg-muted/50 p-4">
            <pre className="text-xs overflow-auto max-h-96">
              {JSON.stringify(version.config_snapshot, null, 2)}
            </pre>
          </div>
        )}
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold">Review &amp; Approve</h2>
          <p className="text-sm text-muted-foreground">
            Config versions awaiting approval or ready to deploy
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : (
        <>
          {/* Pending Approval */}
          <div>
            <h3 className="text-sm font-medium text-muted-foreground mb-3">
              Pending Approval ({pendingVersions.length})
            </h3>
            {pendingVersions.length === 0 ? (
              <Card className="p-8 text-center">
                <p className="text-muted-foreground">No config versions pending approval.</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Submit a change set from the Edit tab to create one.
                </p>
              </Card>
            ) : (
              <div className="space-y-2">
                {pendingVersions.map((v) => renderVersionCard(v, 'pending'))}
              </div>
            )}
          </div>

          {/* Approved (Ready to Deploy) */}
          {approvedVersions.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Approved - Ready to Deploy ({approvedVersions.length})
              </h3>
              <div className="space-y-2">
                {approvedVersions.map((v) => renderVersionCard(v, 'approved'))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Reject Dialog */}
      {rejectDialogOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-[480px] p-6">
            <div className="flex items-center gap-3 mb-4">
              <XCircle className="h-6 w-6 text-red-500" />
              <h2 className="text-lg font-semibold">Reject Config Version</h2>
            </div>
            <div className="mb-4">
              <label className="text-sm font-medium block mb-1">Rejection Reason</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Why is this being rejected?"
                className="w-full px-3 py-2 border rounded bg-background resize-none h-24"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={rejectMutation.isPending || !rejectReason.trim()}
                onClick={() => rejectMutation.mutate()}
              >
                {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

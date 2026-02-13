import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, X, Rocket, RefreshCw } from 'lucide-react'
import { gatewayKeys } from '../queryKeys'
import { Button, Card, Badge } from '@/design-system/components'
import { useToast } from '@/shared/contexts/ToastContext'

interface Exposure {
  id: string
  resource_id: string
  settings: Record<string, unknown>
  generated_config: Record<string, unknown>
  status: string
  created_by: string
  created_at: string
  approved_by?: string
  approved_at?: string
  resource?: {
    id: string
    type: string
    source: string
    source_id: string
    metadata: Record<string, unknown>
  }
}

interface ExposureListResponse {
  items: Exposure[]
  total: number
  page: number
  page_size: number
}

export function ExposuresView() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const { data, isLoading, refetch } = useQuery<ExposureListResponse>({
    queryKey: gatewayKeys.exposures.list(page, statusFilter),
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: '20' })
      if (statusFilter) params.set('status', statusFilter)
      const res = await fetch(`/api/v1/exposures?${params}`)
      if (!res.ok) throw new Error('Failed to fetch exposures')
      return res.json()
    },
  })

  const approveMutation = useMutation({
    mutationFn: async (exposureId: string) => {
      const res = await fetch(`/api/v1/exposures/${exposureId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: 'admin' }),
      })
      if (!res.ok) throw new Error('Failed to approve exposure')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gatewayKeys.exposures.all })
      addToast({ type: 'success', title: 'Exposure approved' })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: async (exposureId: string) => {
      const res = await fetch(`/api/v1/exposures/${exposureId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected_by: 'admin', reason: 'Rejected by admin' }),
      })
      if (!res.ok) throw new Error('Failed to reject exposure')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gatewayKeys.exposures.all })
      addToast({ type: 'info', title: 'Exposure rejected' })
    },
  })

  const deployMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/deployments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deployed_by: 'admin' }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to deploy')
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: gatewayKeys.exposures.all })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.deployments.all })
      queryClient.invalidateQueries({ queryKey: gatewayKeys.config.state })
      addToast({ type: 'success', title: 'Deployment successful' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Deployment failed', description: err.message })
    },
  })

  const statusColors: Record<string, 'default' | 'secondary' | 'success' | 'warning' | 'destructive'> = {
    pending: 'warning',
    approved: 'info' as 'default',
    rejected: 'destructive',
    deployed: 'success',
  }

  const approvedCount = data?.items.filter(e => e.status === 'approved').length || 0

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold">Exposures</h2>
          <div className="flex gap-1">
            {['all', 'pending', 'approved', 'deployed'].map((status) => (
              <Button
                key={status}
                variant={statusFilter === (status === 'all' ? null : status) ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter(status === 'all' ? null : status)}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {approvedCount > 0 && (
            <Button
              size="sm"
              onClick={() => deployMutation.mutate()}
              disabled={deployMutation.isPending}
            >
              <Rocket className="h-4 w-4 mr-2" />
              Deploy ({approvedCount})
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : data?.items.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">No exposures found.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Create exposures from the Resources tab.
          </p>
        </Card>
      ) : (
        <div className="space-y-2">
          {data?.items.map((exposure) => (
            <Card key={exposure.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Badge variant={statusColors[exposure.status] || 'default'}>
                    {exposure.status}
                  </Badge>
                  <div>
                    <p className="font-medium">
                      {exposure.resource?.metadata
                        ? String(exposure.resource.metadata.name || exposure.resource.metadata.dag_id || exposure.resource.source_id)
                        : 'Unknown resource'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Endpoint: {String(exposure.generated_config.endpoint || 'N/A')}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Created by {exposure.created_by} on {new Date(exposure.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {exposure.status === 'pending' && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => approveMutation.mutate(exposure.id)}
                        disabled={approveMutation.isPending}
                      >
                        <Check className="h-4 w-4 mr-1" />
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => rejectMutation.mutate(exposure.id)}
                        disabled={rejectMutation.isPending}
                      >
                        <X className="h-4 w-4 mr-1" />
                        Reject
                      </Button>
                    </>
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
    </div>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, CheckCircle, XCircle, Clock, RotateCcw } from 'lucide-react'
import { Button, Card, Badge } from '@/design-system/components'

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

export function DeploymentsView() {
  const [page, setPage] = useState(1)

  const { data, isLoading, refetch } = useQuery<DeploymentListResponse>({
    queryKey: ['deployments', page],
    queryFn: async () => {
      const res = await fetch(`/api/v1/deployments?page=${page}&page_size=20`)
      if (!res.ok) throw new Error('Failed to fetch deployments')
      return res.json()
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
        <h2 className="text-lg font-semibold">Deployment History</h2>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

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
    </div>
  )
}

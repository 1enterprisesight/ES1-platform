import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Cable, FileCode, ExternalLink, RefreshCw, Trash2, Pencil } from 'lucide-react'
import { Card, Button, Badge, Skeleton, SkeletonList, ErrorDisplay, EmptyState } from '../../../design-system/components'
import { useToast } from '../../../shared/contexts/ToastContext'
import { serviceUrl } from '@/config'

interface Connection {
  connection_id: string
  conn_type: string | null
  host: string | null
  port: number | null
  schema_name: string | null
  description: string | null
}

interface ConnectionsResponse {
  connections: Connection[]
  total_entries: number
}

async function fetchConnections(): Promise<ConnectionsResponse> {
  const res = await fetch('/api/v1/airflow/connections')
  if (!res.ok) throw new Error('Failed to fetch connections')
  return res.json()
}

export function ConnectionsView() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { addToast } = useToast()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['airflow', 'connections'],
    queryFn: fetchConnections,
    refetchInterval: 15000,
  })

  const syncMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/airflow/discover', { method: 'POST' })
      if (!res.ok) throw new Error('Failed to sync')
      return res.json()
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['airflow', 'connections'] })
      queryClient.invalidateQueries({ queryKey: ['resources'] })
      addToast({ type: 'success', message: data.message || 'Synced with Airflow' })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (connectionId: string) => {
      const res = await fetch(`/api/v1/airflow/connections/${connectionId}`, { method: 'DELETE' })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to delete connection')
      }
      return res.json()
    },
    onSuccess: (_, connectionId) => {
      queryClient.invalidateQueries({ queryKey: ['airflow', 'connections'] })
      queryClient.invalidateQueries({ queryKey: ['resources'] })
      addToast({ type: 'success', message: `Connection ${connectionId} deleted` })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-40" />
        </div>
        <SkeletonList items={4} />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorDisplay
        title="Failed to load connections"
        message="Could not fetch connections from Airflow. The service may be unavailable."
        error={error as Error}
        onRetry={() => refetch()}
        suggestion="Check if Airflow is running and healthy."
        helpLink={{ label: 'Open Airflow', url: serviceUrl('airflow') }}
      />
    )
  }

  const connections = data?.connections || []

  if (connections.length === 0) {
    return (
      <EmptyState
        icon={Cable}
        title="No connections found"
        description="Create a new connection using the Connection Editor, or configure connections directly in Airflow."
        action={{ label: 'Open Connection Editor', href: '/workflows/connection-editor' }}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {connections.length} connection{connections.length !== 1 ? 's' : ''} configured
        </p>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
            Sync
          </Button>
          <Button size="sm" variant="outline" onClick={() => navigate('/workflows/connection-editor')}>
            <FileCode className="h-4 w-4 mr-1" />
            Connection Editor
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => window.open(serviceUrl('airflow'), '_blank')}
          >
            <ExternalLink className="h-4 w-4 mr-1" />
            Airflow
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {connections.map((conn) => (
          <Card key={conn.connection_id} className="p-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-medium truncate">{conn.connection_id}</h3>
                {conn.conn_type && <Badge variant="secondary">{conn.conn_type}</Badge>}
              </div>
              {conn.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">{conn.description}</p>
              )}
              <div className="text-xs text-muted-foreground space-y-1">
                {conn.host && (
                  <p>
                    <span className="font-medium">Host:</span> {conn.host}
                    {conn.port ? `:${conn.port}` : ''}
                  </p>
                )}
                {conn.schema_name && (
                  <p>
                    <span className="font-medium">Schema:</span> {conn.schema_name}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 pt-2 border-t">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => navigate(`/workflows/connection-editor?connection=${encodeURIComponent(conn.connection_id)}`)}
                  title="Edit connection"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    if (confirm(`Delete connection "${conn.connection_id}"?`)) {
                      deleteMutation.mutate(conn.connection_id)
                    }
                  }}
                  disabled={deleteMutation.isPending}
                  title="Delete connection"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

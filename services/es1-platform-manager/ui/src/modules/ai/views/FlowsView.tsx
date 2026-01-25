import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Button, Badge, StatusIndicator } from '../../../design-system/components'
import { useToast } from '../../../shared/contexts/ToastContext'

interface Flow {
  id: string
  name: string
  description: string | null
  endpoint_name: string | null
  is_component: boolean
  updated_at: string | null
  folder_id: string | null
}

interface FlowsResponse {
  flows: Flow[]
  total: number
}

async function fetchFlows(): Promise<FlowsResponse> {
  const res = await fetch('/api/v1/langflow/flows')
  if (!res.ok) throw new Error('Failed to fetch flows')
  return res.json()
}

async function deleteFlow(flowId: string): Promise<void> {
  const res = await fetch(`/api/v1/langflow/flows/${flowId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete flow')
}

async function discoverFlows(): Promise<{ flows_discovered: number }> {
  const res = await fetch('/api/v1/langflow/discover', {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to discover flows')
  return res.json()
}

export function FlowsView() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const { data, isLoading, error } = useQuery({
    queryKey: ['langflow', 'flows'],
    queryFn: fetchFlows,
  })

  const discoverMutation = useMutation({
    mutationFn: discoverFlows,
    onSuccess: (result) => {
      addToast({
        type: 'success',
        message: `Discovered ${result.flows_discovered} flows`,
      })
      queryClient.invalidateQueries({ queryKey: ['langflow', 'flows'] })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteFlow,
    onSuccess: () => {
      addToast({ type: 'success', message: 'Flow deleted successfully' })
      queryClient.invalidateQueries({ queryKey: ['langflow', 'flows'] })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  if (isLoading) {
    return <div className="text-muted-foreground">Loading flows...</div>
  }

  if (error) {
    return (
      <Card className="p-4 border-destructive">
        <p className="text-destructive">Failed to load flows: {(error as Error).message}</p>
      </Card>
    )
  }

  const flows = data?.flows || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {flows.length} flow{flows.length !== 1 ? 's' : ''} available
        </p>
        <Button
          size="sm"
          variant="outline"
          onClick={() => discoverMutation.mutate()}
          disabled={discoverMutation.isPending}
        >
          {discoverMutation.isPending ? 'Discovering...' : 'Discover Flows'}
        </Button>
      </div>

      {flows.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">No flows found</p>
          <p className="text-sm text-muted-foreground mt-1">
            Create flows in Langflow or click Discover to sync.
          </p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {flows.map((flow) => (
            <Card key={flow.id} className="p-4">
              <div className="flex items-start justify-between">
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <StatusIndicator status="success" />
                    <h3 className="font-medium truncate">{flow.name}</h3>
                  </div>
                  {flow.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {flow.description}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    {flow.is_component && <Badge variant="secondary">Component</Badge>}
                    {flow.endpoint_name && (
                      <Badge variant="outline" className="font-mono text-xs">
                        /{flow.endpoint_name}
                      </Badge>
                    )}
                  </div>
                  {flow.updated_at && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Updated: {new Date(flow.updated_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive hover:text-destructive"
                    onClick={() => {
                      if (confirm(`Delete flow "${flow.name}"?`)) {
                        deleteMutation.mutate(flow.id)
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

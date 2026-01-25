import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Button, Badge, StatusIndicator } from '../../../design-system/components'
import { useToast } from '../../../shared/contexts/ToastContext'

interface Dag {
  dag_id: string
  description: string | null
  is_paused: boolean
  is_active: boolean
  tags: Array<{ name: string }>
  schedule_interval: string | null
  next_dagrun: string | null
}

interface DagsResponse {
  dags: Dag[]
  total_entries: number
}

async function fetchDags(): Promise<DagsResponse> {
  const res = await fetch('/api/v1/airflow/dags')
  if (!res.ok) throw new Error('Failed to fetch DAGs')
  return res.json()
}

async function triggerDag(dagId: string): Promise<void> {
  const res = await fetch(`/api/v1/airflow/dags/${dagId}/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error('Failed to trigger DAG')
}

async function toggleDagPause(dagId: string, isPaused: boolean): Promise<void> {
  const res = await fetch(`/api/v1/airflow/dags/${dagId}/${isPaused ? 'unpause' : 'pause'}`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to update DAG')
}

export function DagsView() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const { data, isLoading, error } = useQuery({
    queryKey: ['airflow', 'dags'],
    queryFn: fetchDags,
  })

  const triggerMutation = useMutation({
    mutationFn: triggerDag,
    onSuccess: (_, dagId) => {
      addToast({ type: 'success', message: `DAG ${dagId} triggered successfully` })
      queryClient.invalidateQueries({ queryKey: ['airflow'] })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  const togglePauseMutation = useMutation({
    mutationFn: ({ dagId, isPaused }: { dagId: string; isPaused: boolean }) =>
      toggleDagPause(dagId, isPaused),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['airflow', 'dags'] })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  if (isLoading) {
    return <div className="text-muted-foreground">Loading DAGs...</div>
  }

  if (error) {
    return (
      <Card className="p-4 border-destructive">
        <p className="text-destructive">Failed to load DAGs: {(error as Error).message}</p>
      </Card>
    )
  }

  const dags = data?.dags || []

  if (dags.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-muted-foreground">No DAGs found</p>
        <p className="text-sm text-muted-foreground mt-1">
          DAGs will appear here once Airflow is connected and has workflows defined.
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {dags.length} DAG{dags.length !== 1 ? 's' : ''} found
        </p>
      </div>

      <div className="grid gap-4">
        {dags.map((dag) => (
          <Card key={dag.dag_id} className="p-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <StatusIndicator
                    status={dag.is_paused ? 'warning' : dag.is_active ? 'success' : 'neutral'}
                  />
                  <h3 className="font-medium">{dag.dag_id}</h3>
                </div>
                {dag.description && (
                  <p className="text-sm text-muted-foreground">{dag.description}</p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  {dag.is_paused && <Badge variant="warning">Paused</Badge>}
                  {dag.schedule_interval && (
                    <Badge variant="secondary">{dag.schedule_interval}</Badge>
                  )}
                  {dag.tags.map((tag) => (
                    <Badge key={tag.name} variant="outline">
                      {tag.name}
                    </Badge>
                  ))}
                </div>
                {dag.next_dagrun && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Next run: {new Date(dag.next_dagrun).toLocaleString()}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    togglePauseMutation.mutate({ dagId: dag.dag_id, isPaused: dag.is_paused })
                  }
                  disabled={togglePauseMutation.isPending}
                >
                  {dag.is_paused ? 'Resume' : 'Pause'}
                </Button>
                <Button
                  size="sm"
                  onClick={() => triggerMutation.mutate(dag.dag_id)}
                  disabled={dag.is_paused || triggerMutation.isPending}
                >
                  Trigger
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

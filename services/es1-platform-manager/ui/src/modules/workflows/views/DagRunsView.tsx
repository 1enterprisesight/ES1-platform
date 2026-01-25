import { useQuery } from '@tanstack/react-query'
import { Card, Badge, StatusIndicator } from '../../../design-system/components'

interface DagRun {
  dag_run_id: string
  dag_id: string
  state: string
  execution_date: string
  start_date: string | null
  end_date: string | null
  logical_date: string | null
}

interface DagRunsResponse {
  dag_runs: DagRun[]
  total_entries: number
}

async function fetchDagRuns(): Promise<DagRunsResponse> {
  const res = await fetch('/api/v1/airflow/dag-runs?limit=50')
  if (!res.ok) throw new Error('Failed to fetch DAG runs')
  return res.json()
}

function getStateStatus(state: string): 'success' | 'error' | 'warning' | 'neutral' {
  switch (state.toLowerCase()) {
    case 'success':
      return 'success'
    case 'failed':
      return 'error'
    case 'running':
    case 'queued':
      return 'warning'
    default:
      return 'neutral'
  }
}

function getStateBadgeVariant(state: string): 'success' | 'destructive' | 'warning' | 'secondary' {
  switch (state.toLowerCase()) {
    case 'success':
      return 'success'
    case 'failed':
      return 'destructive'
    case 'running':
    case 'queued':
      return 'warning'
    default:
      return 'secondary'
  }
}

export function DagRunsView() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['airflow', 'dag-runs'],
    queryFn: fetchDagRuns,
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  if (isLoading) {
    return <div className="text-muted-foreground">Loading DAG runs...</div>
  }

  if (error) {
    return (
      <Card className="p-4 border-destructive">
        <p className="text-destructive">Failed to load DAG runs: {(error as Error).message}</p>
      </Card>
    )
  }

  const runs = data?.dag_runs || []

  if (runs.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-muted-foreground">No DAG runs found</p>
        <p className="text-sm text-muted-foreground mt-1">
          Trigger a DAG to see execution history here.
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Showing {runs.length} most recent runs
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 font-medium text-muted-foreground">Status</th>
              <th className="text-left py-3 px-4 font-medium text-muted-foreground">DAG ID</th>
              <th className="text-left py-3 px-4 font-medium text-muted-foreground">Run ID</th>
              <th className="text-left py-3 px-4 font-medium text-muted-foreground">Started</th>
              <th className="text-left py-3 px-4 font-medium text-muted-foreground">Ended</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={`${run.dag_id}-${run.dag_run_id}`} className="border-b border-border/50">
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <StatusIndicator status={getStateStatus(run.state)} />
                    <Badge variant={getStateBadgeVariant(run.state)}>
                      {run.state}
                    </Badge>
                  </div>
                </td>
                <td className="py-3 px-4 font-medium">{run.dag_id}</td>
                <td className="py-3 px-4 text-muted-foreground font-mono text-xs">
                  {run.dag_run_id}
                </td>
                <td className="py-3 px-4 text-muted-foreground">
                  {run.start_date ? new Date(run.start_date).toLocaleString() : '-'}
                </td>
                <td className="py-3 px-4 text-muted-foreground">
                  {run.end_date ? new Date(run.end_date).toLocaleString() : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

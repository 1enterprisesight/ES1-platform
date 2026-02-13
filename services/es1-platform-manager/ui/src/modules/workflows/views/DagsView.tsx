import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Workflow, FileCode, Clock, ExternalLink, RefreshCw, Trash2 } from 'lucide-react'
import { Card, Button, Badge, StatusIndicator, Skeleton, SkeletonList, ErrorDisplay, EmptyState } from '../../../design-system/components'
import { useToast } from '../../../shared/contexts/ToastContext'
import { serviceUrl } from '@/config'

interface Dag {
  dag_id: string
  description: string | null
  is_paused: boolean
  is_active: boolean
  tags: Array<{ name: string } | string>
  schedule_interval: string | null
  next_dagrun: string | null
}

interface DagsResponse {
  dags: Dag[]
  total_entries: number
}

interface DAGFile {
  filename: string
  dag_id: string
  path: string
  size: number
  modified_at: string
  created_at: string
}

interface DAGFileListResponse {
  files: DAGFile[]
  total: number
  dags_path: string
}

// A unified DAG entry merging Airflow API + filesystem data
interface MergedDag {
  dag_id: string
  description: string | null
  is_paused: boolean
  is_active: boolean
  tags: string[]
  schedule_interval: string | null
  next_dagrun: string | null
  // Sync status
  status: 'synced' | 'pending_parse' | 'airflow_only'
  // File info (if file exists)
  filename: string | null
  modified_at: string | null
}

function mergeDags(airflowDags: Dag[], dagFiles: DAGFile[]): MergedDag[] {
  const merged: MergedDag[] = []
  const filesByDagId = new Map<string, DAGFile>()

  for (const file of dagFiles) {
    filesByDagId.set(file.dag_id, file)
  }

  const seenDagIds = new Set<string>()

  // Add all Airflow DAGs, enriched with file info
  for (const dag of airflowDags) {
    seenDagIds.add(dag.dag_id)
    const file = filesByDagId.get(dag.dag_id)
    merged.push({
      dag_id: dag.dag_id,
      description: dag.description,
      is_paused: dag.is_paused,
      is_active: dag.is_active,
      tags: dag.tags.map(t => typeof t === 'string' ? t : t.name),
      schedule_interval: dag.schedule_interval,
      next_dagrun: dag.next_dagrun,
      status: file ? 'synced' : 'airflow_only',
      filename: file?.filename || null,
      modified_at: file?.modified_at || null,
    })
  }

  // Add DAG files NOT yet in Airflow (pending parse)
  for (const file of dagFiles) {
    if (!seenDagIds.has(file.dag_id)) {
      merged.push({
        dag_id: file.dag_id,
        description: null,
        is_paused: true, // New DAGs start paused
        is_active: false,
        tags: [],
        schedule_interval: null,
        next_dagrun: null,
        status: 'pending_parse',
        filename: file.filename,
        modified_at: file.modified_at,
      })
    }
  }

  return merged
}

async function fetchDags(): Promise<DagsResponse> {
  const res = await fetch('/api/v1/airflow/dags?only_active=false')
  if (!res.ok) throw new Error('Failed to fetch DAGs')
  return res.json()
}

async function fetchDagFiles(): Promise<DAGFileListResponse> {
  const res = await fetch('/api/v1/airflow/dag-files')
  if (!res.ok) throw new Error('Failed to fetch DAG files')
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
  const navigate = useNavigate()
  const { addToast } = useToast()

  const { data: airflowData, isLoading: airflowLoading, error: airflowError, refetch: refetchAirflow } = useQuery({
    queryKey: ['airflow', 'dags'],
    queryFn: fetchDags,
    refetchInterval: 15000, // Auto-refresh every 15s to catch newly parsed DAGs
  })

  const { data: filesData, isLoading: filesLoading } = useQuery({
    queryKey: ['dag-files'],
    queryFn: fetchDagFiles,
    refetchInterval: 15000,
  })

  const triggerMutation = useMutation({
    mutationFn: triggerDag,
    onSuccess: (_, dagId) => {
      addToast({ type: 'success', message: `DAG ${dagId} triggered successfully` })
      queryClient.invalidateQueries({ queryKey: ['airflow', 'dags'] })
      queryClient.invalidateQueries({ queryKey: ['airflow', 'dag-runs'] })
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

  const syncMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/airflow/discover', { method: 'POST' })
      if (!res.ok) throw new Error('Failed to sync')
      return res.json()
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['airflow', 'dags'] })
      queryClient.invalidateQueries({ queryKey: ['dag-files'] })
      addToast({
        type: 'success',
        message: data.message || 'Synced with Airflow',
      })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  const cleanupMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/airflow/dags/cleanup', { method: 'POST' })
      if (!res.ok) throw new Error('Failed to cleanup')
      return res.json()
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['airflow', 'dags'] })
      addToast({
        type: 'success',
        message: data.message || 'Cleanup complete',
      })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
    },
  })

  const isLoading = airflowLoading || filesLoading

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-32" />
        </div>
        <SkeletonList items={4} />
      </div>
    )
  }

  if (airflowError) {
    return (
      <ErrorDisplay
        title="Failed to load DAGs"
        message="Could not fetch DAGs from Airflow. The service may be unavailable or still starting."
        error={airflowError as Error}
        onRetry={() => refetchAirflow()}
        suggestion="Check if Airflow is running and healthy. You can also try accessing Airflow directly."
        helpLink={{ label: 'Open Airflow', url: serviceUrl('airflow') }}
      />
    )
  }

  const dags = mergeDags(
    airflowData?.dags || [],
    filesData?.files || [],
  )

  if (dags.length === 0) {
    return (
      <EmptyState
        icon={Workflow}
        title="No DAGs found"
        description="Create a new DAG using the DAG Editor, or define DAG files directly in Airflow."
        action={{ label: 'Open DAG Editor', href: '/workflows/editor' }}
      />
    )
  }

  const pendingCount = dags.filter(d => d.status === 'pending_parse').length
  const staleCount = dags.filter(d => d.status === 'airflow_only').length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <p className="text-sm text-muted-foreground">
            {dags.length} DAG{dags.length !== 1 ? 's' : ''}
          </p>
          {pendingCount > 0 && (
            <Badge variant="warning">
              <Clock className="h-3 w-3 mr-1" />
              {pendingCount} pending parse
            </Badge>
          )}
        </div>
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
          {staleCount > 0 && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                if (confirm(`Remove ${staleCount} stale DAG(s) from Airflow that no longer have files?`))
                  cleanupMutation.mutate()
              }}
              disabled={cleanupMutation.isPending}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Clean Up ({staleCount})
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => navigate('/workflows/editor')}>
            <FileCode className="h-4 w-4 mr-1" />
            DAG Editor
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

      <div className="grid gap-4">
        {dags.map((dag) => (
          <Card key={dag.dag_id} className="p-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1 min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <StatusIndicator
                    status={
                      dag.status === 'pending_parse'
                        ? 'warning'
                        : dag.is_paused
                          ? 'warning'
                          : dag.is_active
                            ? 'success'
                            : 'neutral'
                    }
                  />
                  <h3 className="font-medium">{dag.dag_id}</h3>
                  {dag.status === 'pending_parse' && (
                    <Badge variant="warning" className="text-xs">
                      <Clock className="h-3 w-3 mr-1" />
                      Pending Parse
                    </Badge>
                  )}
                  {dag.status === 'airflow_only' && (
                    <Badge variant="secondary" className="text-xs">Airflow Only</Badge>
                  )}
                </div>
                {dag.description && (
                  <p className="text-sm text-muted-foreground">{dag.description}</p>
                )}
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  {dag.is_paused && dag.status !== 'pending_parse' && (
                    <Badge variant="warning">Paused</Badge>
                  )}
                  {dag.schedule_interval && (
                    <Badge variant="secondary">{dag.schedule_interval}</Badge>
                  )}
                  {dag.tags.map((tag) => (
                    <Badge key={tag} variant="outline">{tag}</Badge>
                  ))}
                </div>
                {dag.next_dagrun && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Next run: {new Date(dag.next_dagrun).toLocaleString()}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-4">
                {dag.filename && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => navigate(`/workflows/editor?file=${encodeURIComponent(dag.filename!)}`)}
                    title="Edit DAG file"
                  >
                    <FileCode className="h-4 w-4" />
                  </Button>
                )}
                {dag.status !== 'pending_parse' && (
                  <>
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
                  </>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ExternalLink,
  Eye,
} from 'lucide-react'
import { useState } from 'react'

interface Execution {
  id: string
  workflow_id: string
  workflow_name: string | null
  status: string
  started_at: string | null
  finished_at: string | null
  mode: string | null
}

interface ExecutionListResponse {
  executions: Execution[]
  total: number
}

interface ExecutionDetail extends Execution {
  data: Record<string, unknown>
  error: string | null
}

async function fetchExecutions(limit: number = 50): Promise<ExecutionListResponse> {
  const res = await fetch(`/api/v1/n8n/executions?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch executions')
  return res.json()
}

async function fetchExecutionDetail(id: string): Promise<ExecutionDetail> {
  const res = await fetch(`/api/v1/n8n/executions/${id}`)
  if (!res.ok) throw new Error('Failed to fetch execution detail')
  return res.json()
}

function StatusBadge({ status }: { status: string }) {
  switch (status.toLowerCase()) {
    case 'success':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
          <CheckCircle className="w-3 h-3" />
          Success
        </span>
      )
    case 'error':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
          <XCircle className="w-3 h-3" />
          Error
        </span>
      )
    case 'running':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
          <RefreshCw className="w-3 h-3 animate-spin" />
          Running
        </span>
      )
    case 'waiting':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
          <Clock className="w-3 h-3" />
          Waiting
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400">
          <AlertTriangle className="w-3 h-3" />
          {status}
        </span>
      )
  }
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return '—'
  const startDate = new Date(start)
  const endDate = end ? new Date(end) : new Date()
  const duration = endDate.getTime() - startDate.getTime()

  if (duration < 1000) return `${duration}ms`
  if (duration < 60000) return `${(duration / 1000).toFixed(1)}s`
  return `${(duration / 60000).toFixed(1)}m`
}

export function N8NExecutionsView() {
  const [selectedExecution, setSelectedExecution] = useState<ExecutionDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState<string | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['n8n-executions'],
    queryFn: () => fetchExecutions(50),
    refetchInterval: 10000,
  })

  const handleViewDetails = async (executionId: string) => {
    setLoadingDetail(executionId)
    try {
      const detail = await fetchExecutionDetail(executionId)
      setSelectedExecution(detail)
    } catch (e) {
      console.error('Failed to load execution detail:', e)
    } finally {
      setLoadingDetail(null)
    }
  }

  const openInN8N = (executionId: string) => {
    window.open(`http://localhost:5678/execution/${executionId}`, '_blank')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <div className="flex items-center gap-2 text-destructive">
          <XCircle className="w-5 h-5" />
          <span>Failed to load executions. Is n8n running?</span>
        </div>
        <button
          onClick={() => refetch()}
          className="mt-2 text-sm text-primary hover:underline"
        >
          Try again
        </button>
      </div>
    )
  }

  const executions = data?.executions || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {executions.length} execution{executions.length !== 1 ? 's' : ''} found
        </p>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-md hover:bg-accent"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {executions.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <Clock className="w-12 h-12 mx-auto text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No executions yet</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Execute a workflow to see execution history here.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Workflow
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Mode
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Started
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {executions.map((execution) => (
                <tr key={execution.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <StatusBadge status={execution.status} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium">
                      {execution.workflow_name || 'Unknown'}
                    </span>
                    <p className="text-xs text-muted-foreground">
                      Execution: {execution.id}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-muted-foreground capitalize">
                      {execution.mode || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {execution.started_at
                      ? new Date(execution.started_at).toLocaleString()
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {formatDuration(execution.started_at, execution.finished_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleViewDetails(execution.id)}
                        disabled={loadingDetail === execution.id}
                        className="p-1.5 rounded hover:bg-accent disabled:opacity-50"
                        title="View details"
                      >
                        {loadingDetail === execution.id ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => openInN8N(execution.id)}
                        className="p-1.5 rounded hover:bg-accent"
                        title="View in n8n"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Execution Detail Modal */}
      {selectedExecution && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg shadow-lg w-full max-w-2xl max-h-[80vh] overflow-hidden">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Execution Details</h3>
                <p className="text-sm text-muted-foreground">
                  {selectedExecution.workflow_name || 'Unknown workflow'}
                </p>
              </div>
              <button
                onClick={() => setSelectedExecution(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh] space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Status</p>
                  <StatusBadge status={selectedExecution.status} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Mode</p>
                  <p className="text-sm capitalize">
                    {selectedExecution.mode || '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Started</p>
                  <p className="text-sm">
                    {selectedExecution.started_at
                      ? new Date(selectedExecution.started_at).toLocaleString()
                      : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Duration</p>
                  <p className="text-sm">
                    {formatDuration(
                      selectedExecution.started_at,
                      selectedExecution.finished_at
                    )}
                  </p>
                </div>
              </div>

              {selectedExecution.error && (
                <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
                  <p className="text-xs text-muted-foreground uppercase mb-2">
                    Error
                  </p>
                  <p className="text-sm text-destructive font-mono">
                    {selectedExecution.error}
                  </p>
                </div>
              )}

              <div>
                <p className="text-xs text-muted-foreground uppercase mb-2">
                  Output Data
                </p>
                <pre className="text-xs bg-muted/50 rounded-lg p-4 overflow-x-auto max-h-64">
                  {JSON.stringify(selectedExecution.data, null, 2) || 'No data'}
                </pre>
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-2">
              <button
                onClick={() => openInN8N(selectedExecution.id)}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border rounded-md hover:bg-accent"
              >
                <ExternalLink className="w-4 h-4" />
                View in n8n
              </button>
              <button
                onClick={() => setSelectedExecution(null)}
                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

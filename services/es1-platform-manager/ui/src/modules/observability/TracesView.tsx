import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Badge, StatusIndicator } from '../../design-system/components'

interface Trace {
  id: string
  name: string | null
  user_id: string | null
  session_id: string | null
  input: any
  output: any
  metadata: Record<string, any> | null
  timestamp: string | null
  level: string | null
}

interface TracesResponse {
  data: Trace[]
  meta: {
    totalItems?: number
    page?: number
    limit?: number
  }
}

async function fetchTraces(page: number, limit: number): Promise<TracesResponse> {
  const res = await fetch(`/api/v1/observability/traces?page=${page}&limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch traces')
  return res.json()
}

export function TracesView() {
  const [page, setPage] = useState(1)
  const limit = 20

  const { data, isLoading, error } = useQuery({
    queryKey: ['observability', 'traces', page],
    queryFn: () => fetchTraces(page, limit),
  })

  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null)

  if (isLoading) {
    return <div className="text-muted-foreground">Loading traces...</div>
  }

  if (error) {
    return (
      <Card className="p-4 border-destructive">
        <p className="text-destructive">Failed to load traces: {(error as Error).message}</p>
      </Card>
    )
  }

  const traces = data?.data || []
  const totalItems = data?.meta?.totalItems || 0

  if (traces.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-muted-foreground">No traces found</p>
        <p className="text-sm text-muted-foreground mt-1">
          Traces will appear here when Langfuse receives data.
        </p>
      </Card>
    )
  }

  return (
    <div className="flex gap-6">
      <div className="flex-1 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {traces.length} of {totalItems} traces
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-2 py-1 text-sm border rounded disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={traces.length < limit}
              className="px-2 py-1 text-sm border rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>

        <div className="space-y-2">
          {traces.map((trace) => (
            <button
              key={trace.id}
              onClick={() => setSelectedTrace(trace)}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selectedTrace?.id === trace.id
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <StatusIndicator
                    status={trace.level === 'ERROR' ? 'error' : 'success'}
                  />
                  <span className="font-medium">{trace.name || 'Unnamed trace'}</span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {trace.timestamp
                    ? new Date(trace.timestamp).toLocaleString()
                    : 'Unknown time'}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                {trace.user_id && (
                  <Badge variant="outline" className="text-xs">
                    User: {trace.user_id}
                  </Badge>
                )}
                {trace.session_id && (
                  <Badge variant="outline" className="text-xs">
                    Session: {trace.session_id.slice(0, 8)}...
                  </Badge>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {selectedTrace && (
        <Card className="w-96 p-4 h-fit sticky top-4">
          <h3 className="font-medium mb-4">Trace Details</h3>
          <div className="space-y-4 text-sm">
            <div>
              <label className="text-muted-foreground block mb-1">ID</label>
              <code className="text-xs bg-muted px-2 py-1 rounded block overflow-x-auto">
                {selectedTrace.id}
              </code>
            </div>
            <div>
              <label className="text-muted-foreground block mb-1">Name</label>
              <p>{selectedTrace.name || 'Unnamed'}</p>
            </div>
            {selectedTrace.input && (
              <div>
                <label className="text-muted-foreground block mb-1">Input</label>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-32">
                  {typeof selectedTrace.input === 'string'
                    ? selectedTrace.input
                    : JSON.stringify(selectedTrace.input, null, 2)}
                </pre>
              </div>
            )}
            {selectedTrace.output && (
              <div>
                <label className="text-muted-foreground block mb-1">Output</label>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-32">
                  {typeof selectedTrace.output === 'string'
                    ? selectedTrace.output
                    : JSON.stringify(selectedTrace.output, null, 2)}
                </pre>
              </div>
            )}
            {selectedTrace.metadata && Object.keys(selectedTrace.metadata).length > 0 && (
              <div>
                <label className="text-muted-foreground block mb-1">Metadata</label>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-32">
                  {JSON.stringify(selectedTrace.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}

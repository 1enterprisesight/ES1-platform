import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Badge } from '../../design-system/components'

interface Session {
  id: string
  created_at: string | null
  project_id: string | null
}

interface SessionsResponse {
  data: Session[]
  meta: {
    totalItems?: number
    page?: number
    limit?: number
  }
}

async function fetchSessions(page: number, limit: number): Promise<SessionsResponse> {
  const res = await fetch(`/api/v1/observability/sessions?page=${page}&limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch sessions')
  return res.json()
}

export function SessionsView() {
  const [page, setPage] = useState(1)
  const limit = 20

  const { data, isLoading, error } = useQuery({
    queryKey: ['observability', 'sessions', page],
    queryFn: () => fetchSessions(page, limit),
  })

  if (isLoading) {
    return <div className="text-muted-foreground">Loading sessions...</div>
  }

  if (error) {
    return (
      <Card className="p-4 border-destructive">
        <p className="text-destructive">Failed to load sessions: {(error as Error).message}</p>
      </Card>
    )
  }

  const sessions = data?.data || []
  const totalItems = data?.meta?.totalItems || 0

  if (sessions.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-muted-foreground">No sessions found</p>
        <p className="text-sm text-muted-foreground mt-1">
          Sessions group related traces together.
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Showing {sessions.length} of {totalItems} sessions
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
            disabled={sessions.length < limit}
            className="px-2 py-1 text-sm border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sessions.map((session) => (
          <Card key={session.id} className="p-4">
            <div className="space-y-2">
              <h3 className="font-medium font-mono text-sm truncate" title={session.id}>
                {session.id}
              </h3>
              <div className="flex items-center gap-2">
                {session.project_id && (
                  <Badge variant="outline" className="text-xs">
                    Project: {session.project_id.slice(0, 8)}...
                  </Badge>
                )}
              </div>
              {session.created_at && (
                <p className="text-xs text-muted-foreground">
                  Created: {new Date(session.created_at).toLocaleString()}
                </p>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

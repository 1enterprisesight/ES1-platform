import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import {
  RefreshCw,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'

interface Run {
  run_id: string
  crew_id?: string
  conversation_id?: string
  status: string
  started_at: string
  result?: string
  error?: string
  messages?: Array<{ role: string; name: string; content: string }>
}

export function TasksView() {
  const [crewaiRuns, setCrewaiRuns] = useState<Run[]>([])
  const [autogenRuns, setAutogenRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set())

  const fetchRuns = async () => {
    setLoading(true)
    setError(null)
    try {
      const [crewaiResponse, autogenResponse] = await Promise.allSettled([
        fetch('http://localhost:8100/runs'),
        fetch('http://localhost:8101/runs'),
      ])

      if (crewaiResponse.status === 'fulfilled' && crewaiResponse.value.ok) {
        const data = await crewaiResponse.value.json()
        setCrewaiRuns(data.runs || [])
      }

      if (autogenResponse.status === 'fulfilled' && autogenResponse.value.ok) {
        const data = await autogenResponse.value.json()
        setAutogenRuns(data.runs || [])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRuns()
    const interval = setInterval(fetchRuns, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const toggleExpanded = (runId: string) => {
    const newExpanded = new Set(expandedRuns)
    if (newExpanded.has(runId)) {
      newExpanded.delete(runId)
    } else {
      newExpanded.add(runId)
    }
    setExpandedRuns(newExpanded)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'running':
        return <Play className="h-4 w-4 text-blue-500 animate-pulse" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>
      case 'running':
        return <Badge variant="default">Running</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const allRuns = [
    ...crewaiRuns.map((r) => ({ ...r, framework: 'crewai' as const })),
    ...autogenRuns.map((r) => ({ ...r, framework: 'autogen' as const })),
  ].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchRuns} className="mt-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-muted-foreground">
          View running and completed agent tasks across frameworks
        </p>
        <Button variant="outline" size="sm" onClick={fetchRuns} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Total Runs</p>
            <p className="text-2xl font-semibold">{allRuns.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Running</p>
            <p className="text-2xl font-semibold text-blue-500">
              {allRuns.filter((r) => r.status === 'running').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Completed</p>
            <p className="text-2xl font-semibold text-green-500">
              {allRuns.filter((r) => r.status === 'completed').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Failed</p>
            <p className="text-2xl font-semibold text-red-500">
              {allRuns.filter((r) => r.status === 'failed').length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Runs List */}
      {allRuns.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">No tasks have been run yet.</p>
            <p className="text-sm text-muted-foreground mt-2">
              Create a crew in CrewAI or start a conversation in AutoGen to see tasks here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {allRuns.map((run) => (
            <Card key={run.run_id} className="overflow-hidden">
              <div
                className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => toggleExpanded(run.run_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {expandedRuns.has(run.run_id) ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    {getStatusIcon(run.status)}
                    <div>
                      <p className="font-medium">
                        {run.crew_id || run.conversation_id || run.run_id}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {run.run_id} • {formatDate(run.started_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="capitalize">
                      {run.framework}
                    </Badge>
                    {getStatusBadge(run.status)}
                  </div>
                </div>
              </div>

              {expandedRuns.has(run.run_id) && (
                <div className="px-4 pb-4 border-t bg-muted/30">
                  <div className="pt-4 space-y-4">
                    {run.error && (
                      <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                        <p className="text-sm font-medium text-destructive">Error</p>
                        <p className="text-sm text-destructive/80 mt-1">{run.error}</p>
                      </div>
                    )}

                    {run.result && (
                      <div>
                        <p className="text-sm font-medium mb-2">Result</p>
                        <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-40">
                          {run.result}
                        </pre>
                      </div>
                    )}

                    {run.messages && run.messages.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">
                          Messages ({run.messages.length})
                        </p>
                        <div className="space-y-2 max-h-60 overflow-auto">
                          {run.messages.map((msg, idx) => (
                            <div
                              key={idx}
                              className="p-2 bg-muted rounded-md text-sm"
                            >
                              <p className="text-xs text-muted-foreground mb-1">
                                {msg.name || msg.role}
                              </p>
                              <p className="whitespace-pre-wrap">{msg.content}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react'
import { apiUrl } from '@/config'

interface ErrorRequest {
  id: string
  request_id: string
  timestamp: string
  source_service: string | null
  source_ip: string | null
  method: string
  path: string
  response_status: number
  latency_ms: number
  error_code: string | null
  error_message: string | null
}

export function ErrorsView() {
  const [errors, setErrors] = useState<ErrorRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [periodHours, setPeriodHours] = useState(24)
  const [expandedError, setExpandedError] = useState<string | null>(null)

  const fetchErrors = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(
        apiUrl(`traffic/errors?hours=${periodHours}&limit=100`)
      )
      if (!response.ok) throw new Error('Failed to fetch errors')
      const data = await response.json()
      setErrors(data.errors || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchErrors()
  }, [periodHours])

  const getStatusBadge = (status: number) => {
    if (status >= 400 && status < 500) {
      return <Badge variant="warning">{status} Client Error</Badge>
    }
    return <Badge variant="destructive">{status} Server Error</Badge>
  }

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET':
        return 'bg-blue-500'
      case 'POST':
        return 'bg-green-500'
      case 'PUT':
      case 'PATCH':
        return 'bg-yellow-500'
      case 'DELETE':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  const formatTimestamp = (ts: string) => {
    return new Date(ts).toLocaleString()
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchErrors} className="mt-4">
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
        <div className="flex items-center gap-4">
          <select
            value={periodHours}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setPeriodHours(parseInt(e.target.value))}
            className="px-3 py-2 border rounded-md bg-background text-sm"
          >
            <option value="1">Last 1 hour</option>
            <option value="6">Last 6 hours</option>
            <option value="24">Last 24 hours</option>
            <option value="48">Last 48 hours</option>
            <option value="168">Last 7 days</option>
          </select>
          <p className="text-sm text-muted-foreground">
            {errors.length} error{errors.length !== 1 ? 's' : ''} found
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchErrors} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Errors List */}
      {errors.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <AlertTriangle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No errors in this time period.</p>
            <p className="text-sm text-muted-foreground mt-2">
              That's good news!
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {errors.map((err) => (
            <Card key={err.id} className="overflow-hidden border-l-4 border-l-destructive">
              <div
                className="p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() =>
                  setExpandedError(expandedError === err.id ? null : err.id)
                }
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {expandedError === err.id ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <span
                      className={`px-2 py-0.5 text-xs font-medium text-white rounded ${getMethodColor(
                        err.method
                      )}`}
                    >
                      {err.method}
                    </span>
                    <span className="font-mono text-sm truncate max-w-md">
                      {err.path}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">
                      {formatTimestamp(err.timestamp)}
                    </span>
                    {getStatusBadge(err.response_status)}
                  </div>
                </div>
              </div>

              {expandedError === err.id && (
                <div className="px-4 pb-4 border-t bg-muted/30">
                  <div className="pt-4 space-y-3">
                    <div className="grid gap-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Request ID:</span>
                        <span className="font-mono">{err.request_id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Source:</span>
                        <span>{err.source_service || err.source_ip || 'Unknown'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Latency:</span>
                        <span>{err.latency_ms}ms</span>
                      </div>
                      {err.error_code && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Error Code:</span>
                          <span>{err.error_code}</span>
                        </div>
                      )}
                    </div>
                    {err.error_message && (
                      <div>
                        <p className="text-sm font-medium mb-1">Error Message</p>
                        <pre className="text-xs bg-destructive/10 text-destructive p-2 rounded-md overflow-auto">
                          {err.error_message}
                        </pre>
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

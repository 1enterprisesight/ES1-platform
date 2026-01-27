import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'

interface ApiRequest {
  id: string
  request_id: string
  timestamp: string
  source_service: string | null
  source_ip: string | null
  method: string
  path: string
  response_status: number
  latency_ms: number
}

export function RequestsView() {
  const [requests, setRequests] = useState<ApiRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')
  const [expandedRequest, setExpandedRequest] = useState<string | null>(null)

  const fetchRequests = async () => {
    setLoading(true)
    setError(null)
    try {
      const statusFilter = filter !== 'all' ? `&status_filter=${filter}` : ''
      const response = await fetch(
        `http://localhost:8000/api/v1/traffic/requests?limit=100${statusFilter}`
      )
      if (!response.ok) throw new Error('Failed to fetch requests')
      const data = await response.json()
      setRequests(data.requests || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRequests()
    const interval = setInterval(fetchRequests, 10000)
    return () => clearInterval(interval)
  }, [filter])

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'success'
    if (status >= 400 && status < 500) return 'warning'
    if (status >= 500) return 'destructive'
    return 'secondary'
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
            <Button onClick={fetchRequests} className="mt-4">
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
            value={filter}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilter(e.target.value)}
            className="px-3 py-2 border rounded-md bg-background text-sm"
          >
            <option value="all">All Requests</option>
            <option value="success">Success Only</option>
            <option value="error">Errors Only</option>
          </select>
        </div>
        <Button variant="outline" size="sm" onClick={fetchRequests} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Requests List */}
      {requests.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">No requests found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {requests.map((req) => (
            <Card key={req.id} className="overflow-hidden">
              <div
                className="p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() =>
                  setExpandedRequest(expandedRequest === req.id ? null : req.id)
                }
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {expandedRequest === req.id ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <span
                      className={`px-2 py-0.5 text-xs font-medium text-white rounded ${getMethodColor(
                        req.method
                      )}`}
                    >
                      {req.method}
                    </span>
                    <span className="font-mono text-sm truncate max-w-md">
                      {req.path}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">
                      {req.latency_ms}ms
                    </span>
                    <Badge variant={getStatusColor(req.response_status)}>
                      {req.response_status}
                    </Badge>
                  </div>
                </div>
              </div>

              {expandedRequest === req.id && (
                <div className="px-4 pb-4 border-t bg-muted/30">
                  <div className="pt-4 grid gap-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Request ID:</span>
                      <span className="font-mono">{req.request_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Timestamp:</span>
                      <span>{formatTimestamp(req.timestamp)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Source:</span>
                      <span>{req.source_service || req.source_ip || 'Unknown'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Latency:</span>
                      <span>{req.latency_ms}ms</span>
                    </div>
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

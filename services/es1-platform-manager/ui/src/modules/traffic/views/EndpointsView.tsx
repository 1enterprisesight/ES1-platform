import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw } from 'lucide-react'

interface EndpointStats {
  method: string
  path: string
  request_count: number
  avg_latency_ms: number
  error_count: number
  error_rate: number
}

export function EndpointsView() {
  const [endpoints, setEndpoints] = useState<EndpointStats[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [periodHours, setPeriodHours] = useState(24)

  const fetchEndpoints = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/traffic/endpoints?hours=${periodHours}&limit=50`
      )
      if (!response.ok) throw new Error('Failed to fetch endpoints')
      const data = await response.json()
      setEndpoints(data.endpoints || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEndpoints()
  }, [periodHours])

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

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchEndpoints} className="mt-4">
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
        </div>
        <Button variant="outline" size="sm" onClick={fetchEndpoints} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Endpoints Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top Endpoints by Request Count</CardTitle>
        </CardHeader>
        <CardContent>
          {endpoints.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No endpoint data available for this period.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3 font-medium">Endpoint</th>
                    <th className="text-right py-2 px-3 font-medium">Requests</th>
                    <th className="text-right py-2 px-3 font-medium">Avg Latency</th>
                    <th className="text-right py-2 px-3 font-medium">Error Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {endpoints.map((ep, idx) => (
                    <tr key={idx} className="border-b hover:bg-muted/50">
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 text-xs font-medium text-white rounded ${getMethodColor(
                              ep.method
                            )}`}
                          >
                            {ep.method}
                          </span>
                          <span className="font-mono text-xs truncate max-w-md">
                            {ep.path}
                          </span>
                        </div>
                      </td>
                      <td className="text-right py-2 px-3">
                        {ep.request_count.toLocaleString()}
                      </td>
                      <td className="text-right py-2 px-3">{ep.avg_latency_ms.toFixed(0)}ms</td>
                      <td className="text-right py-2 px-3">
                        {ep.error_rate > 0 ? (
                          <Badge variant="destructive" className="text-xs">
                            {ep.error_rate.toFixed(1)}%
                          </Badge>
                        ) : (
                          <Badge variant="success" className="text-xs">
                            0%
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

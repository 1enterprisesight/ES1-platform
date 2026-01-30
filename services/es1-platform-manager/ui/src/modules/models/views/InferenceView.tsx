import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, Activity, Zap, Clock, AlertTriangle } from 'lucide-react'
import { apiUrl } from '@/config'

interface EndpointMetric {
  path: string
  request_count: number
  avg_latency_ms: number
  error_count: number
  error_rate: number
  first_request: string | null
  last_request: string | null
}

interface InferenceMetrics {
  period_hours: number
  inference: EndpointMetric[]
  agents: EndpointMetric[]
  knowledge: EndpointMetric[]
  totals: {
    total_requests: number
    total_errors: number
    error_rate: number
    avg_latency_ms: number
  }
}

export function InferenceView() {
  const [metrics, setMetrics] = useState<InferenceMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [periodHours, setPeriodHours] = useState(24)

  const fetchMetrics = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(
        apiUrl(`models/inference/metrics?hours=${periodHours}`)
      )
      if (!response.ok) throw new Error('Failed to fetch inference metrics')
      const data = await response.json()
      setMetrics(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
  }, [periodHours])

  const getLatencyColor = (latency: number) => {
    if (latency < 100) return 'text-green-500'
    if (latency < 500) return 'text-yellow-500'
    return 'text-red-500'
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchMetrics} className="mt-4">
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
            onChange={(e) => setPeriodHours(parseInt(e.target.value))}
            className="px-3 py-2 border rounded-md bg-background text-sm"
          >
            <option value="1">Last 1 hour</option>
            <option value="6">Last 6 hours</option>
            <option value="24">Last 24 hours</option>
            <option value="48">Last 48 hours</option>
            <option value="168">Last 7 days</option>
          </select>
        </div>
        <Button variant="outline" size="sm" onClick={fetchMetrics} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Total Requests</p>
            </div>
            <p className="text-3xl font-bold mt-2">
              {metrics?.totals.total_requests.toLocaleString() || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Avg Latency</p>
            </div>
            <p className={`text-3xl font-bold mt-2 ${getLatencyColor(metrics?.totals.avg_latency_ms || 0)}`}>
              {metrics?.totals.avg_latency_ms.toFixed(0) || 0}ms
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <p className="text-sm text-muted-foreground">Errors</p>
            </div>
            <p className="text-3xl font-bold mt-2 text-red-500">
              {metrics?.totals.total_errors || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Error Rate</p>
            </div>
            <p className={`text-3xl font-bold mt-2 ${(metrics?.totals.error_rate || 0) > 5 ? 'text-red-500' : 'text-green-500'}`}>
              {metrics?.totals.error_rate.toFixed(1) || 0}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Inference Endpoints */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">LLM Inference (Ollama)</CardTitle>
        </CardHeader>
        <CardContent>
          {!metrics?.inference.length ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No inference requests in this time period.
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
                  {metrics.inference.map((ep) => (
                    <tr key={ep.path} className="border-b hover:bg-muted/50">
                      <td className="py-2 px-3 font-mono text-xs">{ep.path}</td>
                      <td className="text-right py-2 px-3">{ep.request_count.toLocaleString()}</td>
                      <td className={`text-right py-2 px-3 ${getLatencyColor(ep.avg_latency_ms)}`}>
                        {ep.avg_latency_ms.toFixed(0)}ms
                      </td>
                      <td className="text-right py-2 px-3">
                        {ep.error_rate > 0 ? (
                          <Badge variant="destructive" className="text-xs">
                            {ep.error_rate.toFixed(1)}%
                          </Badge>
                        ) : (
                          <Badge variant="success" className="text-xs">0%</Badge>
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

      {/* Agent Endpoints */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Agent Invocations</CardTitle>
        </CardHeader>
        <CardContent>
          {!metrics?.agents.length ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No agent invocations in this time period.
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
                  {metrics.agents.map((ep) => (
                    <tr key={ep.path} className="border-b hover:bg-muted/50">
                      <td className="py-2 px-3 font-mono text-xs">{ep.path}</td>
                      <td className="text-right py-2 px-3">{ep.request_count.toLocaleString()}</td>
                      <td className={`text-right py-2 px-3 ${getLatencyColor(ep.avg_latency_ms)}`}>
                        {ep.avg_latency_ms.toFixed(0)}ms
                      </td>
                      <td className="text-right py-2 px-3">
                        {ep.error_rate > 0 ? (
                          <Badge variant="destructive" className="text-xs">
                            {ep.error_rate.toFixed(1)}%
                          </Badge>
                        ) : (
                          <Badge variant="success" className="text-xs">0%</Badge>
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

      {/* Knowledge Endpoints */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Knowledge Search</CardTitle>
        </CardHeader>
        <CardContent>
          {!metrics?.knowledge.length ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No knowledge search requests in this time period.
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
                  {metrics.knowledge.map((ep) => (
                    <tr key={ep.path} className="border-b hover:bg-muted/50">
                      <td className="py-2 px-3 font-mono text-xs">{ep.path}</td>
                      <td className="text-right py-2 px-3">{ep.request_count.toLocaleString()}</td>
                      <td className={`text-right py-2 px-3 ${getLatencyColor(ep.avg_latency_ms)}`}>
                        {ep.avg_latency_ms.toFixed(0)}ms
                      </td>
                      <td className="text-right py-2 px-3">
                        {ep.error_rate > 0 ? (
                          <Badge variant="destructive" className="text-xs">
                            {ep.error_rate.toFixed(1)}%
                          </Badge>
                        ) : (
                          <Badge variant="success" className="text-xs">0%</Badge>
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

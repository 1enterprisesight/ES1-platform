import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, Activity, Clock, AlertTriangle, CheckCircle } from 'lucide-react'

interface TrafficStats {
  period_hours: number
  total_requests: number
  success_count: number
  client_error_count: number
  server_error_count: number
  success_rate: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  p99_latency_ms: number
}

interface ServiceStats {
  service: string
  request_count: number
  avg_latency_ms: number
  error_count: number
}

export function OverviewView() {
  const [stats, setStats] = useState<TrafficStats | null>(null)
  const [services, setServices] = useState<ServiceStats[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [periodHours, setPeriodHours] = useState(24)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsResponse, servicesResponse] = await Promise.all([
        fetch(`http://localhost:8000/api/v1/traffic/stats?hours=${periodHours}`),
        fetch(`http://localhost:8000/api/v1/traffic/services?hours=${periodHours}`),
      ])

      if (!statsResponse.ok) throw new Error('Failed to fetch traffic stats')
      if (!servicesResponse.ok) throw new Error('Failed to fetch service stats')

      const statsData = await statsResponse.json()
      const servicesData = await servicesResponse.json()

      setStats(statsData)
      setServices(servicesData.services || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [periodHours])

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchData} className="mt-4">
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
        <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Total Requests</p>
            </div>
            <p className="text-3xl font-bold mt-2">
              {stats?.total_requests.toLocaleString() || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <p className="text-sm text-muted-foreground">Success Rate</p>
            </div>
            <p className="text-3xl font-bold mt-2 text-green-500">
              {stats?.success_rate || 0}%
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
              {((stats?.client_error_count || 0) + (stats?.server_error_count || 0)).toLocaleString()}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Avg Latency</p>
            </div>
            <p className="text-3xl font-bold mt-2">
              {stats?.avg_latency_ms?.toFixed(0) || 0}ms
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Latency Percentiles */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Latency Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="text-center p-4 bg-muted rounded-md">
              <p className="text-sm text-muted-foreground">P50 (Median)</p>
              <p className="text-2xl font-semibold">{stats?.p50_latency_ms?.toFixed(0) || 0}ms</p>
            </div>
            <div className="text-center p-4 bg-muted rounded-md">
              <p className="text-sm text-muted-foreground">P95</p>
              <p className="text-2xl font-semibold">{stats?.p95_latency_ms?.toFixed(0) || 0}ms</p>
            </div>
            <div className="text-center p-4 bg-muted rounded-md">
              <p className="text-sm text-muted-foreground">P99</p>
              <p className="text-2xl font-semibold">{stats?.p99_latency_ms?.toFixed(0) || 0}ms</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Services */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Traffic by Service</CardTitle>
        </CardHeader>
        <CardContent>
          {services.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No traffic data available for this period.
            </p>
          ) : (
            <div className="space-y-3">
              {services.map((svc) => (
                <div
                  key={svc.service}
                  className="flex items-center justify-between p-3 bg-muted rounded-md"
                >
                  <div>
                    <p className="font-medium">{svc.service}</p>
                    <p className="text-xs text-muted-foreground">
                      {svc.request_count.toLocaleString()} requests - {svc.avg_latency_ms.toFixed(0)}ms avg
                    </p>
                  </div>
                  <div className="text-right">
                    {svc.error_count > 0 ? (
                      <span className="text-red-500 text-sm">{svc.error_count} errors</span>
                    ) : (
                      <span className="text-green-500 text-sm">No errors</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'
import { Card } from '../../design-system/components'

interface MetricsResponse {
  total_traces: number
  total_observations: number
  total_generations: number
  daily_traces: Array<{ date: string; count: number }>
}

async function fetchMetrics(): Promise<MetricsResponse> {
  const res = await fetch('/api/v1/observability/metrics')
  if (!res.ok) throw new Error('Failed to fetch metrics')
  return res.json()
}

export function MetricsView() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['observability', 'metrics'],
    queryFn: fetchMetrics,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  if (isLoading) {
    return <div className="text-muted-foreground">Loading metrics...</div>
  }

  if (error) {
    return (
      <Card className="p-4 border-destructive">
        <p className="text-destructive">Failed to load metrics: {(error as Error).message}</p>
      </Card>
    )
  }

  const metrics = data || {
    total_traces: 0,
    total_observations: 0,
    total_generations: 0,
    daily_traces: [],
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-6">
          <h3 className="text-sm font-medium text-muted-foreground">Total Traces</h3>
          <p className="text-3xl font-bold mt-2">{metrics.total_traces.toLocaleString()}</p>
        </Card>
        <Card className="p-6">
          <h3 className="text-sm font-medium text-muted-foreground">Total Observations</h3>
          <p className="text-3xl font-bold mt-2">{metrics.total_observations.toLocaleString()}</p>
        </Card>
        <Card className="p-6">
          <h3 className="text-sm font-medium text-muted-foreground">Total Generations</h3>
          <p className="text-3xl font-bold mt-2">{metrics.total_generations.toLocaleString()}</p>
        </Card>
      </div>

      {metrics.daily_traces.length > 0 && (
        <Card className="p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">Daily Traces</h3>
          <div className="space-y-2">
            {metrics.daily_traces.slice(0, 14).map((day) => (
              <div key={day.date} className="flex items-center gap-4">
                <span className="text-sm text-muted-foreground w-24">{day.date}</span>
                <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{
                      width: `${Math.min(
                        100,
                        (day.count / Math.max(...metrics.daily_traces.map((d) => d.count))) * 100
                      )}%`,
                    }}
                  />
                </div>
                <span className="text-sm font-medium w-16 text-right">
                  {day.count.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

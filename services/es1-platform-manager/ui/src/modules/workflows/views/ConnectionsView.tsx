import { useQuery } from '@tanstack/react-query'
import { Card, Badge } from '../../../design-system/components'

interface Connection {
  connection_id: string
  conn_type: string
  host: string | null
  port: number | null
  schema: string | null
  description: string | null
}

interface ConnectionsResponse {
  connections: Connection[]
  total_entries: number
}

async function fetchConnections(): Promise<ConnectionsResponse> {
  const res = await fetch('/api/v1/airflow/connections')
  if (!res.ok) throw new Error('Failed to fetch connections')
  return res.json()
}

export function ConnectionsView() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['airflow', 'connections'],
    queryFn: fetchConnections,
  })

  if (isLoading) {
    return <div className="text-muted-foreground">Loading connections...</div>
  }

  if (error) {
    return (
      <Card className="p-4 border-destructive">
        <p className="text-destructive">Failed to load connections: {(error as Error).message}</p>
      </Card>
    )
  }

  const connections = data?.connections || []

  if (connections.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-muted-foreground">No connections found</p>
        <p className="text-sm text-muted-foreground mt-1">
          Connections are configured in Airflow.
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {connections.length} connection{connections.length !== 1 ? 's' : ''} configured
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {connections.map((conn) => (
          <Card key={conn.connection_id} className="p-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">{conn.connection_id}</h3>
                <Badge variant="secondary">{conn.conn_type}</Badge>
              </div>
              {conn.description && (
                <p className="text-sm text-muted-foreground">{conn.description}</p>
              )}
              <div className="text-xs text-muted-foreground space-y-1">
                {conn.host && (
                  <p>
                    <span className="font-medium">Host:</span> {conn.host}
                    {conn.port && `:${conn.port}`}
                  </p>
                )}
                {conn.schema && (
                  <p>
                    <span className="font-medium">Schema:</span> {conn.schema}
                  </p>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

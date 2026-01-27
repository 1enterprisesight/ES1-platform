import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, Box, Brain, Server, HardDrive } from 'lucide-react'

interface OllamaModel {
  name: string
  type: string
  source: string
  size_gb: number
  modified_at: string
  family: string | null
  parameter_size: string | null
  quantization: string | null
}

interface MLflowModel {
  name: string
  type: string
  source: string
  description: string | null
  latest_version: string | null
  stage: string | null
  created_at: number | null
  updated_at: number | null
}

interface ModelInventory {
  ollama: {
    status: string
    models: OllamaModel[]
    error: string | null
  }
  mlflow: {
    status: string
    models: MLflowModel[]
    error: string | null
  }
  total_models: number
  timestamp: string
}

export function InventoryView() {
  const [inventory, setInventory] = useState<ModelInventory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchInventory = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:8000/api/v1/models/inventory')
      if (!response.ok) throw new Error('Failed to fetch model inventory')
      const data = await response.json()
      setInventory(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchInventory()
  }, [])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return <Badge variant="success">Healthy</Badge>
      case 'unhealthy':
        return <Badge variant="destructive">Unhealthy</Badge>
      default:
        return <Badge variant="secondary">Unavailable</Badge>
    }
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchInventory} className="mt-4">
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
          <p className="text-sm text-muted-foreground">
            {inventory?.total_models || 0} total models
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchInventory} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-purple-500" />
                <div>
                  <p className="text-sm font-medium">Ollama Models</p>
                  <p className="text-2xl font-bold">{inventory?.ollama.models.length || 0}</p>
                </div>
              </div>
              {inventory && getStatusBadge(inventory.ollama.status)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Box className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="text-sm font-medium">MLflow Models</p>
                  <p className="text-2xl font-bold">{inventory?.mlflow.models.length || 0}</p>
                </div>
              </div>
              {inventory && getStatusBadge(inventory.mlflow.status)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <HardDrive className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Total Storage</p>
                <p className="text-2xl font-bold">
                  {inventory?.ollama.models.reduce((sum, m) => sum + m.size_gb, 0).toFixed(1) || 0} GB
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Ollama Models */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Brain className="h-4 w-4 text-purple-500" />
            Ollama LLM Models
          </CardTitle>
        </CardHeader>
        <CardContent>
          {inventory?.ollama.error ? (
            <p className="text-sm text-destructive">{inventory.ollama.error}</p>
          ) : inventory?.ollama.models.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No Ollama models found. Pull a model using the Ollama tab.
            </p>
          ) : (
            <div className="space-y-2">
              {inventory?.ollama.models.map((model) => (
                <div
                  key={model.name}
                  className="flex items-center justify-between p-3 bg-muted rounded-md"
                >
                  <div className="flex items-center gap-3">
                    <Server className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{model.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {model.family} {model.parameter_size && `• ${model.parameter_size}`}
                        {model.quantization && ` • ${model.quantization}`}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{model.size_gb} GB</p>
                    <Badge variant="secondary" className="text-xs">LLM</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* MLflow Models */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Box className="h-4 w-4 text-blue-500" />
            MLflow Registered Models
          </CardTitle>
        </CardHeader>
        <CardContent>
          {inventory?.mlflow.error ? (
            <p className="text-sm text-destructive">{inventory.mlflow.error}</p>
          ) : inventory?.mlflow.models.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No MLflow models registered yet.
            </p>
          ) : (
            <div className="space-y-2">
              {inventory?.mlflow.models.map((model) => (
                <div
                  key={model.name}
                  className="flex items-center justify-between p-3 bg-muted rounded-md"
                >
                  <div className="flex items-center gap-3">
                    <Box className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{model.name}</p>
                      {model.description && (
                        <p className="text-xs text-muted-foreground truncate max-w-md">
                          {model.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="text-right flex items-center gap-2">
                    {model.latest_version && (
                      <span className="text-xs text-muted-foreground">v{model.latest_version}</span>
                    )}
                    {model.stage && (
                      <Badge
                        variant={model.stage === 'Production' ? 'success' : 'secondary'}
                        className="text-xs"
                      >
                        {model.stage}
                      </Badge>
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

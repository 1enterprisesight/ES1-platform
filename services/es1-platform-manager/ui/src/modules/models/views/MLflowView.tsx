import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, Box, FlaskConical, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react'
import { apiUrl, serviceUrl } from '@/config'

interface ModelVersion {
  version: string
  current_stage: string
  creation_timestamp: number
  last_updated_timestamp: number
  run_id: string
  status: string
}

interface RegisteredModel {
  name: string
  creation_timestamp: number
  last_updated_timestamp: number
  description: string | null
  latest_versions: ModelVersion[]
  tags: Record<string, string>
}

interface Experiment {
  experiment_id: string
  name: string
  artifact_location: string
  lifecycle_stage: string
  creation_time: number
  last_update_time: number
  tags: Record<string, string>
}

export function MLflowView() {
  const [models, setModels] = useState<RegisteredModel[]>([])
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedModel, setExpandedModel] = useState<string | null>(null)
  const [tab, setTab] = useState<'models' | 'experiments'>('models')

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [modelsRes, expRes] = await Promise.all([
        fetch(apiUrl('mlflow/models')),
        fetch(apiUrl('mlflow/experiments')),
      ])
      if (!modelsRes.ok) throw new Error('Failed to fetch MLflow models')
      if (!expRes.ok) throw new Error('Failed to fetch MLflow experiments')
      const modelsData = await modelsRes.json()
      const expData = await expRes.json()
      setModels(modelsData.models || [])
      setExperiments(expData.experiments || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const getStageBadge = (stage: string) => {
    switch (stage) {
      case 'Production':
        return <Badge variant="success">{stage}</Badge>
      case 'Staging':
        return <Badge variant="warning">{stage}</Badge>
      case 'Archived':
        return <Badge variant="secondary">{stage}</Badge>
      default:
        return <Badge variant="outline">{stage || 'None'}</Badge>
    }
  }

  const formatTimestamp = (ts: number) => {
    if (!ts) return 'Unknown'
    return new Date(ts).toLocaleDateString()
  }

  const mlflowUrl = serviceUrl('mlflow')

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
          <div className="flex gap-2">
            <Button
              variant={tab === 'models' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTab('models')}
            >
              <Box className="h-4 w-4 mr-2" />
              Models ({models.length})
            </Button>
            <Button
              variant={tab === 'experiments' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTab('experiments')}
            >
              <FlaskConical className="h-4 w-4 mr-2" />
              Experiments ({experiments.length})
            </Button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={mlflowUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
          >
            <ExternalLink className="h-3 w-3" />
            Open MLflow UI
          </a>
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Models Tab */}
      {tab === 'models' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Registered Models</CardTitle>
          </CardHeader>
          <CardContent>
            {models.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No models registered in MLflow Model Registry.
              </p>
            ) : (
              <div className="space-y-2">
                {models.map((model) => (
                  <div key={model.name} className="border rounded-md overflow-hidden">
                    <div
                      className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => setExpandedModel(expandedModel === model.name ? null : model.name)}
                    >
                      <div className="flex items-center gap-3">
                        {expandedModel === model.name ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                        <Box className="h-4 w-4 text-blue-500" />
                        <div>
                          <p className="font-medium">{model.name}</p>
                          {model.description && (
                            <p className="text-xs text-muted-foreground truncate max-w-md">
                              {model.description}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {model.latest_versions.length > 0 && (
                          <>
                            <span className="text-xs text-muted-foreground">
                              v{model.latest_versions[0].version}
                            </span>
                            {getStageBadge(model.latest_versions[0].current_stage)}
                          </>
                        )}
                      </div>
                    </div>

                    {expandedModel === model.name && (
                      <div className="px-4 pb-4 border-t bg-muted/30">
                        <div className="pt-4 space-y-4">
                          <div className="grid gap-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Created:</span>
                              <span>{formatTimestamp(model.creation_timestamp)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Last Updated:</span>
                              <span>{formatTimestamp(model.last_updated_timestamp)}</span>
                            </div>
                          </div>

                          {model.latest_versions.length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2">Versions</p>
                              <div className="space-y-2">
                                {model.latest_versions.map((v) => (
                                  <div
                                    key={v.version}
                                    className="flex items-center justify-between p-2 bg-background rounded"
                                  >
                                    <div className="flex items-center gap-2">
                                      <span className="font-mono text-sm">v{v.version}</span>
                                      {getStageBadge(v.current_stage)}
                                    </div>
                                    <span className="text-xs text-muted-foreground">
                                      {formatTimestamp(v.creation_timestamp)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {Object.keys(model.tags).length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2">Tags</p>
                              <div className="flex flex-wrap gap-1">
                                {Object.entries(model.tags).map(([key, value]) => (
                                  <Badge key={key} variant="outline" className="text-xs">
                                    {key}: {value}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Experiments Tab */}
      {tab === 'experiments' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Experiments</CardTitle>
          </CardHeader>
          <CardContent>
            {experiments.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No experiments found in MLflow.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 px-3 font-medium">Name</th>
                      <th className="text-left py-2 px-3 font-medium">ID</th>
                      <th className="text-left py-2 px-3 font-medium">Status</th>
                      <th className="text-left py-2 px-3 font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {experiments.map((exp) => (
                      <tr key={exp.experiment_id} className="border-b hover:bg-muted/50">
                        <td className="py-2 px-3">
                          <div className="flex items-center gap-2">
                            <FlaskConical className="h-4 w-4 text-muted-foreground" />
                            {exp.name}
                          </div>
                        </td>
                        <td className="py-2 px-3 font-mono text-xs">{exp.experiment_id}</td>
                        <td className="py-2 px-3">
                          <Badge
                            variant={exp.lifecycle_stage === 'active' ? 'success' : 'secondary'}
                          >
                            {exp.lifecycle_stage}
                          </Badge>
                        </td>
                        <td className="py-2 px-3 text-muted-foreground">
                          {formatTimestamp(exp.creation_time)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

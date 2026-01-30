import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, Download, Trash2, Play, ChevronDown, ChevronRight, Server } from 'lucide-react'
import { apiUrl } from '@/config'

interface OllamaModel {
  name: string
  model: string
  modified_at: string
  size: number
  size_gb: number
  digest: string
  details: {
    family?: string
    parameter_size?: string
    quantization_level?: string
  }
}

interface RunningModel {
  name: string
  size_gb: number
  vram_gb: number | null
  expires_at: string
  details: Record<string, unknown>
}

export function OllamaView() {
  const [models, setModels] = useState<OllamaModel[]>([])
  const [running, setRunning] = useState<RunningModel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedModel, setExpandedModel] = useState<string | null>(null)
  const [pullModel, setPullModel] = useState('')
  const [pulling, setPulling] = useState(false)

  const fetchModels = async () => {
    setLoading(true)
    setError(null)
    try {
      const [modelsRes, runningRes] = await Promise.all([
        fetch(apiUrl('ollama/models')),
        fetch(apiUrl('ollama/ps')),
      ])
      if (!modelsRes.ok) throw new Error('Failed to fetch models')
      const modelsData = await modelsRes.json()
      const runningData = await runningRes.json()
      setModels(modelsData.models || [])
      setRunning(runningData.running_models || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchModels()
  }, [])

  const handlePullModel = async () => {
    if (!pullModel.trim()) return
    setPulling(true)
    try {
      const response = await fetch(apiUrl('ollama/models/pull'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: pullModel.trim() }),
      })
      if (!response.ok) throw new Error('Failed to pull model')
      setPullModel('')
      await fetchModels()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pull model')
    } finally {
      setPulling(false)
    }
  }

  const handleDeleteModel = async (name: string) => {
    if (!confirm(`Delete model "${name}"?`)) return
    try {
      const response = await fetch(apiUrl(`ollama/models/${encodeURIComponent(name)}`), {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete model')
      await fetchModels()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete model')
    }
  }

  const isRunning = (name: string) => running.some((r) => r.name === name)

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchModels} className="mt-4">
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
        <p className="text-sm text-muted-foreground">
          {models.length} model{models.length !== 1 ? 's' : ''} • {running.length} running
        </p>
        <Button variant="outline" size="sm" onClick={fetchModels} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Pull Model */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pull Model</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Model name (e.g., llama3.2, mistral, codellama)"
              value={pullModel}
              onChange={(e) => setPullModel(e.target.value)}
              className="flex-1 px-3 py-2 border rounded-md bg-background text-sm"
              onKeyDown={(e) => e.key === 'Enter' && handlePullModel()}
            />
            <Button onClick={handlePullModel} disabled={pulling || !pullModel.trim()}>
              <Download className={`h-4 w-4 mr-2 ${pulling ? 'animate-pulse' : ''}`} />
              {pulling ? 'Pulling...' : 'Pull'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Browse available models at{' '}
            <a href="https://ollama.com/library" target="_blank" rel="noopener noreferrer" className="underline">
              ollama.com/library
            </a>
          </p>
        </CardContent>
      </Card>

      {/* Running Models */}
      {running.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Play className="h-4 w-4 text-green-500" />
              Running Models
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {running.map((model) => (
                <div
                  key={model.name}
                  className="flex items-center justify-between p-3 bg-green-500/10 border border-green-500/20 rounded-md"
                >
                  <div className="flex items-center gap-3">
                    <Server className="h-4 w-4 text-green-500" />
                    <div>
                      <p className="font-medium">{model.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {model.size_gb} GB {model.vram_gb && `• ${model.vram_gb} GB VRAM`}
                      </p>
                    </div>
                  </div>
                  <Badge variant="success">Active</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* All Models */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Available Models</CardTitle>
        </CardHeader>
        <CardContent>
          {models.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No models installed. Pull a model to get started.
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
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{model.name}</p>
                          {isRunning(model.name) && (
                            <Badge variant="success" className="text-xs">Running</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {model.details.family} {model.details.parameter_size && `• ${model.details.parameter_size}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm">{model.size_gb} GB</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteModel(model.name)
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>

                  {expandedModel === model.name && (
                    <div className="px-4 pb-4 border-t bg-muted/30">
                      <div className="pt-4 grid gap-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Family:</span>
                          <span>{model.details.family || 'Unknown'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Parameters:</span>
                          <span>{model.details.parameter_size || 'Unknown'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Quantization:</span>
                          <span>{model.details.quantization_level || 'None'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Modified:</span>
                          <span>{new Date(model.modified_at).toLocaleDateString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Digest:</span>
                          <span className="font-mono text-xs">{model.digest?.slice(0, 12)}...</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

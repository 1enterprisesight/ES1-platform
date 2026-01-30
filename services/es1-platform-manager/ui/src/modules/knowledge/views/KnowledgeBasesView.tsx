import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { Input } from '@/design-system/components/Input'
import { RefreshCw, Plus, Database, FileText, Trash2, Play } from 'lucide-react'
import { apiUrl } from '@/config'

interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  embedding_model: string
  embedding_dimension: number
  chunking_strategy: string
  chunk_size: number
  chunk_overlap: number
  is_active: boolean
  document_count: number
  chunk_count: number
  entity_count: number
  created_at: string
  updated_at: string
}

interface KnowledgeBasesResponse {
  knowledge_bases: KnowledgeBase[]
  total: number
}

export function KnowledgeBasesView() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)

  // Create form state
  const [newKB, setNewKB] = useState({
    name: '',
    description: '',
    embedding_model: 'nomic-embed-text',
    chunking_strategy: 'recursive',
    chunk_size: 512,
    chunk_overlap: 50,
  })

  const fetchKnowledgeBases = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(apiUrl('knowledge/bases'))
      if (!response.ok) throw new Error('Failed to fetch knowledge bases')
      const data: KnowledgeBasesResponse = await response.json()
      setKnowledgeBases(data.knowledge_bases)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchKnowledgeBases()
  }, [])

  const createKnowledgeBase = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    try {
      const response = await fetch(apiUrl('knowledge/bases'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newKB),
      })
      if (!response.ok) throw new Error('Failed to create knowledge base')
      setShowCreateForm(false)
      setNewKB({
        name: '',
        description: '',
        embedding_model: 'nomic-embed-text',
        chunking_strategy: 'recursive',
        chunk_size: 512,
        chunk_overlap: 50,
      })
      fetchKnowledgeBases()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create knowledge base')
    }
  }

  const deleteKnowledgeBase = async (kbId: string) => {
    if (!confirm('Are you sure you want to delete this knowledge base? All documents and entities will be deleted.')) return
    try {
      const response = await fetch(apiUrl(`knowledge/bases/${kbId}`), {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete knowledge base')
      fetchKnowledgeBases()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete')
    }
  }

  const triggerIngestion = async (kbId: string) => {
    try {
      const response = await fetch(apiUrl(`knowledge/bases/${kbId}/ingest`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!response.ok) throw new Error('Failed to trigger ingestion')
      alert('Ingestion triggered successfully')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to trigger ingestion')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchKnowledgeBases} className="mt-4">
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
        <p className="text-muted-foreground">
          Manage knowledge bases for document storage and retrieval
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchKnowledgeBases} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowCreateForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Knowledge Base
          </Button>
        </div>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create Knowledge Base</CardTitle>
            <CardDescription>
              Create a new knowledge base for storing and querying documents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={createKnowledgeBase} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium">Name</label>
                  <Input
                    value={newKB.name}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewKB({ ...newKB, name: e.target.value })}
                    placeholder="My Knowledge Base"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Embedding Model</label>
                  <select
                    value={newKB.embedding_model}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setNewKB({ ...newKB, embedding_model: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm mt-1"
                  >
                    <option value="nomic-embed-text">nomic-embed-text (768d)</option>
                    <option value="mxbai-embed-large">mxbai-embed-large (1024d)</option>
                    <option value="all-minilm">all-minilm (384d)</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <Input
                  value={newKB.description}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewKB({ ...newKB, description: e.target.value })}
                  placeholder="A knowledge base for..."
                />
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="text-sm font-medium">Chunking Strategy</label>
                  <select
                    value={newKB.chunking_strategy}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setNewKB({ ...newKB, chunking_strategy: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm mt-1"
                  >
                    <option value="recursive">Recursive (Recommended)</option>
                    <option value="fixed">Fixed Size</option>
                    <option value="semantic">Semantic</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Chunk Size</label>
                  <Input
                    type="number"
                    value={newKB.chunk_size}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewKB({ ...newKB, chunk_size: parseInt(e.target.value) })}
                    min={100}
                    max={4096}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Chunk Overlap</label>
                  <Input
                    type="number"
                    value={newKB.chunk_overlap}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewKB({ ...newKB, chunk_overlap: parseInt(e.target.value) })}
                    min={0}
                    max={500}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit">Create Knowledge Base</Button>
                <Button type="button" variant="outline" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Knowledge Bases List */}
      {knowledgeBases.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No knowledge bases created yet.</p>
            <p className="text-sm text-muted-foreground mt-2">
              Create a knowledge base to start ingesting and querying documents.
            </p>
            <Button className="mt-4" onClick={() => setShowCreateForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Knowledge Base
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {knowledgeBases.map((kb) => (
            <Card key={kb.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    {kb.name}
                  </CardTitle>
                  <Badge variant={kb.is_active ? 'success' : 'secondary'}>
                    {kb.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                <CardDescription>{kb.description || 'No description'}</CardDescription>
              </CardHeader>
              <CardContent>
                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center p-2 bg-muted rounded-md">
                    <p className="text-2xl font-semibold">{kb.document_count}</p>
                    <p className="text-xs text-muted-foreground">Documents</p>
                  </div>
                  <div className="text-center p-2 bg-muted rounded-md">
                    <p className="text-2xl font-semibold">{kb.chunk_count}</p>
                    <p className="text-xs text-muted-foreground">Chunks</p>
                  </div>
                  <div className="text-center p-2 bg-muted rounded-md">
                    <p className="text-2xl font-semibold">{kb.entity_count}</p>
                    <p className="text-xs text-muted-foreground">Entities</p>
                  </div>
                </div>

                {/* Config */}
                <div className="space-y-1 text-xs text-muted-foreground mb-4">
                  <p>
                    <span className="font-medium">Model:</span> {kb.embedding_model} ({kb.embedding_dimension}d)
                  </p>
                  <p>
                    <span className="font-medium">Chunking:</span> {kb.chunking_strategy} ({kb.chunk_size} chars, {kb.chunk_overlap} overlap)
                  </p>
                  <p>
                    <span className="font-medium">Created:</span> {formatDate(kb.created_at)}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => triggerIngestion(kb.id)}
                  >
                    <Play className="h-4 w-4 mr-1" />
                    Ingest
                  </Button>
                  <Button variant="outline" size="sm" disabled>
                    <FileText className="h-4 w-4 mr-1" />
                    Sources
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteKnowledgeBase(kb.id)}
                    className="text-destructive hover:text-destructive ml-auto"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

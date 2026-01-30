import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, FileText, ChevronDown, ChevronRight, Trash2 } from 'lucide-react'
import { apiUrl } from '@/config'

interface KnowledgeBase {
  id: string
  name: string
}

interface Document {
  id: string
  knowledge_base_id: string
  source_id: string | null
  title: string
  content_type: string
  status: string
  chunk_count: number
  created_at: string
}

interface Chunk {
  id: string
  chunk_index: number
  content: string
  has_embedding: boolean
}

export function DocumentsView() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [selectedKB, setSelectedKB] = useState<string>('')
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null)
  const [chunks, setChunks] = useState<Chunk[]>([])
  const [loadingChunks, setLoadingChunks] = useState(false)

  // Fetch knowledge bases
  useEffect(() => {
    const fetchKBs = async () => {
      try {
        const response = await fetch(apiUrl('knowledge/bases'))
        if (!response.ok) throw new Error('Failed to fetch knowledge bases')
        const data = await response.json()
        setKnowledgeBases(data.knowledge_bases)
        if (data.knowledge_bases.length > 0) {
          setSelectedKB(data.knowledge_bases[0].id)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchKBs()
  }, [])

  // Fetch documents when KB changes
  useEffect(() => {
    if (!selectedKB) return

    const fetchDocs = async () => {
      setLoading(true)
      try {
        const response = await fetch(apiUrl(`knowledge/bases/${selectedKB}/documents`))
        if (!response.ok) throw new Error('Failed to fetch documents')
        const data = await response.json()
        setDocuments(data.documents)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchDocs()
  }, [selectedKB])

  const toggleDocument = async (docId: string) => {
    if (expandedDoc === docId) {
      setExpandedDoc(null)
      setChunks([])
      return
    }

    setExpandedDoc(docId)
    setLoadingChunks(true)
    try {
      const response = await fetch(apiUrl(`knowledge/documents/${docId}?include_chunks=true`))
      if (!response.ok) throw new Error('Failed to fetch document')
      const data = await response.json()
      setChunks(data.chunks || [])
    } catch (err) {
      console.error('Failed to fetch chunks:', err)
    } finally {
      setLoadingChunks(false)
    }
  }

  const deleteDocument = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return
    try {
      const response = await fetch(apiUrl(`knowledge/documents/${docId}`), {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete document')
      setDocuments(documents.filter((d) => d.id !== docId))
      if (expandedDoc === docId) {
        setExpandedDoc(null)
        setChunks([])
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete')
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
            <Button onClick={() => window.location.reload()} className="mt-4">
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
          <p className="text-muted-foreground">View documents and chunks</p>
          <select
            value={selectedKB}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedKB(e.target.value)}
            className="px-3 py-2 border rounded-md bg-background text-sm"
          >
            {knowledgeBases.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </div>
        <Button variant="outline" size="sm" onClick={() => window.location.reload()} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Documents List */}
      {documents.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No documents in this knowledge base.</p>
            <p className="text-sm text-muted-foreground mt-2">
              Add sources and trigger ingestion to populate documents.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <Card key={doc.id} className="overflow-hidden">
              <div
                className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => toggleDocument(doc.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {expandedDoc === doc.id ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{doc.title || 'Untitled'}</p>
                      <p className="text-xs text-muted-foreground">
                        {doc.chunk_count} chunks - {formatDate(doc.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{doc.content_type || 'text'}</Badge>
                    <Badge variant={doc.status === 'active' ? 'success' : 'secondary'}>
                      {doc.status}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation()
                        deleteDocument(doc.id)
                      }}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              {expandedDoc === doc.id && (
                <div className="px-4 pb-4 border-t bg-muted/30">
                  <div className="pt-4">
                    <p className="text-sm font-medium mb-2">Chunks ({chunks.length})</p>
                    {loadingChunks ? (
                      <p className="text-sm text-muted-foreground">Loading chunks...</p>
                    ) : chunks.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No chunks available</p>
                    ) : (
                      <div className="space-y-2 max-h-80 overflow-auto">
                        {chunks.map((chunk) => (
                          <div
                            key={chunk.id}
                            className="p-3 bg-background border rounded-md text-sm"
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-muted-foreground">
                                Chunk #{chunk.chunk_index + 1}
                              </span>
                              <Badge variant={chunk.has_embedding ? 'success' : 'secondary'} className="text-xs">
                                {chunk.has_embedding ? 'Embedded' : 'No Embedding'}
                              </Badge>
                            </div>
                            <p className="whitespace-pre-wrap text-xs">
                              {chunk.content.length > 500
                                ? chunk.content.substring(0, 500) + '...'
                                : chunk.content}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
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

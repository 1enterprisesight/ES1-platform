import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { Input } from '@/design-system/components/Input'
import { Search, FileText, Loader2 } from 'lucide-react'
import { apiUrl } from '@/config'

interface KnowledgeBase {
  id: string
  name: string
}

interface SearchResult {
  chunk_id: string
  document_id: string
  document_title: string
  content: string
  score: number
  metadata: Record<string, unknown>
  knowledge_base_id: string
  knowledge_base_name: string
}

export function SearchView() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [selectedKB, setSelectedKB] = useState<string>('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch knowledge bases
  useEffect(() => {
    const fetchKBs = async () => {
      try {
        const response = await fetch(apiUrl('knowledge/bases'))
        if (!response.ok) throw new Error('Failed to fetch knowledge bases')
        const data = await response.json()
        setKnowledgeBases(data.knowledge_bases)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }
    fetchKBs()
  }, [])

  const performSearch = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setSearched(true)
    setError(null)
    try {
      const response = await fetch(apiUrl('knowledge/search'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          knowledge_base_id: selectedKB || undefined,
          limit: 20,
          min_score: 0.3,
          include_content: true,
          include_metadata: true,
        }),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.message || 'Search failed')
      }
      const data = await response.json()
      setResults(data.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-500'
    if (score >= 0.6) return 'text-yellow-500'
    return 'text-orange-500'
  }

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Semantic Search
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={performSearch} className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <Input
                  value={query}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
                  placeholder="Enter your search query..."
                  className="w-full"
                />
              </div>
              <select
                value={selectedKB}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedKB(e.target.value)}
                className="px-3 py-2 border rounded-md bg-background text-sm min-w-[200px]"
              >
                <option value="">All Knowledge Bases</option>
                {knowledgeBases.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))}
              </select>
              <Button type="submit" disabled={loading || !query.trim()}>
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Search
                  </>
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Search uses vector similarity to find relevant content. Try natural language queries.
            </p>
          </form>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <Card>
          <CardContent className="p-6">
            <div className="text-center text-destructive">
              <p>Error: {error}</p>
              <p className="text-sm text-muted-foreground mt-2">
                Make sure Ollama is running and has the embedding model available.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {searched && !error && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {results.length} result{results.length !== 1 ? 's' : ''} for "{query}"
            </p>
          </div>

          {results.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No results found.</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Try a different query or make sure documents have been ingested and embedded.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {results.map((result, index) => (
                <Card key={result.chunk_id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{result.document_title || 'Untitled'}</span>
                        <Badge variant="outline" className="text-xs">
                          {result.knowledge_base_name}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">#{index + 1}</span>
                        <span className={`text-sm font-medium ${getScoreColor(result.score)}`}>
                          {(result.score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <div className="bg-muted p-3 rounded-md">
                      <p className="text-sm whitespace-pre-wrap">
                        {result.content.length > 800
                          ? result.content.substring(0, 800) + '...'
                          : result.content}
                      </p>
                    </div>
                    {result.metadata && Object.keys(result.metadata).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {Object.entries(result.metadata).map(([key, value]) => (
                          <Badge key={key} variant="secondary" className="text-xs">
                            {key}: {String(value)}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Help */}
      {!searched && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">How Semantic Search Works</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>
              Semantic search finds content based on meaning rather than exact keyword matches.
              Your query is converted to a vector embedding and compared against document chunks.
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Use natural language - "How do I configure authentication?"</li>
              <li>Ask questions - "What are the main components of the system?"</li>
              <li>Describe concepts - "Error handling best practices"</li>
            </ul>
            <p className="pt-2">
              Results are ranked by similarity score. Higher scores indicate better matches.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

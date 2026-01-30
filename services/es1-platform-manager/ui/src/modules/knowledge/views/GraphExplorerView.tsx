import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, Network, Circle } from 'lucide-react'
import { apiUrl } from '@/config'

interface KnowledgeBase {
  id: string
  name: string
}

interface Entity {
  id: string
  entity_type: string
  name: string
  canonical_name: string | null
  description: string | null
  confidence: number
  mention_count: number
}

interface Relationship {
  id: string
  source_entity_id: string
  target_entity_id: string
  relationship_type: string
  source_entity_name: string
  target_entity_name: string
}

interface GraphNode {
  id: string
  label: string
  type: string
  properties: Record<string, unknown>
}

interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
  properties: Record<string, unknown>
}

export function GraphExplorerView() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [selectedKB, setSelectedKB] = useState<string>('')
  const [entities, setEntities] = useState<Entity[]>([])
  const [relationships, setRelationships] = useState<Relationship[]>([])
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null)
  const [entityFilter, setEntityFilter] = useState<string>('')

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

  // Fetch entities and graph when KB changes
  useEffect(() => {
    if (!selectedKB) return

    const fetchData = async () => {
      setLoading(true)
      try {
        // Fetch entities
        const entitiesResponse = await fetch(
          apiUrl(`knowledge/bases/${selectedKB}/entities?limit=100`)
        )
        if (!entitiesResponse.ok) throw new Error('Failed to fetch entities')
        const entitiesData = await entitiesResponse.json()
        setEntities(entitiesData.entities)

        // Fetch relationships
        const relsResponse = await fetch(
          apiUrl(`knowledge/bases/${selectedKB}/relationships?limit=100`)
        )
        if (!relsResponse.ok) throw new Error('Failed to fetch relationships')
        const relsData = await relsResponse.json()
        setRelationships(relsData.relationships)

        // Fetch graph visualization data
        const graphResponse = await fetch(apiUrl('knowledge/graph'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            knowledge_base_id: selectedKB,
            depth: 2,
            limit: 50,
          }),
        })
        if (graphResponse.ok) {
          const graphResult = await graphResponse.json()
          setGraphData(graphResult)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [selectedKB])

  const getEntityTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'person':
        return 'bg-blue-500'
      case 'organization':
        return 'bg-purple-500'
      case 'location':
        return 'bg-green-500'
      case 'concept':
        return 'bg-yellow-500'
      case 'technology':
        return 'bg-orange-500'
      default:
        return 'bg-gray-500'
    }
  }

  const filteredEntities = entities.filter(
    (e) =>
      entityFilter === '' ||
      e.entity_type.toLowerCase() === entityFilter.toLowerCase()
  )

  const entityTypes = [...new Set(entities.map((e) => e.entity_type))]

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
          <p className="text-muted-foreground">Explore entities and relationships</p>
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

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Total Entities</p>
            <p className="text-2xl font-semibold">{entities.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Relationships</p>
            <p className="text-2xl font-semibold">{relationships.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Entity Types</p>
            <p className="text-2xl font-semibold">{entityTypes.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Graph Nodes</p>
            <p className="text-2xl font-semibold">{graphData.nodes.length}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Entity Types Legend */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Network className="h-4 w-4" />
              Entity Types
            </CardTitle>
          </CardHeader>
          <CardContent>
            {entityTypes.length === 0 ? (
              <p className="text-sm text-muted-foreground">No entities found</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Badge
                  variant={entityFilter === '' ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => setEntityFilter('')}
                >
                  All ({entities.length})
                </Badge>
                {entityTypes.map((type) => (
                  <Badge
                    key={type}
                    variant={entityFilter === type ? 'default' : 'outline'}
                    className="cursor-pointer flex items-center gap-1"
                    onClick={() => setEntityFilter(type)}
                  >
                    <div className={`w-2 h-2 rounded-full ${getEntityTypeColor(type)}`} />
                    {type} ({entities.filter((e) => e.entity_type === type).length})
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Graph Visualization Placeholder */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Graph Visualization</CardTitle>
          </CardHeader>
          <CardContent>
            {graphData.nodes.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-muted-foreground">
                <p>No graph data available</p>
              </div>
            ) : (
              <div className="h-48 bg-muted rounded-md flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Network className="h-8 w-8 mx-auto mb-2" />
                  <p className="text-sm">{graphData.nodes.length} nodes, {graphData.edges.length} edges</p>
                  <p className="text-xs mt-1">Interactive visualization coming soon</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Entities List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Entities</CardTitle>
        </CardHeader>
        <CardContent>
          {filteredEntities.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No entities found. Ingest documents to extract entities.
            </p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-auto">
              {filteredEntities.map((entity) => (
                <div
                  key={entity.id}
                  className={`p-3 border rounded-md cursor-pointer transition-colors ${
                    selectedEntity?.id === entity.id ? 'bg-muted border-primary' : 'hover:bg-muted/50'
                  }`}
                  onClick={() => setSelectedEntity(selectedEntity?.id === entity.id ? null : entity)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Circle className={`h-3 w-3 ${getEntityTypeColor(entity.entity_type)} rounded-full`} />
                      <span className="font-medium">{entity.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {entity.entity_type}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {(entity.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                  {selectedEntity?.id === entity.id && entity.description && (
                    <p className="text-sm text-muted-foreground mt-2">{entity.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Relationships */}
      {relationships.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Relationships</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-auto">
              {relationships.slice(0, 20).map((rel) => (
                <div key={rel.id} className="flex items-center gap-2 text-sm p-2 bg-muted rounded-md">
                  <span className="font-medium">{rel.source_entity_name}</span>
                  <span className="text-muted-foreground">-[{rel.relationship_type}]-&gt;</span>
                  <span className="font-medium">{rel.target_entity_name}</span>
                </div>
              ))}
              {relationships.length > 20 && (
                <p className="text-xs text-muted-foreground text-center">
                  And {relationships.length - 20} more relationships...
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

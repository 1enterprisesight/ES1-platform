import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { Input } from '@/design-system/components/Input'
import { RefreshCw, Search, Trash2 } from 'lucide-react'

interface Agent {
  key: string
  name: string
  framework: string
  description: string
  capabilities: string[]
  registered_at: string
  last_seen: string
}

interface AgentsResponse {
  agents: Agent[]
}

export function AgentsView() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterFramework, setFilterFramework] = useState<string>('')

  const fetchAgents = async () => {
    setLoading(true)
    setError(null)
    try {
      const url = filterFramework
        ? `http://localhost:8102/agents?framework=${filterFramework}`
        : 'http://localhost:8102/agents'
      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to fetch agents')
      const data: AgentsResponse = await response.json()
      setAgents(data.agents)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAgents()
  }, [filterFramework])

  const deleteAgent = async (agentKey: string) => {
    if (!confirm('Are you sure you want to unregister this agent?')) return

    try {
      const response = await fetch(`http://localhost:8102/agents/${agentKey}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete agent')
      fetchAgents()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete agent')
    }
  }

  const filteredAgents = agents.filter(
    (agent) =>
      agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getFrameworkColor = (framework: string) => {
    switch (framework) {
      case 'crewai':
        return 'bg-blue-500'
      case 'autogen':
        return 'bg-purple-500'
      case 'langflow':
        return 'bg-green-500'
      case 'n8n':
        return 'bg-orange-500'
      default:
        return 'bg-gray-500'
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
            <Button onClick={fetchAgents} className="mt-4">
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
      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={filterFramework}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilterFramework(e.target.value)}
          className="px-3 py-2 border rounded-md bg-background text-sm"
        >
          <option value="">All Frameworks</option>
          <option value="crewai">CrewAI</option>
          <option value="autogen">AutoGen</option>
          <option value="langflow">Langflow</option>
          <option value="n8n">n8n</option>
        </select>
        <Button variant="outline" size="sm" onClick={fetchAgents} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Agents List */}
      {filteredAgents.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">No agents registered yet.</p>
            <p className="text-sm text-muted-foreground mt-2">
              Agents are automatically registered when they connect to the router,
              or you can register them via the API.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredAgents.map((agent) => (
            <Card key={agent.key} className="relative overflow-hidden">
              <div className={`absolute top-0 left-0 w-1 h-full ${getFrameworkColor(agent.framework)}`} />
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-lg">{agent.name}</CardTitle>
                    <Badge variant="outline" className="capitalize">
                      {agent.framework}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteAgent(agent.key)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <CardDescription>{agent.description || 'No description'}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-medium mb-2">Capabilities</p>
                    <div className="flex flex-wrap gap-1">
                      {agent.capabilities && agent.capabilities.length > 0 ? (
                        agent.capabilities.map((cap, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            {cap}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">No capabilities defined</span>
                      )}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Registered:</span> {formatDate(agent.registered_at)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Last seen:</span> {formatDate(agent.last_seen)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Key:</span> {agent.key}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

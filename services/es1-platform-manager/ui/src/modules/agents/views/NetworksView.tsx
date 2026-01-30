import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { Input } from '@/design-system/components/Input'
import { RefreshCw, Plus, Network, ArrowRight } from 'lucide-react'
import { agentRouterUrl } from '@/config'

interface AgentRef {
  name: string
  framework: string
  role?: string
}

interface AgentNetwork {
  network_id: string
  name: string
  description: string
  agents: AgentRef[]
  connections: Array<{ from: string; to: string }>
  orchestration: string
}

interface NetworksResponse {
  networks: AgentNetwork[]
}

export function NetworksView() {
  const [networks, setNetworks] = useState<AgentNetwork[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)

  // Create form state
  const [newNetwork, setNewNetwork] = useState({
    name: '',
    description: '',
    orchestration: 'event_driven',
  })

  const fetchNetworks = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(agentRouterUrl('networks'))
      if (!response.ok) throw new Error('Failed to fetch networks')
      const data: NetworksResponse = await response.json()
      setNetworks(data.networks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNetworks()
  }, [])

  const createNetwork = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    try {
      const response = await fetch(agentRouterUrl('networks'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newNetwork.name,
          description: newNetwork.description,
          agents: [],
          connections: [],
          orchestration: newNetwork.orchestration,
        }),
      })
      if (!response.ok) throw new Error('Failed to create network')
      setShowCreateForm(false)
      setNewNetwork({ name: '', description: '', orchestration: 'event_driven' })
      fetchNetworks()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create network')
    }
  }

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

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchNetworks} className="mt-4">
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
          Define agent networks that span multiple frameworks
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchNetworks} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowCreateForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Network
          </Button>
        </div>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create Agent Network</CardTitle>
            <CardDescription>
              Define a network of agents that can collaborate across frameworks
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={createNetwork} className="space-y-4">
              <div>
                <label className="text-sm font-medium">Name</label>
                <Input
                  value={newNetwork.name}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewNetwork({ ...newNetwork, name: e.target.value })}
                  placeholder="My Agent Network"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <Input
                  value={newNetwork.description}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewNetwork({ ...newNetwork, description: e.target.value })}
                  placeholder="A network of agents for..."
                />
              </div>
              <div>
                <label className="text-sm font-medium">Orchestration</label>
                <select
                  value={newNetwork.orchestration}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setNewNetwork({ ...newNetwork, orchestration: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md bg-background text-sm mt-1"
                >
                  <option value="event_driven">Event Driven</option>
                  <option value="sequential">Sequential</option>
                  <option value="parallel">Parallel</option>
                </select>
              </div>
              <div className="flex gap-2">
                <Button type="submit">Create Network</Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Networks List */}
      {networks.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Network className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No agent networks defined yet.</p>
            <p className="text-sm text-muted-foreground mt-2">
              Create a network to connect agents across CrewAI, AutoGen, Langflow, and n8n.
            </p>
            <Button className="mt-4" onClick={() => setShowCreateForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Network
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {networks.map((network) => (
            <Card key={network.network_id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Network className="h-5 w-5" />
                    {network.name}
                  </CardTitle>
                  <Badge variant="outline" className="capitalize">
                    {network.orchestration.replace('_', ' ')}
                  </Badge>
                </div>
                <CardDescription>{network.description || 'No description'}</CardDescription>
              </CardHeader>
              <CardContent>
                {/* Agents in Network */}
                <div className="mb-4">
                  <p className="text-sm font-medium mb-2">Agents ({network.agents.length})</p>
                  {network.agents.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No agents added yet</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {network.agents.map((agent, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-1 px-2 py-1 bg-muted rounded-md"
                        >
                          <div
                            className={`w-2 h-2 rounded-full ${getFrameworkColor(agent.framework)}`}
                          />
                          <span className="text-xs">{agent.name}</span>
                          <span className="text-xs text-muted-foreground">
                            ({agent.framework})
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Connections */}
                {network.connections.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm font-medium mb-2">Connections</p>
                    <div className="space-y-1">
                      {network.connections.map((conn, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-xs">
                          <span>{conn.from}</span>
                          <ArrowRight className="h-3 w-3" />
                          <span>{conn.to}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t">
                  <Button variant="outline" size="sm" disabled>
                    Edit
                  </Button>
                  <Button variant="outline" size="sm" disabled>
                    Add Agent
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">About Agent Networks</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            Agent networks allow you to define collaborative groups of agents that span
            multiple frameworks. For example:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>A CrewAI research team that feeds results to an AutoGen debate</li>
            <li>A Langflow data pipeline that triggers n8n notifications</li>
            <li>Multiple agent teams that share context via the Agent Router</li>
          </ul>
          <p className="pt-2">
            Networks use Redis pub/sub for real-time messaging and the shared context
            store for persistent state.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

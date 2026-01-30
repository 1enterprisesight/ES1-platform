import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/design-system/components/Card'
import { Badge } from '@/design-system/components/Badge'
import { Button } from '@/design-system/components/Button'
import { RefreshCw, ExternalLink, Users, MessageSquare, Workflow, Bot } from 'lucide-react'
import { config, agentRouterUrl, serviceUrl, isFeatureEnabled } from '@/config'

interface Framework {
  name: string
  url: string
  status: 'healthy' | 'unhealthy' | 'unreachable'
  health: Record<string, unknown>
}

interface FrameworksResponse {
  frameworks: Framework[]
}

const FRAMEWORK_INFO: Record<string, {
  icon: typeof Bot
  description: string
  color: string
  serviceKey?: keyof ReturnType<typeof config>['services']
  studioKey?: keyof ReturnType<typeof config>['services']
}> = {
  crewai: {
    icon: Users,
    description: 'Role-based agent teams for complex tasks',
    color: 'bg-blue-500',
    serviceKey: 'crewai',
    studioKey: 'crewaiStudio',
  },
  autogen: {
    icon: MessageSquare,
    description: 'Multi-agent conversations and debates',
    color: 'bg-purple-500',
    serviceKey: 'autogen',
  },
  langflow: {
    icon: Workflow,
    description: 'Visual agent flow builder with LangChain',
    color: 'bg-green-500',
    serviceKey: 'langflow',
  },
  n8n: {
    icon: Workflow,
    description: 'Workflow automation with 400+ integrations',
    color: 'bg-orange-500',
    serviceKey: 'n8n',
  },
}

export function FrameworksView() {
  const navigate = useNavigate()
  const [frameworks, setFrameworks] = useState<Framework[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchFrameworks = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(agentRouterUrl('frameworks'))
      if (!response.ok) throw new Error('Failed to fetch frameworks')
      const data: FrameworksResponse = await response.json()
      setFrameworks(data.frameworks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFrameworks()
    const interval = setInterval(fetchFrameworks, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return <Badge variant="success">Healthy</Badge>
      case 'unhealthy':
        return <Badge variant="warning">Unhealthy</Badge>
      case 'unreachable':
        return <Badge variant="destructive">Unreachable</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  const openExternalUrl = (serviceKey: keyof ReturnType<typeof config>['services'], suffix?: string) => {
    const url = serviceUrl(serviceKey)
    window.open(suffix ? `${url}${suffix}` : url, '_blank')
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-destructive">
            <p>Error: {error}</p>
            <Button onClick={fetchFrameworks} className="mt-4">
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
      <div className="flex items-center justify-between">
        <p className="text-muted-foreground">
          Agent frameworks available for building and running AI agents
        </p>
        <Button variant="outline" size="sm" onClick={fetchFrameworks} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {frameworks.map((framework) => {
          const info = FRAMEWORK_INFO[framework.name] || {
            icon: Bot,
            description: 'Agent framework',
            color: 'bg-gray-500',
          }
          const Icon = info.icon
          const showStudio = info.studioKey && isFeatureEnabled('enableCrewaiStudio')

          return (
            <Card key={framework.name} className="relative overflow-hidden">
              <div className={`absolute top-0 left-0 w-1 h-full ${info.color}`} />
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${info.color} bg-opacity-10`}>
                      <Icon className={`h-5 w-5 ${info.color.replace('bg-', 'text-')}`} />
                    </div>
                    <div>
                      <CardTitle className="capitalize">{framework.name}</CardTitle>
                      <CardDescription className="text-xs mt-0.5">
                        {framework.url}
                      </CardDescription>
                    </div>
                  </div>
                  {getStatusBadge(framework.status)}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  {info.description}
                </p>
                <div className="flex gap-2">
                  {info.serviceKey && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openExternalUrl(info.serviceKey!, '/docs')}
                    >
                      <ExternalLink className="h-3 w-3 mr-1" />
                      API Docs
                    </Button>
                  )}
                  {showStudio && info.studioKey && (
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => openExternalUrl(info.studioKey!)}
                    >
                      <Workflow className="h-3 w-3 mr-1" />
                      Open Studio
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/agents/registry?framework=${framework.name}`)}
                    disabled={framework.status !== 'healthy'}
                  >
                    View Agents
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Agent Router Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Agent Router
          </CardTitle>
          <CardDescription>
            Unified API for managing agents across all frameworks
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium">API Endpoint</p>
              <p className="text-xs text-muted-foreground mt-1">{agentRouterUrl()}</p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium">WebSocket Events</p>
              <p className="text-xs text-muted-foreground mt-1">{agentRouterUrl('ws/events').replace('http', 'ws')}</p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium">Documentation</p>
              <Button
                variant="link"
                size="sm"
                className="p-0 h-auto text-xs"
                onClick={() => window.open(`${agentRouterUrl()}/docs`, '_blank')}
              >
                OpenAPI Docs
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

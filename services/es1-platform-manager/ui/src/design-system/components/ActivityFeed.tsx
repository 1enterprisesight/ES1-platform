import { useState } from 'react'
import {
  Activity,
  Rocket,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  Search,
  ChevronDown,
  ChevronRight,
  Trash2,
  Network,
  Workflow,
  Brain,
  Zap,
  Server,
  RefreshCw,
  Play,
  Pause,
} from 'lucide-react'
import { PlatformEvent } from '@/shared/contexts/EventBusContext'
import { cn } from '@/shared/utils/cn'
import { Button } from './Button'

interface ActivityFeedProps {
  events: PlatformEvent[]
  onClear?: () => void
}

type EventCategory = 'all' | 'operations' | 'deployments' | 'resources' | 'workflows' | 'ai' | 'system'

const categoryFilters: { value: EventCategory; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'operations', label: 'Operations' },
  { value: 'deployments', label: 'Deployments' },
  { value: 'resources', label: 'Resources' },
  { value: 'workflows', label: 'Workflows' },
  { value: 'ai', label: 'AI' },
  { value: 'system', label: 'System' },
]

const eventCategoryMap: Record<string, EventCategory> = {
  // Operations
  operation_started: 'operations',
  operation_progress: 'operations',
  operation_completed: 'operations',
  operation_failed: 'operations',
  // Deployments
  deployment_started: 'deployments',
  deployment_progress: 'deployments',
  deployment_completed: 'deployments',
  deployment_failed: 'deployments',
  deployment_rolled_back: 'deployments',
  // Resources
  resource_discovered: 'resources',
  resource_updated: 'resources',
  resource_deleted: 'resources',
  exposure_created: 'resources',
  exposure_approved: 'resources',
  exposure_rejected: 'resources',
  exposure_deployed: 'resources',
  // Workflows (n8n + Airflow)
  workflow_executed: 'workflows',
  workflow_activated: 'workflows',
  workflow_deactivated: 'workflows',
  workflow_execution_completed: 'workflows',
  workflow_execution_failed: 'workflows',
  dag_triggered: 'workflows',
  dag_paused: 'workflows',
  dag_unpaused: 'workflows',
  dag_discovered: 'workflows',
  dag_run_started: 'workflows',
  dag_run_completed: 'workflows',
  dag_run_failed: 'workflows',
  // AI (Langflow)
  flow_executed: 'ai',
  flow_created: 'ai',
  flow_updated: 'ai',
  // System
  health_status_changed: 'system',
  system_info: 'system',
  system_warning: 'system',
  system_error: 'system',
}

export function ActivityFeed({ events, onClear }: ActivityFeedProps) {
  const [filter, setFilter] = useState<EventCategory>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const filteredEvents = events.filter((event) => {
    // Category filter
    if (filter !== 'all') {
      const eventCategory = eventCategoryMap[event.type] || 'system'
      if (eventCategory !== filter) return false
    }

    // Search filter
    if (searchQuery) {
      const searchLower = searchQuery.toLowerCase()
      const matchesType = event.type.toLowerCase().includes(searchLower)
      const matchesMessage = event.data.message?.toString().toLowerCase().includes(searchLower)
      const matchesData = JSON.stringify(event.data).toLowerCase().includes(searchLower)
      if (!matchesType && !matchesMessage && !matchesData) return false
    }

    return true
  })

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            <h2 className="font-medium text-sm">Activity</h2>
            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {filteredEvents.length}
            </span>
          </div>
          {onClear && events.length > 0 && (
            <Button variant="ghost" size="sm" onClick={onClear} className="h-7 px-2">
              <Trash2 className="h-3 w-3" />
            </Button>
          )}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search events..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-7 pl-7 pr-2 text-xs rounded border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex gap-1 flex-wrap">
          {categoryFilters.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setFilter(cat.value)}
              className={cn(
                'px-2 py-0.5 text-xs rounded-full transition-colors',
                filter === cat.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80 text-muted-foreground'
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-auto">
        {filteredEvents.length === 0 ? (
          <div className="p-4 text-center">
            <Activity className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
            <p className="text-sm text-muted-foreground">
              {events.length === 0 ? 'No activity yet' : 'No matching events'}
            </p>
          </div>
        ) : (
          <div className="divide-y">
            {filteredEvents.slice(0, 50).map((event) => (
              <ActivityItem
                key={event.id}
                event={event}
                isExpanded={expandedIds.has(event.id)}
                onToggle={() => toggleExpanded(event.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface ActivityItemProps {
  event: PlatformEvent
  isExpanded: boolean
  onToggle: () => void
}

function ActivityItem({ event, isExpanded, onToggle }: ActivityItemProps) {
  const config = getEventConfig(event.type)
  const Icon = config.icon
  const hasDetails = Object.keys(event.data).length > (event.data.message ? 1 : 0)

  return (
    <div
      className={cn(
        'transition-colors',
        config.bgClass,
        hasDetails && 'cursor-pointer'
      )}
      onClick={hasDetails ? onToggle : undefined}
    >
      <div className="p-3">
        <div className="flex items-start gap-2">
          {/* Icon */}
          <div className={cn('mt-0.5 p-1 rounded', config.iconBgClass)}>
            <Icon className={cn('h-3 w-3', config.iconClass)} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className={cn('text-xs font-medium', config.textClass)}>
                {config.label}
              </span>
              <span className="text-xs text-muted-foreground flex-shrink-0">
                {formatRelativeTime(event.timestamp)}
              </span>
            </div>

            {/* Message */}
            {event.data.message ? (
              <p className={cn('text-sm mt-0.5', isExpanded ? '' : 'line-clamp-2')}>
                {String(event.data.message)}
              </p>
            ) : null}

            {/* Error */}
            {event.data.error ? (
              <p className="text-xs text-red-500 mt-1 font-mono bg-red-500/10 px-1.5 py-0.5 rounded">
                {String(event.data.error)}
              </p>
            ) : null}

            {/* Expand indicator */}
            {hasDetails && (
              <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                {isExpanded ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
                <span>{isExpanded ? 'Hide details' : 'Show details'}</span>
              </div>
            )}
          </div>
        </div>

        {/* Expanded Details */}
        {isExpanded && hasDetails && (
          <div className="mt-2 ml-7 p-2 bg-muted/50 rounded text-xs font-mono overflow-x-auto">
            <EventDetails data={event.data} />
          </div>
        )}
      </div>
    </div>
  )
}

function EventDetails({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([key]) => key !== 'message')

  return (
    <div className="space-y-1">
      {entries.map(([key, value]) => (
        <div key={key} className="flex gap-2">
          <span className="text-muted-foreground">{key}:</span>
          <span className="text-foreground break-all">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </span>
        </div>
      ))}
    </div>
  )
}

function formatRelativeTime(timestamp: string): string {
  const now = Date.now()
  const time = new Date(timestamp).getTime()
  const diff = now - time

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 10) return 'now'
  if (seconds < 60) return `${seconds}s`
  if (minutes < 60) return `${minutes}m`
  if (hours < 24) return `${hours}h`
  return `${days}d`
}

interface EventConfig {
  icon: typeof Activity
  label: string
  iconClass: string
  iconBgClass: string
  textClass: string
  bgClass: string
}

function getEventConfig(type: string): EventConfig {
  const configs: Record<string, EventConfig> = {
    // Operations
    operation_started: {
      icon: Play,
      label: 'Operation Started',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    operation_progress: {
      icon: RefreshCw,
      label: 'In Progress',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    operation_completed: {
      icon: CheckCircle,
      label: 'Completed',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },
    operation_failed: {
      icon: XCircle,
      label: 'Failed',
      iconClass: 'text-red-500',
      iconBgClass: 'bg-red-500/10',
      textClass: 'text-red-500',
      bgClass: 'hover:bg-red-500/5',
    },

    // Deployments
    deployment_started: {
      icon: Rocket,
      label: 'Deployment Started',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    deployment_progress: {
      icon: RefreshCw,
      label: 'Deploying',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    deployment_completed: {
      icon: CheckCircle,
      label: 'Deployed',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },
    deployment_failed: {
      icon: XCircle,
      label: 'Deploy Failed',
      iconClass: 'text-red-500',
      iconBgClass: 'bg-red-500/10',
      textClass: 'text-red-500',
      bgClass: 'hover:bg-red-500/5',
    },
    deployment_rolled_back: {
      icon: RefreshCw,
      label: 'Rolled Back',
      iconClass: 'text-orange-500',
      iconBgClass: 'bg-orange-500/10',
      textClass: 'text-orange-500',
      bgClass: 'hover:bg-orange-500/5',
    },

    // Resources
    resource_discovered: {
      icon: Search,
      label: 'Discovered',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    resource_updated: {
      icon: RefreshCw,
      label: 'Updated',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    resource_deleted: {
      icon: Trash2,
      label: 'Deleted',
      iconClass: 'text-gray-500',
      iconBgClass: 'bg-gray-500/10',
      textClass: 'text-gray-500',
      bgClass: 'hover:bg-gray-500/5',
    },

    // Exposures
    exposure_created: {
      icon: Network,
      label: 'Exposure Created',
      iconClass: 'text-purple-500',
      iconBgClass: 'bg-purple-500/10',
      textClass: 'text-purple-500',
      bgClass: 'hover:bg-purple-500/5',
    },
    exposure_approved: {
      icon: CheckCircle,
      label: 'Approved',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },
    exposure_rejected: {
      icon: XCircle,
      label: 'Rejected',
      iconClass: 'text-red-500',
      iconBgClass: 'bg-red-500/10',
      textClass: 'text-red-500',
      bgClass: 'hover:bg-red-500/5',
    },
    exposure_deployed: {
      icon: Rocket,
      label: 'Exposure Deployed',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },

    // Airflow DAG events
    dag_triggered: {
      icon: Workflow,
      label: 'DAG Triggered',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },
    dag_run_started: {
      icon: Play,
      label: 'DAG Running',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    dag_run_completed: {
      icon: CheckCircle,
      label: 'DAG Completed',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },
    dag_run_failed: {
      icon: XCircle,
      label: 'DAG Failed',
      iconClass: 'text-red-500',
      iconBgClass: 'bg-red-500/10',
      textClass: 'text-red-500',
      bgClass: 'hover:bg-red-500/5',
    },
    dag_paused: {
      icon: Pause,
      label: 'DAG Paused',
      iconClass: 'text-yellow-500',
      iconBgClass: 'bg-yellow-500/10',
      textClass: 'text-yellow-500',
      bgClass: 'hover:bg-yellow-500/5',
    },
    dag_unpaused: {
      icon: Play,
      label: 'DAG Unpaused',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },
    dag_discovered: {
      icon: Search,
      label: 'DAG Discovered',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },

    // n8n Workflow events
    workflow_executed: {
      icon: Zap,
      label: 'Workflow Executed',
      iconClass: 'text-orange-500',
      iconBgClass: 'bg-orange-500/10',
      textClass: 'text-orange-500',
      bgClass: 'hover:bg-orange-500/5',
    },
    workflow_activated: {
      icon: Play,
      label: 'Workflow Activated',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },
    workflow_deactivated: {
      icon: Pause,
      label: 'Workflow Deactivated',
      iconClass: 'text-gray-500',
      iconBgClass: 'bg-gray-500/10',
      textClass: 'text-gray-500',
      bgClass: 'hover:bg-gray-500/5',
    },
    workflow_execution_completed: {
      icon: CheckCircle,
      label: 'Workflow Completed',
      iconClass: 'text-green-500',
      iconBgClass: 'bg-green-500/10',
      textClass: 'text-green-500',
      bgClass: 'hover:bg-green-500/5',
    },
    workflow_execution_failed: {
      icon: XCircle,
      label: 'Workflow Failed',
      iconClass: 'text-red-500',
      iconBgClass: 'bg-red-500/10',
      textClass: 'text-red-500',
      bgClass: 'hover:bg-red-500/5',
    },

    // AI / Langflow events
    flow_executed: {
      icon: Brain,
      label: 'Flow Executed',
      iconClass: 'text-purple-500',
      iconBgClass: 'bg-purple-500/10',
      textClass: 'text-purple-500',
      bgClass: 'hover:bg-purple-500/5',
    },
    flow_created: {
      icon: Brain,
      label: 'Flow Created',
      iconClass: 'text-purple-500',
      iconBgClass: 'bg-purple-500/10',
      textClass: 'text-purple-500',
      bgClass: 'hover:bg-purple-500/5',
    },
    flow_updated: {
      icon: Brain,
      label: 'Flow Updated',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },

    // System
    health_status_changed: {
      icon: Server,
      label: 'Health Changed',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    system_info: {
      icon: Info,
      label: 'Info',
      iconClass: 'text-blue-500',
      iconBgClass: 'bg-blue-500/10',
      textClass: 'text-blue-500',
      bgClass: 'hover:bg-blue-500/5',
    },
    system_warning: {
      icon: AlertTriangle,
      label: 'Warning',
      iconClass: 'text-yellow-500',
      iconBgClass: 'bg-yellow-500/10',
      textClass: 'text-yellow-500',
      bgClass: 'hover:bg-yellow-500/5',
    },
    system_error: {
      icon: XCircle,
      label: 'Error',
      iconClass: 'text-red-500',
      iconBgClass: 'bg-red-500/10',
      textClass: 'text-red-500',
      bgClass: 'hover:bg-red-500/5',
    },
  }

  return (
    configs[type] || {
      icon: Activity,
      label: type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
      iconClass: 'text-muted-foreground',
      iconBgClass: 'bg-muted',
      textClass: 'text-muted-foreground',
      bgClass: 'hover:bg-accent/50',
    }
  )
}

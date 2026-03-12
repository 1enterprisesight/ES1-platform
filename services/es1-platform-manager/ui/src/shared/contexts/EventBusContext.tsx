import { createContext, useContext, useEffect, useState, useCallback, useRef, ReactNode } from 'react'

export interface PlatformEvent {
  id: string
  type: string
  timestamp: string
  data: Record<string, unknown>
}

interface EventBusContextType {
  events: PlatformEvent[]
  connected: boolean
  subscribe: (eventType: string, handler: (event: PlatformEvent) => void) => () => void
  clearEvents: () => void
}

const EventBusContext = createContext<EventBusContextType | undefined>(undefined)

function notifyHandlers(
  handlersRef: React.RefObject<Map<string, Set<(event: PlatformEvent) => void>>>,
  event: PlatformEvent,
) {
  const handlers = handlersRef.current
  if (!handlers) return
  const typeHandlers = handlers.get(event.type)
  if (typeHandlers) {
    typeHandlers.forEach((handler) => handler(event))
  }
  const wildcardHandlers = handlers.get('*')
  if (wildcardHandlers) {
    wildcardHandlers.forEach((handler) => handler(event))
  }
}

export function EventBusProvider({ children }: { children: ReactNode }) {
  const [events, setEvents] = useState<PlatformEvent[]>([])
  const [connected, setConnected] = useState(false)
  const handlersRef = useRef<Map<string, Set<(event: PlatformEvent) => void>>>(new Map())

  // Load event history on mount
  useEffect(() => {
    fetch('/api/v1/events/history?limit=50')
      .then((res) => res.json())
      .then((data) => {
        if (data.events && Array.isArray(data.events)) {
          const historicalEvents: PlatformEvent[] = data.events.map((e: PlatformEvent) => ({
            id: e.id,
            type: e.type,
            timestamp: e.timestamp,
            data: e.data,
          }))
          setEvents(historicalEvents)
        }
      })
      .catch((err) => console.error('Failed to load event history:', err))
  }, [])

  // SSE connection — stable effect, no handler dependency
  useEffect(() => {
    const eventSource = new EventSource('/api/v1/events/stream')

    eventSource.onopen = () => {
      setConnected(true)
    }

    eventSource.onerror = () => {
      setConnected(false)
    }

    eventSource.onmessage = (e) => {
      if (e.data) {
        try {
          const eventData = JSON.parse(e.data)
          const event: PlatformEvent = {
            id: eventData.id,
            type: eventData.type,
            timestamp: eventData.timestamp,
            data: eventData.data,
          }

          setEvents((prev) => [event, ...prev].slice(0, 100))
          notifyHandlers(handlersRef, event)
        } catch (err) {
          console.error('Failed to parse event:', err)
        }
      }
    }

    // Handle specific event types
    const eventTypes = [
      // Operation events
      'operation_started',
      'operation_progress',
      'operation_completed',
      'operation_failed',
      // Deployment events
      'deployment_started',
      'deployment_progress',
      'deployment_completed',
      'deployment_failed',
      'deployment_rolled_back',
      // Resource events
      'resource_discovered',
      'resource_updated',
      'resource_deleted',
      // Exposure events
      'exposure_created',
      'exposure_approved',
      'exposure_rejected',
      'exposure_deployed',
      // System events
      'system_info',
      'system_warning',
      'system_error',
      'health_status_changed',
      // Workflow events (n8n)
      'workflow_executed',
      'workflow_activated',
      'workflow_deactivated',
      'workflow_execution_completed',
      'workflow_execution_failed',
      // DAG events (Airflow)
      'dag_triggered',
      'dag_paused',
      'dag_unpaused',
      'dag_discovered',
      // AI Flow events (Langflow)
      'flow_executed',
      'flow_created',
      'flow_updated',
    ]

    eventTypes.forEach((type) => {
      eventSource.addEventListener(type, (e: MessageEvent) => {
        try {
          const eventData = JSON.parse(e.data)
          const event: PlatformEvent = {
            id: eventData.id,
            type: type,
            timestamp: eventData.timestamp,
            data: eventData.data,
          }

          setEvents((prev) => [event, ...prev].slice(0, 100))
          notifyHandlers(handlersRef, event)
        } catch (err) {
          console.error('Failed to parse event:', err)
        }
      })
    })

    return () => {
      eventSource.close()
    }
  }, [])

  const subscribe = useCallback((eventType: string, handler: (event: PlatformEvent) => void) => {
    const handlers = handlersRef.current!
    const existing = handlers.get(eventType) || new Set()
    existing.add(handler)
    handlers.set(eventType, existing)

    return () => {
      const existing = handlers.get(eventType)
      if (existing) {
        existing.delete(handler)
        if (existing.size === 0) {
          handlers.delete(eventType)
        }
      }
    }
  }, [])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  return (
    <EventBusContext.Provider value={{ events, connected, subscribe, clearEvents }}>
      {children}
    </EventBusContext.Provider>
  )
}

export function useEventBus() {
  const context = useContext(EventBusContext)
  if (!context) {
    throw new Error('useEventBus must be used within an EventBusProvider')
  }
  return context
}

export function useEvent(eventType: string, handler: (event: PlatformEvent) => void) {
  const { subscribe } = useEventBus()

  useEffect(() => {
    return subscribe(eventType, handler)
  }, [eventType, handler, subscribe])
}

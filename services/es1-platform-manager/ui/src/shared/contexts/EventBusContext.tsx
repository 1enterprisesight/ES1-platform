import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'

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
}

const EventBusContext = createContext<EventBusContextType | undefined>(undefined)

export function EventBusProvider({ children }: { children: ReactNode }) {
  const [events, setEvents] = useState<PlatformEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [handlers, setHandlers] = useState<Map<string, Set<(event: PlatformEvent) => void>>>(new Map())

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

          // Notify subscribers
          const typeHandlers = handlers.get(event.type)
          if (typeHandlers) {
            typeHandlers.forEach((handler) => handler(event))
          }
          // Also notify wildcard subscribers
          const wildcardHandlers = handlers.get('*')
          if (wildcardHandlers) {
            wildcardHandlers.forEach((handler) => handler(event))
          }
        } catch (err) {
          console.error('Failed to parse event:', err)
        }
      }
    }

    // Handle specific event types
    const eventTypes = [
      'operation_started',
      'operation_progress',
      'operation_completed',
      'operation_failed',
      'deployment_started',
      'deployment_progress',
      'deployment_completed',
      'deployment_failed',
      'deployment_rolled_back',
      'resource_discovered',
      'resource_updated',
      'exposure_created',
      'exposure_approved',
      'system_info',
      'system_warning',
      'system_error',
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

          const typeHandlers = handlers.get(type)
          if (typeHandlers) {
            typeHandlers.forEach((handler) => handler(event))
          }
          const wildcardHandlers = handlers.get('*')
          if (wildcardHandlers) {
            wildcardHandlers.forEach((handler) => handler(event))
          }
        } catch (err) {
          console.error('Failed to parse event:', err)
        }
      })
    })

    return () => {
      eventSource.close()
    }
  }, [handlers])

  const subscribe = useCallback((eventType: string, handler: (event: PlatformEvent) => void) => {
    setHandlers((prev) => {
      const newHandlers = new Map(prev)
      const existing = newHandlers.get(eventType) || new Set()
      existing.add(handler)
      newHandlers.set(eventType, existing)
      return newHandlers
    })

    return () => {
      setHandlers((prev) => {
        const newHandlers = new Map(prev)
        const existing = newHandlers.get(eventType)
        if (existing) {
          existing.delete(handler)
          if (existing.size === 0) {
            newHandlers.delete(eventType)
          }
        }
        return newHandlers
      })
    }
  }, [])

  return (
    <EventBusContext.Provider value={{ events, connected, subscribe }}>
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

"""Event bus for real-time updates via SSE and WebSocket."""
import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4
from pydantic import BaseModel


class EventType(str, Enum):
    """Event types for the platform manager."""
    # Operation events
    OPERATION_STARTED = "operation_started"
    OPERATION_PROGRESS = "operation_progress"
    OPERATION_COMPLETED = "operation_completed"
    OPERATION_FAILED = "operation_failed"

    # Health events
    HEALTH_STATUS_CHANGED = "health_status_changed"

    # Resource events
    RESOURCE_DISCOVERED = "resource_discovered"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"

    # Exposure events
    EXPOSURE_CREATED = "exposure_created"
    EXPOSURE_APPROVED = "exposure_approved"
    EXPOSURE_REJECTED = "exposure_rejected"
    EXPOSURE_DEPLOYED = "exposure_deployed"

    # Deployment events
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_PROGRESS = "deployment_progress"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"
    DEPLOYMENT_ROLLED_BACK = "deployment_rolled_back"

    # System events
    SYSTEM_INFO = "system_info"
    SYSTEM_WARNING = "system_warning"
    SYSTEM_ERROR = "system_error"


class Event(BaseModel):
    """Event model for broadcasting to clients."""
    id: str
    type: EventType
    timestamp: str
    data: dict[str, Any]

    @classmethod
    def create(cls, event_type: EventType, data: dict[str, Any]) -> "Event":
        """Create a new event with auto-generated ID and timestamp."""
        return cls(
            id=str(uuid4()),
            type=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            data=data,
        )

    def to_sse(self) -> str:
        """Format event for SSE transmission."""
        return f"id: {self.id}\nevent: {self.type.value}\ndata: {json.dumps(self.data)}\n\n"


class EventBus:
    """
    Event bus for broadcasting real-time updates.

    Supports both SSE (Server-Sent Events) and WebSocket clients.
    Events are broadcast to all connected clients.
    """

    def __init__(self, max_history: int = 100):
        """Initialize the event bus."""
        self._subscribers: list[asyncio.Queue] = []
        self._history: list[Event] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to events.

        Returns a queue that will receive all future events.
        """
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from events."""
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    async def publish(self, event_type: EventType, data: dict[str, Any]) -> Event:
        """
        Publish an event to all subscribers.

        Args:
            event_type: The type of event
            data: Event payload data

        Returns:
            The created event
        """
        event = Event.create(event_type, data)

        async with self._lock:
            # Add to history
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Broadcast to all subscribers
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Skip if queue is full (slow consumer)
                    pass

        return event

    async def get_history(self, limit: int = 50, event_types: list[EventType] | None = None) -> list[Event]:
        """
        Get recent event history.

        Args:
            limit: Maximum number of events to return
            event_types: Optional filter for specific event types

        Returns:
            List of recent events, newest first
        """
        async with self._lock:
            events = self._history.copy()

        if event_types:
            events = [e for e in events if e.type in event_types]

        return list(reversed(events[-limit:]))

    @property
    def subscriber_count(self) -> int:
        """Get the current number of subscribers."""
        return len(self._subscribers)


# Global event bus instance
event_bus = EventBus()


# Convenience functions for common event types
async def emit_operation_started(
    operation: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> Event:
    """Emit an operation started event."""
    return await event_bus.publish(
        EventType.OPERATION_STARTED,
        {
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id,
            **(details or {}),
        },
    )


async def emit_operation_progress(
    operation: str,
    progress: int,
    message: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> Event:
    """Emit an operation progress event."""
    return await event_bus.publish(
        EventType.OPERATION_PROGRESS,
        {
            "operation": operation,
            "progress": progress,
            "message": message,
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )


async def emit_operation_completed(
    operation: str,
    entity_type: str,
    entity_id: str | None = None,
    result: dict[str, Any] | None = None,
) -> Event:
    """Emit an operation completed event."""
    return await event_bus.publish(
        EventType.OPERATION_COMPLETED,
        {
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "result": result,
        },
    )


async def emit_operation_failed(
    operation: str,
    entity_type: str,
    error: str,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> Event:
    """Emit an operation failed event."""
    return await event_bus.publish(
        EventType.OPERATION_FAILED,
        {
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "error": error,
            **(details or {}),
        },
    )


async def emit_deployment_event(
    event_type: EventType,
    deployment_id: str,
    version: int | None = None,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> Event:
    """Emit a deployment-related event."""
    return await event_bus.publish(
        event_type,
        {
            "deployment_id": deployment_id,
            "version": version,
            "message": message,
            **(details or {}),
        },
    )

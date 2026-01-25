"""Events API routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel, field_serializer
from datetime import datetime

from app.core.database import get_db
from app.models import EventLog

router = APIRouter(prefix="/events", tags=["events"])


class EventResponse(BaseModel):
    """Event response schema."""

    id: UUID
    event_type: str
    entity_type: str
    entity_id: UUID
    user_id: str | None
    event_metadata: dict | None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime) -> str:
        """Serialize datetime as ISO 8601 with UTC indicator."""
        return dt.isoformat() + 'Z'

    class Config:
        from_attributes = True


@router.get("", response_model=list[EventResponse])
async def list_events(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List recent events for activity feed."""
    query = (
        select(EventLog)
        .order_by(EventLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    return [EventResponse.model_validate(event) for event in events]

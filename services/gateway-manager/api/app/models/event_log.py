"""Event log model."""
from sqlalchemy import Column, String, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from app.core.database import Base


class EventLog(Base):
    """Event log (for audit trail)."""

    __tablename__ = "event_log"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    event_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(String(255), nullable=True)
    event_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_events_type", "event_type"),
        Index("idx_events_entity", "entity_type", "entity_id"),
        Index("idx_events_created", "created_at"),
    )

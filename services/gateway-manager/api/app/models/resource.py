"""Discovered resource model."""
from sqlalchemy import Column, String, TIMESTAMP, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class DiscoveredResource(Base):
    """Discovered resources from external systems."""

    __tablename__ = "discovered_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    type = Column(String(50), nullable=False)  # workflow, connection, service, etc.
    source = Column(String(50), nullable=False)  # airflow, kubernetes, manual
    source_id = Column(String(255), nullable=False)  # ID in source system
    resource_metadata = Column("metadata", JSONB, nullable=False)  # Resource-specific data
    discovered_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    last_updated = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    status = Column(String(20), nullable=False, server_default="active")  # active, inactive, deleted

    __table_args__ = (
        Index("idx_resources_type", "type"),
        Index("idx_resources_source", "source"),
        Index("idx_resources_status", "status"),
    )

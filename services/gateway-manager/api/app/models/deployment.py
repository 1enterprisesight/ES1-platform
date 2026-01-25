"""Deployment model."""
from sqlalchemy import Column, String, TIMESTAMP, Index, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from app.core.database import Base


class Deployment(Base):
    """Deployments."""

    __tablename__ = "deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    version_id = Column(UUID(as_uuid=True), ForeignKey("config_versions.id"), nullable=False)
    status = Column(String(20), nullable=False, server_default="pending")  # pending, in_progress, succeeded, failed, rolled_back
    deployed_by = Column(String(255), nullable=False)
    deployed_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP, nullable=True)
    health_check_passed = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    rollback_from_deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True)

    __table_args__ = (
        Index("idx_deployments_status", "status"),
        Index("idx_deployments_version", "version_id"),
        Index("idx_deployments_deployed_at", "deployed_at"),
    )

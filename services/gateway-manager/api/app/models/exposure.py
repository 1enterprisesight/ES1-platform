"""Exposure model."""
from sqlalchemy import Column, String, TIMESTAMP, Index, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from app.core.database import Base


class Exposure(Base):
    """Exposures (tagged resources)."""

    __tablename__ = "exposures"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    resource_id = Column(UUID(as_uuid=True), ForeignKey("discovered_resources.id", ondelete="CASCADE"), nullable=False)
    settings = Column(JSONB, nullable=False)  # User settings (rate limit, access level)
    generated_config = Column(JSONB, nullable=False)  # Auto-generated endpoint config
    status = Column(String(20), nullable=False, server_default="pending")  # pending, approved, rejected, deployed
    created_by = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(TIMESTAMP, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Deployment tracking (added in migration 001)
    deployed_in_version_id = Column(UUID(as_uuid=True), ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)
    removed_in_version_id = Column(UUID(as_uuid=True), ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("idx_exposures_status", "status"),
        Index("idx_exposures_resource", "resource_id"),
        Index("idx_exposures_deployed_in_version", "deployed_in_version_id"),
        Index("idx_exposures_removed_in_version", "removed_in_version_id"),
    )

"""Exposure change model."""
from sqlalchemy import Column, String, TIMESTAMP, Index, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from app.core.database import Base


class ExposureChange(Base):
    """Exposure changes (change management workflow)."""

    __tablename__ = "exposure_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))

    # What's changing
    exposure_id = Column(UUID(as_uuid=True), ForeignKey("exposures.id", ondelete="SET NULL"), nullable=True)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("discovered_resources.id", ondelete="CASCADE"), nullable=False)
    change_type = Column(String(20), nullable=False)  # add, remove, modify

    # Change details
    settings_before = Column(JSONB, nullable=True)  # For modify: old settings
    settings_after = Column(JSONB, nullable=True)   # For add/modify: new settings

    # Workflow status
    status = Column(String(20), nullable=False, server_default="draft")
    # draft, pending_approval, approved, rejected, deployed, cancelled

    # Batch grouping
    batch_id = Column(UUID(as_uuid=True), nullable=True)

    # People and timestamps
    requested_by = Column(String(255), nullable=False)
    requested_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    submitted_for_approval_at = Column(TIMESTAMP, nullable=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(TIMESTAMP, nullable=True)
    rejected_by = Column(String(255), nullable=True)
    rejected_at = Column(TIMESTAMP, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Deployment tracking
    deployed_in_version_id = Column(UUID(as_uuid=True), ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)
    deployed_at = Column(TIMESTAMP, nullable=True)

    __table_args__ = (
        Index("idx_exposure_changes_status", "status"),
        Index("idx_exposure_changes_batch", "batch_id"),
        Index("idx_exposure_changes_resource", "resource_id"),
    )

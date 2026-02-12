"""Database models for the gateway module."""
from sqlalchemy import Column, String, TIMESTAMP, Index, ForeignKey, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from app.core.database import Base


class DiscoveredResource(Base):
    """Discovered resources from external systems."""

    __tablename__ = "discovered_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    type = Column(String(50), nullable=False)  # workflow, connection, service, flow
    source = Column(String(50), nullable=False)  # airflow, kubernetes, manual, langflow
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


class ConfigVersion(Base):
    """Configuration versions (audit trail)."""

    __tablename__ = "config_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(Integer, nullable=False, unique=True)
    config_snapshot = Column(JSONB, nullable=False)  # Complete gateway config
    created_by = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    commit_message = Column(Text, nullable=True)

    # Active version tracking
    is_active = Column(Boolean, nullable=False, server_default=text("false"))
    deployed_to_gateway_at = Column(TIMESTAMP, nullable=True)

    # Status tracking for approval workflow
    status = Column(String(50), nullable=True)  # pending_approval, approved, deployed, rejected

    # Approval tracking
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(TIMESTAMP, nullable=True)

    # Rejection tracking
    rejected_by = Column(String(255), nullable=True)
    rejected_at = Column(TIMESTAMP, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_versions_created", "created_at"),
        Index("idx_config_versions_is_active", "is_active", postgresql_where=text("is_active = true")),
    )


class Exposure(Base):
    """Exposures (tagged resources for API gateway)."""

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

    # Deployment tracking
    deployed_in_version_id = Column(UUID(as_uuid=True), ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)
    removed_in_version_id = Column(UUID(as_uuid=True), ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("idx_exposures_status", "status"),
        Index("idx_exposures_resource", "resource_id"),
        Index("idx_exposures_deployed_in_version", "deployed_in_version_id"),
        Index("idx_exposures_removed_in_version", "removed_in_version_id"),
    )


class ChangeSet(Base):
    """Change sets for batching gateway configuration changes."""

    __tablename__ = "change_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    base_version_id = Column(UUID(as_uuid=True), ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, server_default="draft")
    # draft, submitted, approved, rejected, deployed, cancelled
    created_by = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    submitted_at = Column(TIMESTAMP, nullable=True)
    description = Column(Text, nullable=True)
    config_version_id = Column(UUID(as_uuid=True), ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("idx_change_sets_status", "status"),
        Index("idx_change_sets_created_by", "created_by"),
        Index("idx_change_sets_created_at", "created_at"),
    )


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

    # Change set link
    change_set_id = Column(UUID(as_uuid=True), ForeignKey("change_sets.id", ondelete="SET NULL"), nullable=True)

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
        Index("idx_exposure_changes_change_set", "change_set_id"),
    )


class Deployment(Base):
    """Deployment records."""

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


class Approval(Base):
    """Approval workflow records."""

    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    exposure_id = Column(UUID(as_uuid=True), ForeignKey("exposures.id", ondelete="CASCADE"), nullable=False)
    approver = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # approved, rejected, pending
    comments = Column(Text, nullable=True)
    approved_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_approvals_exposure", "exposure_id"),
        Index("idx_approvals_status", "status"),
    )


class EventLog(Base):
    """Event log for audit trail."""

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

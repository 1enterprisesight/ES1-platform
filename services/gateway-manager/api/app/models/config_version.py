"""Configuration version model."""
from sqlalchemy import Column, String, TIMESTAMP, Index, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from app.core.database import Base


class ConfigVersion(Base):
    """Configuration versions (audit trail)."""

    __tablename__ = "config_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(Integer, nullable=False, unique=True)
    config_snapshot = Column(JSONB, nullable=False)  # Complete gateway config
    created_by = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    commit_message = Column(Text, nullable=True)

    # Active version tracking (added in migration 001)
    is_active = Column(Boolean, nullable=False, server_default=text("false"))
    deployed_to_gateway_at = Column(TIMESTAMP, nullable=True)

    # Status tracking for approval workflow (added in Session 14)
    status = Column(String(50), nullable=True)  # pending_approval, approved, deployed, rejected

    # Approval tracking (added in Session 14 Step 1.2)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(TIMESTAMP, nullable=True)

    # Rejection tracking (added in Session 18)
    rejected_by = Column(String(255), nullable=True)
    rejected_at = Column(TIMESTAMP, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_versions_created", "created_at"),
        Index("idx_config_versions_is_active", "is_active", postgresql_where=text("is_active = true")),
    )

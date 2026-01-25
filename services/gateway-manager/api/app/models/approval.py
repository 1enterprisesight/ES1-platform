"""Approval model."""
from sqlalchemy import Column, String, TIMESTAMP, Index, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from app.core.database import Base


class Approval(Base):
    """Approval workflow."""

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

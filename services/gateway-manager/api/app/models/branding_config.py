"""Branding configuration model."""
from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from app.core.database import Base


class BrandingConfig(Base):
    """Branding configuration (singleton table)."""

    __tablename__ = "branding_config"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    company_name = Column(String(100), nullable=False)
    product_name = Column(String(100), nullable=False)
    logo_url = Column(String(500), nullable=False)
    favicon_url = Column(String(500), nullable=False)
    colors = Column(JSONB, nullable=False)
    fonts = Column(JSONB, nullable=False)
    terminology = Column(JSONB, nullable=False)
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

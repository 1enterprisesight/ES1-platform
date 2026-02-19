"""Settings database models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Setting(Base):
    """Key-value settings storage."""
    __tablename__ = "settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    is_secret = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BrandingConfig(Base):
    """Branding configuration."""
    __tablename__ = "branding_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, default="Engine Platform")
    tagline = Column(String(500), nullable=True)
    logo_url = Column(String(1000), nullable=True)
    logo_dark_url = Column(String(1000), nullable=True)
    favicon_url = Column(String(1000), nullable=True)
    primary_color = Column(String(50), default="#3B82F6")
    secondary_color = Column(String(50), default="#10B981")
    accent_color = Column(String(50), default="#8B5CF6")
    custom_css = Column(Text, nullable=True)
    custom_js = Column(Text, nullable=True)
    footer_text = Column(Text, nullable=True)
    support_email = Column(String(255), nullable=True)
    support_url = Column(String(1000), nullable=True)
    docs_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

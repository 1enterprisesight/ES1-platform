"""Settings schemas."""
from typing import Any
from pydantic import BaseModel


class SettingResponse(BaseModel):
    """Setting response."""
    key: str
    value: Any
    description: str | None = None
    category: str | None = None
    is_secret: bool = False

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    """Setting update request."""
    value: Any
    description: str | None = None
    category: str | None = None


class SettingsListResponse(BaseModel):
    """List of settings."""
    settings: list[SettingResponse]


class BrandingResponse(BaseModel):
    """Branding configuration response."""
    name: str = "Engine Platform"
    tagline: str | None = None
    logo_url: str | None = None
    logo_dark_url: str | None = None
    favicon_url: str | None = None
    primary_color: str = "#3B82F6"
    secondary_color: str = "#10B981"
    accent_color: str = "#8B5CF6"
    custom_css: str | None = None
    footer_text: str | None = None
    support_email: str | None = None
    support_url: str | None = None
    docs_url: str | None = None

    class Config:
        from_attributes = True


class BrandingUpdate(BaseModel):
    """Branding update request."""
    name: str | None = None
    tagline: str | None = None
    logo_url: str | None = None
    logo_dark_url: str | None = None
    favicon_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    custom_css: str | None = None
    footer_text: str | None = None
    support_email: str | None = None
    support_url: str | None = None
    docs_url: str | None = None


class FeatureFlagsResponse(BaseModel):
    """Feature flags response."""
    gateway_enabled: bool = True
    workflows_enabled: bool = True
    ai_flows_enabled: bool = True
    observability_enabled: bool = True
    automation_enabled: bool = False
    dark_mode_enabled: bool = True
    api_docs_enabled: bool = True


class FeatureFlagsUpdate(BaseModel):
    """Feature flags update request."""
    gateway_enabled: bool | None = None
    workflows_enabled: bool | None = None
    ai_flows_enabled: bool | None = None
    observability_enabled: bool | None = None
    automation_enabled: bool | None = None
    dark_mode_enabled: bool | None = None
    api_docs_enabled: bool | None = None

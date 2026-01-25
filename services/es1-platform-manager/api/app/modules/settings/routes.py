"""Settings and branding routes."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_admin, UserContext
from app.core.events import event_bus, EventType
from .models import Setting, BrandingConfig
from .schemas import (
    SettingResponse,
    SettingUpdate,
    SettingsListResponse,
    BrandingResponse,
    BrandingUpdate,
    FeatureFlagsResponse,
    FeatureFlagsUpdate,
)


router = APIRouter(prefix="/settings", tags=["Settings"])


# =============================================================================
# General Settings
# =============================================================================

@router.get("/", response_model=SettingsListResponse)
async def list_settings(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all settings."""
    query = select(Setting)
    if category:
        query = query.where(Setting.category == category)
    query = query.order_by(Setting.category, Setting.key)

    result = await db.execute(query)
    settings = result.scalars().all()

    return SettingsListResponse(
        settings=[
            SettingResponse(
                key=s.key,
                value="***" if s.is_secret else s.value,
                description=s.description,
                category=s.category,
                is_secret=s.is_secret,
            )
            for s in settings
        ]
    )


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific setting."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    return SettingResponse(
        key=setting.key,
        value="***" if setting.is_secret else setting.value,
        description=setting.description,
        category=setting.category,
        is_secret=setting.is_secret,
    )


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    request: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_admin),
):
    """Update or create a setting (admin only)."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = request.value
        if request.description is not None:
            setting.description = request.description
        if request.category is not None:
            setting.category = request.category
    else:
        setting = Setting(
            key=key,
            value=request.value,
            description=request.description,
            category=request.category,
        )
        db.add(setting)

    await db.commit()
    await db.refresh(setting)

    await event_bus.publish(
        EventType.SYSTEM_INFO,
        {
            "message": f"Setting '{key}' updated",
            "user": user.username,
        },
    )

    return SettingResponse(
        key=setting.key,
        value="***" if setting.is_secret else setting.value,
        description=setting.description,
        category=setting.category,
        is_secret=setting.is_secret,
    )


@router.delete("/{key}")
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_admin),
):
    """Delete a setting (admin only)."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    await db.delete(setting)
    await db.commit()

    return {"message": f"Setting '{key}' deleted"}


# =============================================================================
# Branding
# =============================================================================

@router.get("/branding/config", response_model=BrandingResponse)
async def get_branding(db: AsyncSession = Depends(get_db)):
    """Get branding configuration."""
    result = await db.execute(select(BrandingConfig).limit(1))
    branding = result.scalar_one_or_none()

    if not branding:
        return BrandingResponse()

    return BrandingResponse(
        name=branding.name,
        tagline=branding.tagline,
        logo_url=branding.logo_url,
        logo_dark_url=branding.logo_dark_url,
        favicon_url=branding.favicon_url,
        primary_color=branding.primary_color,
        secondary_color=branding.secondary_color,
        accent_color=branding.accent_color,
        custom_css=branding.custom_css,
        footer_text=branding.footer_text,
        support_email=branding.support_email,
        support_url=branding.support_url,
        docs_url=branding.docs_url,
    )


@router.put("/branding/config", response_model=BrandingResponse)
async def update_branding(
    request: BrandingUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_admin),
):
    """Update branding configuration (admin only)."""
    result = await db.execute(select(BrandingConfig).limit(1))
    branding = result.scalar_one_or_none()

    if not branding:
        branding = BrandingConfig()
        db.add(branding)

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(branding, key, value)

    await db.commit()
    await db.refresh(branding)

    await event_bus.publish(
        EventType.SYSTEM_INFO,
        {
            "message": "Branding configuration updated",
            "user": user.username,
        },
    )

    return BrandingResponse(
        name=branding.name,
        tagline=branding.tagline,
        logo_url=branding.logo_url,
        logo_dark_url=branding.logo_dark_url,
        favicon_url=branding.favicon_url,
        primary_color=branding.primary_color,
        secondary_color=branding.secondary_color,
        accent_color=branding.accent_color,
        custom_css=branding.custom_css,
        footer_text=branding.footer_text,
        support_email=branding.support_email,
        support_url=branding.support_url,
        docs_url=branding.docs_url,
    )


# =============================================================================
# Feature Flags
# =============================================================================

# Default feature flags
DEFAULT_FEATURE_FLAGS = {
    "gateway_enabled": True,
    "workflows_enabled": True,
    "ai_flows_enabled": True,
    "observability_enabled": True,
    "automation_enabled": False,
    "dark_mode_enabled": True,
    "api_docs_enabled": True,
}


@router.get("/features/flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(db: AsyncSession = Depends(get_db)):
    """Get feature flags."""
    result = await db.execute(
        select(Setting).where(Setting.key == "feature_flags")
    )
    setting = result.scalar_one_or_none()

    if not setting or not setting.value:
        return FeatureFlagsResponse(**DEFAULT_FEATURE_FLAGS)

    flags = {**DEFAULT_FEATURE_FLAGS, **setting.value}
    return FeatureFlagsResponse(**flags)


@router.put("/features/flags", response_model=FeatureFlagsResponse)
async def update_feature_flags(
    request: FeatureFlagsUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_admin),
):
    """Update feature flags (admin only)."""
    result = await db.execute(
        select(Setting).where(Setting.key == "feature_flags")
    )
    setting = result.scalar_one_or_none()

    current_flags = DEFAULT_FEATURE_FLAGS.copy()
    if setting and setting.value:
        current_flags.update(setting.value)

    # Update with new values
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            current_flags[key] = value

    if setting:
        setting.value = current_flags
    else:
        setting = Setting(
            key="feature_flags",
            value=current_flags,
            description="Feature flags configuration",
            category="features",
        )
        db.add(setting)

    await db.commit()

    await event_bus.publish(
        EventType.SYSTEM_INFO,
        {
            "message": "Feature flags updated",
            "user": user.username,
        },
    )

    return FeatureFlagsResponse(**current_flags)

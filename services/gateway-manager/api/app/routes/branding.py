"""Branding configuration routes."""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import BrandingConfig as BrandingConfigModel

router = APIRouter(prefix="/branding", tags=["branding"])


class ColorConfig(BaseModel):
    """Color configuration."""
    primary: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    primaryHover: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    secondaryHover: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    accent: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    danger: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    success: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    warning: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    info: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")


class FontConfig(BaseModel):
    """Font configuration."""
    heading: str
    body: str
    mono: str


class TerminologyConfig(BaseModel):
    """Terminology configuration."""
    workflow: str
    workflows: str
    connection: str
    connections: str
    service: str
    services: str
    gateway: str
    orchestrator: str
    exposure: str
    exposures: str
    pushToGateway: str
    approve: str
    reject: str
    deploy: str
    deployment: str
    rollback: str


class BrandingConfig(BaseModel):
    """Complete branding configuration."""
    companyName: str = Field(..., min_length=1, max_length=100)
    productName: str = Field(..., min_length=1, max_length=100)
    logoUrl: str
    faviconUrl: str
    colors: ColorConfig
    fonts: FontConfig
    terminology: TerminologyConfig


@router.get("")
async def get_branding(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get current branding configuration from database.

    Returns:
        Current branding configuration
    """
    try:
        # Query the database for branding config (singleton table)
        result = await db.execute(select(BrandingConfigModel).limit(1))
        branding = result.scalar_one_or_none()

        if not branding:
            # No branding exists, create default and return it
            default_branding = BrandingConfigModel(
                company_name="Enterprise Sight",
                product_name="Core-GW",
                logo_url="/assets/logo.png",
                favicon_url="/assets/favicon.ico",
                colors={
                    "primary": "#1a73e8",
                    "primaryHover": "#1557b0",
                    "secondary": "#34a853",
                    "secondaryHover": "#2a8a43",
                    "accent": "#fbbc04",
                    "danger": "#ea4335",
                    "success": "#34a853",
                    "warning": "#fbbc04",
                    "info": "#4285f4"
                },
                fonts={
                    "heading": "Inter, sans-serif",
                    "body": "Inter, sans-serif",
                    "mono": "Courier New, monospace"
                },
                terminology={
                    "workflow": "Workflow",
                    "workflows": "Workflows",
                    "connection": "Service Connection",
                    "connections": "Service Connections",
                    "service": "Service",
                    "services": "Services",
                    "gateway": "API Gateway",
                    "orchestrator": "Workflow Engine",
                    "exposure": "Gateway Exposure",
                    "exposures": "Gateway Exposures",
                    "pushToGateway": "Push to Core-GW",
                    "approve": "Approve",
                    "reject": "Reject",
                    "deploy": "Deploy",
                    "deployment": "Deployment",
                    "rollback": "Rollback"
                }
            )
            db.add(default_branding)
            await db.commit()
            await db.refresh(default_branding)
            branding = default_branding

        # Map database model to API response format
        return {
            "companyName": branding.company_name,
            "productName": branding.product_name,
            "logoUrl": branding.logo_url,
            "faviconUrl": branding.favicon_url,
            "colors": branding.colors,
            "fonts": branding.fonts,
            "terminology": branding.terminology
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read branding configuration: {str(e)}"
        )


@router.put("")
async def update_branding(
    branding: BrandingConfig,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update branding configuration in database.

    Args:
        branding: New branding configuration
        db: Database session

    Returns:
        Success message with updated configuration
    """
    try:
        # Query for existing branding config (singleton table)
        result = await db.execute(select(BrandingConfigModel).limit(1))
        db_branding = result.scalar_one_or_none()

        if not db_branding:
            # Create new branding record
            db_branding = BrandingConfigModel(
                company_name=branding.companyName,
                product_name=branding.productName,
                logo_url=branding.logoUrl,
                favicon_url=branding.faviconUrl,
                colors=branding.colors.model_dump(),
                fonts=branding.fonts.model_dump(),
                terminology=branding.terminology.model_dump(),
                updated_by="api_user"  # TODO: Get from auth context
            )
            db.add(db_branding)
        else:
            # Update existing record
            db_branding.company_name = branding.companyName
            db_branding.product_name = branding.productName
            db_branding.logo_url = branding.logoUrl
            db_branding.favicon_url = branding.faviconUrl
            db_branding.colors = branding.colors.model_dump()
            db_branding.fonts = branding.fonts.model_dump()
            db_branding.terminology = branding.terminology.model_dump()
            db_branding.updated_by = "api_user"  # TODO: Get from auth context

        await db.commit()
        await db.refresh(db_branding)

        return {
            "success": True,
            "message": "Branding configuration updated successfully.",
            "branding": branding.model_dump()
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update branding configuration: {str(e)}"
        )

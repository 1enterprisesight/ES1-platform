"""Authentication routes."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    AuthService,
    UserContext,
    get_current_user,
    require_admin,
)
from app.core.config import settings
from app.core.database import get_db


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==========================================================================
# Models
# ==========================================================================


class MeResponse(BaseModel):
    """Current user information."""
    api_key_id: str | None
    user_id: str | None
    username: str | None
    permissions: list[str]
    is_admin: bool


class LoginRequest(BaseModel):
    """Request to validate an API key."""
    api_key: str


class LoginResponse(BaseModel):
    """Response with validation result."""
    authenticated: bool
    user: MeResponse | None = None


class CreateApiKeyRequest(BaseModel):
    """Request to create a new API key."""
    name: str
    user_id: str | None = None
    username: str | None = None
    permissions: list[str] = []
    is_admin: bool = False


class CreateApiKeyResponse(BaseModel):
    """Response with new API key."""
    key: str
    key_id: str
    message: str


class ApiKeyInfo(BaseModel):
    """API key information (without the actual key)."""
    id: str
    name: str
    user_id: str | None
    username: str | None
    permissions: list[str]
    is_admin: bool
    created_at: str | None


class ApiKeyListResponse(BaseModel):
    """Response with list of API keys."""
    keys: list[ApiKeyInfo]


# ==========================================================================
# Public endpoints (no auth required)
# ==========================================================================


@router.get("/status")
async def auth_status():
    """Get authentication status (public - no auth required)."""
    return {
        "auth_required": settings.auth_enabled,
        "auth_mode": settings.AUTH_MODE,
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate an API key and return user info.

    Used by the UI login page to verify credentials before storing the key.
    This endpoint does not require authentication itself.
    """
    if not settings.auth_enabled:
        return LoginResponse(
            authenticated=True,
            user=MeResponse(
                api_key_id=None,
                user_id="anonymous",
                username="anonymous",
                permissions=["*"],
                is_admin=True,
            ),
        )

    user = await AuthService.validate_key(request.api_key, db)
    if not user:
        return LoginResponse(authenticated=False)

    return LoginResponse(
        authenticated=True,
        user=MeResponse(
            api_key_id=user.api_key_id,
            user_id=user.user_id,
            username=user.username,
            permissions=user.permissions,
            is_admin=user.is_admin,
        ),
    )


# ==========================================================================
# Authenticated endpoints
# ==========================================================================


@router.get("/me", response_model=MeResponse)
async def get_me(user: UserContext = Depends(get_current_user)):
    """Get current authenticated user information."""
    return MeResponse(
        api_key_id=user.api_key_id,
        user_id=user.user_id,
        username=user.username,
        permissions=user.permissions,
        is_admin=user.is_admin,
    )


@router.get("/keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys (admin only)."""
    keys = await AuthService.list_keys(db)
    return ApiKeyListResponse(
        keys=[
            ApiKeyInfo(
                id=k["id"],
                name=k["name"],
                user_id=k.get("user_id"),
                username=k.get("username"),
                permissions=k.get("permissions", []),
                is_admin=k.get("is_admin", False),
                created_at=k.get("created_at"),
            )
            for k in keys
        ]
    )


@router.post("/keys", response_model=CreateApiKeyResponse)
async def create_api_key(
    request: CreateApiKeyRequest,
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key (admin only)."""
    raw_key, key_id = await AuthService.create_key(
        name=request.name,
        db=db,
        user_id=request.user_id,
        username=request.username,
        permissions=request.permissions,
        is_admin=request.is_admin,
    )

    return CreateApiKeyResponse(
        key=raw_key,
        key_id=key_id,
        message="API key created successfully. Store this key securely - it won't be shown again.",
    )


@router.delete("/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key (admin only)."""
    # Prevent revoking your own key
    if user.api_key_id == key_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot revoke your own API key",
        )

    if await AuthService.revoke_key(key_id, db):
        return {"message": "API key revoked successfully"}
    else:
        raise HTTPException(
            status_code=404,
            detail="API key not found",
        )

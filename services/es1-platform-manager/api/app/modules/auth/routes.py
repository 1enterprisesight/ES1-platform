"""Authentication routes."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import (
    AuthService,
    UserContext,
    get_current_user,
    require_admin,
)
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


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


class MeResponse(BaseModel):
    """Current user information."""
    api_key_id: str | None
    user_id: str | None
    username: str | None
    permissions: list[str]
    is_admin: bool


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
async def list_api_keys(user: UserContext = Depends(require_admin)):
    """List all API keys (admin only)."""
    keys = AuthService.list_keys()
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
):
    """Create a new API key (admin only)."""
    raw_key, key_id = AuthService.create_key(
        name=request.name,
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
):
    """Revoke an API key (admin only)."""
    # Prevent revoking your own key
    if user.api_key_id == key_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot revoke your own API key",
        )

    if AuthService.revoke_key(key_id):
        return {"message": "API key revoked successfully"}
    else:
        raise HTTPException(
            status_code=404,
            detail="API key not found",
        )


@router.get("/status")
async def auth_status():
    """Get authentication status."""
    return {
        "auth_required": settings.AUTH_REQUIRED,
        "message": "Authentication is enabled" if settings.AUTH_REQUIRED else "Authentication is disabled (dev mode)",
    }

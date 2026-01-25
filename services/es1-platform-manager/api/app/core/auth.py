"""Authentication and authorization middleware."""
import hashlib
import secrets
from datetime import datetime
from typing import Any
from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserContext(BaseModel):
    """User context for authenticated requests."""
    api_key_id: str | None = None
    user_id: str | None = None
    username: str | None = None
    permissions: list[str] = []
    is_admin: bool = False


# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (raw_key, hashed_key)
    """
    raw_key = f"es1_{secrets.token_urlsafe(32)}"
    hashed = hash_api_key(raw_key)
    return raw_key, hashed


class AuthService:
    """Service for authentication operations."""

    # In-memory store for development (replace with database in production)
    _api_keys: dict[str, dict[str, Any]] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """Initialize default API keys for development."""
        if cls._initialized:
            return

        # Create a default admin key for development
        default_key = settings.DEFAULT_API_KEY
        if default_key:
            cls._api_keys[hash_api_key(default_key)] = {
                "id": "default-admin",
                "name": "Default Admin Key",
                "user_id": "admin",
                "username": "admin",
                "permissions": ["*"],
                "is_admin": True,
                "created_at": datetime.utcnow().isoformat(),
            }
            logger.info("Default admin API key configured")

        cls._initialized = True

    @classmethod
    def validate_key(cls, api_key: str) -> UserContext | None:
        """
        Validate an API key and return user context.

        Args:
            api_key: The raw API key

        Returns:
            UserContext if valid, None otherwise
        """
        if not api_key:
            return None

        hashed = hash_api_key(api_key)
        key_data = cls._api_keys.get(hashed)

        if not key_data:
            return None

        return UserContext(
            api_key_id=key_data["id"],
            user_id=key_data.get("user_id"),
            username=key_data.get("username"),
            permissions=key_data.get("permissions", []),
            is_admin=key_data.get("is_admin", False),
        )

    @classmethod
    def create_key(
        cls,
        name: str,
        user_id: str | None = None,
        username: str | None = None,
        permissions: list[str] | None = None,
        is_admin: bool = False,
    ) -> tuple[str, str]:
        """
        Create a new API key.

        Args:
            name: Key name/description
            user_id: Associated user ID
            username: Associated username
            permissions: List of permissions
            is_admin: Whether this is an admin key

        Returns:
            Tuple of (raw_key, key_id)
        """
        raw_key, hashed = generate_api_key()
        key_id = secrets.token_urlsafe(8)

        cls._api_keys[hashed] = {
            "id": key_id,
            "name": name,
            "user_id": user_id,
            "username": username,
            "permissions": permissions or [],
            "is_admin": is_admin,
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Created API key: {name} (id: {key_id})")
        return raw_key, key_id

    @classmethod
    def revoke_key(cls, key_id: str) -> bool:
        """
        Revoke an API key by ID.

        Args:
            key_id: The key ID to revoke

        Returns:
            True if revoked, False if not found
        """
        for hashed, data in list(cls._api_keys.items()):
            if data["id"] == key_id:
                del cls._api_keys[hashed]
                logger.info(f"Revoked API key: {key_id}")
                return True
        return False

    @classmethod
    def list_keys(cls) -> list[dict[str, Any]]:
        """List all API keys (without the actual keys)."""
        return [
            {
                "id": data["id"],
                "name": data["name"],
                "user_id": data.get("user_id"),
                "username": data.get("username"),
                "permissions": data.get("permissions", []),
                "is_admin": data.get("is_admin", False),
                "created_at": data.get("created_at"),
            }
            for data in cls._api_keys.values()
        ]


# Initialize on module load
AuthService.initialize()


async def get_optional_user(
    api_key: str | None = Depends(api_key_header),
) -> UserContext | None:
    """
    Get user context if authenticated, None otherwise.

    Use this for endpoints that optionally require authentication.
    """
    if not api_key:
        return None
    return AuthService.validate_key(api_key)


async def get_current_user(
    api_key: str | None = Depends(api_key_header),
) -> UserContext:
    """
    Get current authenticated user.

    Raises HTTPException if not authenticated.
    """
    if not settings.AUTH_REQUIRED:
        # Return a default context if auth is disabled
        return UserContext(
            user_id="anonymous",
            username="anonymous",
            permissions=["*"],
            is_admin=True,
        )

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    user = AuthService.validate_key(api_key)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    return user


async def require_admin(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    """
    Require admin privileges.

    Raises HTTPException if not admin.
    """
    if not user.is_admin and "*" not in user.permissions:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required",
        )
    return user


def require_permission(permission: str):
    """
    Create a dependency that requires a specific permission.

    Usage:
        @router.post("/deploy", dependencies=[Depends(require_permission("gateway.deploy"))])
    """
    async def check_permission(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if user.is_admin or "*" in user.permissions:
            return user
        if permission not in user.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {permission}",
            )
        return user

    return check_permission

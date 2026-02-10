"""Authentication and authorization — database-backed with in-memory cache."""
import asyncio
import hashlib
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
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
    """Generate a new API key. Returns (raw_key, hashed_key)."""
    prefix = settings.API_KEY_PREFIX or "pk"
    raw_key = f"{prefix}_{secrets.token_urlsafe(32)}"
    hashed = hash_api_key(raw_key)
    return raw_key, hashed


class AuthService:
    """
    Database-backed authentication service with per-pod read-through cache.

    Storage: audit.api_keys table (created by V002 migration).
    Cache: 60s TTL per-pod cache to reduce DB load. Source of truth is always
    PostgreSQL, which all pods share.

    The audit.api_keys table MUST exist before the service starts. If it
    doesn't, initialization fails loudly — this is a deployment error, not
    something to silently degrade around.
    """

    _initialized: bool = False

    # Per-pod cache: key_hash -> (UserContext, expiry_timestamp)
    _cache: dict[str, tuple[UserContext, float]] = {}
    _CACHE_TTL: int = 60

    @classmethod
    async def initialize(cls, db: AsyncSession):
        """
        Initialize AuthService. Verifies audit.api_keys table exists
        and seeds the DEFAULT_API_KEY if configured.

        Raises RuntimeError if the required table is missing.
        """
        if cls._initialized:
            return

        # Verify audit.api_keys table exists — hard fail if not
        try:
            await db.execute(text("SELECT 1 FROM audit.api_keys LIMIT 0"))
        except Exception as e:
            raise RuntimeError(
                "AuthService: audit.api_keys table does not exist. "
                "Run db-migrate before starting the platform. "
                f"Original error: {e}"
            ) from e

        logger.info("AuthService: database-backed key storage verified (audit.api_keys)")

        # Seed DEFAULT_API_KEY if configured
        default_key = settings.DEFAULT_API_KEY
        if default_key:
            await cls._seed_default_key(default_key, db)
        elif settings.auth_enabled:
            logger.warning(
                "AuthService: AUTH_MODE=%s but DEFAULT_API_KEY is empty. "
                "Generate credentials with: ./scripts/generate-credentials.sh",
                settings.AUTH_MODE,
            )

        cls._initialized = True

    @classmethod
    async def _seed_default_key(cls, default_key: str, db: AsyncSession):
        """Seed the DEFAULT_API_KEY into audit.api_keys if not already present."""
        key_hash = hash_api_key(default_key)
        key_prefix = default_key[:8]

        result = await db.execute(
            text("SELECT id FROM audit.api_keys WHERE key_hash = :hash"),
            {"hash": key_hash},
        )
        if not result.scalar():
            await db.execute(
                text("""
                    INSERT INTO audit.api_keys
                        (name, key_hash, key_prefix, service_name, scopes,
                         is_active, created_by, metadata)
                    VALUES
                        (:name, :hash, :prefix, :service, :scopes::jsonb,
                         true, :created_by, :metadata::jsonb)
                """),
                {
                    "name": "Default Admin Key",
                    "hash": key_hash,
                    "prefix": key_prefix,
                    "service": "platform-manager",
                    "scopes": '["*"]',
                    "created_by": "system",
                    "metadata": json.dumps({
                        "user_id": "admin",
                        "username": "admin",
                        "is_admin": True,
                    }),
                },
            )
            await db.commit()
            logger.info("Default admin API key seeded into database")
        else:
            logger.info("Default admin API key already exists in database")

    # ── Cache helpers ──────────────────────────────────────────────────

    @classmethod
    def _get_cached(cls, key_hash: str) -> UserContext | None:
        entry = cls._cache.get(key_hash)
        if entry and entry[1] > time.time():
            return entry[0]
        if entry:
            del cls._cache[key_hash]
        return None

    @classmethod
    def _set_cached(cls, key_hash: str, user: UserContext):
        cls._cache[key_hash] = (user, time.time() + cls._CACHE_TTL)

    @classmethod
    def _invalidate_cache(cls, key_hash: str | None = None):
        if key_hash:
            cls._cache.pop(key_hash, None)
        else:
            cls._cache.clear()

    # ── Core operations ────────────────────────────────────────────────

    @classmethod
    async def validate_key(cls, api_key: str, db: AsyncSession) -> UserContext | None:
        """Validate an API key against the database. Returns UserContext if valid."""
        if not api_key:
            return None

        key_hash = hash_api_key(api_key)

        # Check per-pod cache first
        cached = cls._get_cached(key_hash)
        if cached is not None:
            return cached

        # Query database (source of truth)
        result = await db.execute(
            text("""
                SELECT id, name, scopes, is_active, expires_at, metadata
                FROM audit.api_keys
                WHERE key_hash = :hash
            """),
            {"hash": key_hash},
        )
        row = result.mappings().first()

        if not row or not row["is_active"]:
            return None

        # Check expiration
        if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
            return None

        metadata = row["metadata"] or {}
        scopes = row["scopes"] or []
        is_admin = metadata.get("is_admin", False) or "*" in scopes

        user = UserContext(
            api_key_id=str(row["id"]),
            user_id=metadata.get("user_id"),
            username=metadata.get("username"),
            permissions=scopes,
            is_admin=is_admin,
        )

        cls._set_cached(key_hash, user)

        # Fire-and-forget: update last_used_at in a separate session
        asyncio.create_task(cls._update_last_used(key_hash))

        return user

    @classmethod
    async def _update_last_used(cls, key_hash: str):
        """Background task to update last_used_at timestamp."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("UPDATE audit.api_keys SET last_used_at = NOW() WHERE key_hash = :hash"),
                    {"hash": key_hash},
                )
                await session.commit()
        except Exception:
            pass  # Non-critical — don't fail requests over usage tracking

    @classmethod
    async def create_key(
        cls,
        name: str,
        db: AsyncSession,
        user_id: str | None = None,
        username: str | None = None,
        permissions: list[str] | None = None,
        is_admin: bool = False,
    ) -> tuple[str, str]:
        """Create a new API key in the database. Returns (raw_key, key_id)."""
        raw_key, key_hash = generate_api_key()
        key_prefix = raw_key[:8]
        perms = permissions or []

        result = await db.execute(
            text("""
                INSERT INTO audit.api_keys
                    (name, key_hash, key_prefix, service_name, scopes,
                     is_active, created_by, metadata)
                VALUES
                    (:name, :hash, :prefix, :service, :scopes::jsonb,
                     true, :created_by, :metadata::jsonb)
                RETURNING id
            """),
            {
                "name": name,
                "hash": key_hash,
                "prefix": key_prefix,
                "service": "platform-manager",
                "scopes": json.dumps(perms),
                "created_by": username or "system",
                "metadata": json.dumps({
                    "user_id": user_id,
                    "username": username,
                    "is_admin": is_admin,
                }),
            },
        )
        row = result.fetchone()
        await db.commit()
        key_id = str(row[0])
        logger.info(f"Created API key: {name} (id: {key_id})")
        return raw_key, key_id

    @classmethod
    async def revoke_key(cls, key_id: str, db: AsyncSession) -> bool:
        """Revoke an API key by ID. Returns True if revoked."""
        result = await db.execute(
            text("""
                UPDATE audit.api_keys SET is_active = false
                WHERE id = CAST(:id AS uuid) AND is_active = true
            """),
            {"id": key_id},
        )
        await db.commit()
        if result.rowcount > 0:
            cls._invalidate_cache()
            logger.info(f"Revoked API key: {key_id}")
            return True
        return False

    @classmethod
    async def list_keys(cls, db: AsyncSession) -> list[dict[str, Any]]:
        """List all active API keys (without the actual key values)."""
        result = await db.execute(
            text("""
                SELECT id, name, key_prefix, service_name, scopes,
                       is_active, expires_at, last_used_at, created_at, metadata
                FROM audit.api_keys
                WHERE is_active = true
                ORDER BY created_at DESC
            """)
        )
        rows = result.mappings().all()
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "key_prefix": r["key_prefix"],
                "service_name": r["service_name"],
                "user_id": (r["metadata"] or {}).get("user_id"),
                "username": (r["metadata"] or {}).get("username"),
                "permissions": r["scopes"] or [],
                "is_admin": (r["metadata"] or {}).get("is_admin", False),
                "last_used_at": r["last_used_at"].isoformat() if r["last_used_at"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]


# ── FastAPI Dependencies ───────────────────────────────────────────────


async def get_optional_user(
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> UserContext | None:
    """Get user context if authenticated, None otherwise."""
    if not api_key:
        return None
    return await AuthService.validate_key(api_key, db)


async def get_current_user(
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """Get current authenticated user. Raises 401 if not authenticated."""
    if not settings.auth_enabled:
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

    user = await AuthService.validate_key(api_key, db)
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
    """Require admin privileges. Raises 403 if not admin."""
    if not user.is_admin and "*" not in user.permissions:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required",
        )
    return user


def require_permission(permission: str):
    """Create a dependency that requires a specific permission."""
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

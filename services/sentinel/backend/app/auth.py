"""Authentication: password hashing, sessions, request middleware."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
from fastapi import Request, HTTPException
from pydantic import BaseModel

from app.config import JWT_SECRET, SESSION_EXPIRY_HOURS, ADMIN_EMAIL, ADMIN_PASSWORD
from app.database import get_pool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# Session tokens — HMAC-signed, non-guessable
# ---------------------------------------------------------------------------

def _create_token() -> str:
    raw = secrets.token_urlsafe(32)
    sig = hmac.new(JWT_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{raw}.{sig}"


def _verify_token(token: str) -> bool:
    parts = token.split(".")
    if len(parts) != 2:
        return False
    raw, sig = parts
    expected = hmac.new(JWT_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(sig, expected)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    role: str = "user"
    status: str = "pending"
    created_at: Optional[datetime] = None


class SessionInfo(BaseModel):
    user: User
    session_id: str
    workspace_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

async def bootstrap_admin():
    """Create the admin user from env vars if it doesn't exist."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT id FROM sentinel.users WHERE email = $1", ADMIN_EMAIL
    )
    if row:
        logger.info(f"Admin user already exists: {ADMIN_EMAIL}")
        return

    pw_hash = hash_password(ADMIN_PASSWORD)
    await pool.execute(
        """INSERT INTO sentinel.users (email, password_hash, display_name, role, status)
           VALUES ($1, $2, $3, 'admin', 'active')""",
        ADMIN_EMAIL, pw_hash, "Admin",
    )
    logger.info(f"Admin user created: {ADMIN_EMAIL}")


async def authenticate(email: str, password: str) -> Optional[User]:
    """Verify email/password, return User or None."""
    pool = get_pool()
    row = await pool.fetchrow(
        """SELECT id, email, display_name, role, status, password_hash
           FROM sentinel.users WHERE email = $1""",
        email,
    )
    if not row:
        return None
    if row["status"] != "active":
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return User(
        id=str(row["id"]),
        email=row["email"],
        display_name=row["display_name"],
        role=row["role"],
        status=row["status"],
    )


async def create_session(user_id: str) -> tuple[str, str]:
    """Create a new session, return (token, session_id)."""
    pool = get_pool()
    token = _create_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS)
    row = await pool.fetchrow(
        """INSERT INTO sentinel.sessions (user_id, token, expires_at)
           VALUES ($1, $2, $3)
           RETURNING id""",
        uuid.UUID(user_id), token, expires,
    )
    return token, str(row["id"])


async def validate_session(token: str) -> Optional[SessionInfo]:
    """Validate a session token, return SessionInfo or None."""
    if not token or not _verify_token(token):
        return None
    pool = get_pool()
    row = await pool.fetchrow(
        """SELECT s.id as session_id, s.workspace_id, u.id, u.email, u.display_name, u.role, u.status
           FROM sentinel.sessions s
           JOIN sentinel.users u ON u.id = s.user_id
           WHERE s.token = $1 AND s.expires_at > now()""",
        token,
    )
    if not row:
        return None
    return SessionInfo(
        user=User(
            id=str(row["id"]),
            email=row["email"],
            display_name=row["display_name"],
            role=row["role"],
            status=row["status"],
        ),
        session_id=str(row["session_id"]),
        workspace_id=str(row["workspace_id"]) if row["workspace_id"] else None,
    )


async def delete_session(token: str):
    """Delete a session (logout)."""
    pool = get_pool()
    await pool.execute("DELETE FROM sentinel.sessions WHERE token = $1", token)


async def get_current_user(request: Request) -> Optional[SessionInfo]:
    """Extract session from cookie or Authorization header."""
    token = request.cookies.get("sentinel_session")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        return None
    return await validate_session(token)


async def require_user(request: Request) -> SessionInfo:
    """Dependency: require authenticated user or raise 401."""
    session = await get_current_user(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session


async def require_admin(request: Request) -> SessionInfo:
    """Dependency: require admin user or raise 403."""
    session = await require_user(request)
    if session.user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return session


# ---------------------------------------------------------------------------
# User CRUD (admin)
# ---------------------------------------------------------------------------

async def list_users() -> list[User]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT id, email, display_name, role, status, created_at
           FROM sentinel.users ORDER BY created_at DESC"""
    )
    return [
        User(
            id=str(r["id"]), email=r["email"], display_name=r["display_name"],
            role=r["role"], status=r["status"], created_at=r["created_at"],
        )
        for r in rows
    ]


async def update_user_status(user_id: str, status: str) -> Optional[User]:
    pool = get_pool()
    row = await pool.fetchrow(
        """UPDATE sentinel.users SET status = $1, updated_at = now()
           WHERE id = $2
           RETURNING id, email, display_name, role, status, created_at""",
        status, uuid.UUID(user_id),
    )
    if not row:
        return None
    return User(
        id=str(row["id"]), email=row["email"], display_name=row["display_name"],
        role=row["role"], status=row["status"], created_at=row["created_at"],
    )


async def update_user_role(user_id: str, role: str) -> Optional[User]:
    pool = get_pool()
    row = await pool.fetchrow(
        """UPDATE sentinel.users SET role = $1, updated_at = now()
           WHERE id = $2
           RETURNING id, email, display_name, role, status, created_at""",
        role, uuid.UUID(user_id),
    )
    if not row:
        return None
    return User(
        id=str(row["id"]), email=row["email"], display_name=row["display_name"],
        role=row["role"], status=row["status"], created_at=row["created_at"],
    )


async def delete_user(user_id: str) -> bool:
    pool = get_pool()
    result = await pool.execute(
        "DELETE FROM sentinel.users WHERE id = $1", uuid.UUID(user_id)
    )
    return result == "DELETE 1"


async def register_user(email: str, password: str, display_name: str = None) -> User:
    """Register a new user (status=pending, needs admin approval)."""
    pool = get_pool()
    # Check if email already taken
    existing = await pool.fetchrow(
        "SELECT id FROM sentinel.users WHERE email = $1", email
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = hash_password(password)
    row = await pool.fetchrow(
        """INSERT INTO sentinel.users (email, password_hash, display_name, status)
           VALUES ($1, $2, $3, 'pending')
           RETURNING id, email, display_name, role, status, created_at""",
        email, pw_hash, display_name or email.split("@")[0],
    )
    return User(
        id=str(row["id"]), email=row["email"], display_name=row["display_name"],
        role=row["role"], status=row["status"], created_at=row["created_at"],
    )

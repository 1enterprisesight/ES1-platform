"""Auth routes: login, register, logout, user management."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import (
    authenticate, create_session, delete_session, require_user, require_admin,
    register_user, list_users, update_user_status, update_user_role, delete_user,
    SessionInfo,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = None


class UserStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(active|disabled|pending|verified)$")


class UserRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(user|admin)$")


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@router.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    user = await authenticate(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = await create_session(user.id)

    # Ensure user has a default workspace and link it to the session
    from app.routes.workspaces import ensure_default_workspace, set_session_workspace
    ws = await ensure_default_workspace(user.id)
    await set_session_workspace(token, ws["id"])

    response.set_cookie(
        key="sentinel_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production with HTTPS
        max_age=72 * 3600,
        path="/",
    )
    return {"user": user.model_dump(), "token": token, "workspace": ws}


@router.post("/auth/register")
async def register(body: RegisterRequest):
    user = await register_user(body.email, body.password, body.display_name)

    # Send verification email if SMTP configured
    from app.email import is_email_configured, send_verification_email
    email_sent = False
    if is_email_configured():
        import secrets
        from datetime import datetime, timezone, timedelta
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        pool = __import__("app.database", fromlist=["get_pool"]).get_pool()
        await pool.execute(
            "UPDATE sentinel.users SET email_token = $1, email_token_expires_at = $2 WHERE id = $3",
            token, expires, __import__("uuid").UUID(user.id),
        )
        email_sent = send_verification_email(user.email, token)

    msg = "Registration successful. "
    if email_sent:
        msg += "Check your email to verify your account."
    else:
        msg += "An admin must approve your account before you can log in."

    return {"user": user.model_dump(), "message": msg}


class VerifyRequest(BaseModel):
    token: str


@router.post("/auth/verify")
async def verify_email(body: VerifyRequest):
    """Verify email address using token from verification email."""
    pool = __import__("app.database", fromlist=["get_pool"]).get_pool()
    row = await pool.fetchrow(
        """UPDATE sentinel.users
           SET status = 'verified', email_token = NULL, email_token_expires_at = NULL, updated_at = now()
           WHERE email_token = $1 AND email_token_expires_at > now() AND status = 'pending'
           RETURNING id, email""",
        body.token,
    )
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    return {"ok": True, "email": row["email"]}


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Send password reset email (if SMTP configured)."""
    from app.email import is_email_configured, send_password_reset_email
    if not is_email_configured():
        raise HTTPException(status_code=400, detail="Email not configured. Contact an admin to reset your password.")

    pool = __import__("app.database", fromlist=["get_pool"]).get_pool()
    row = await pool.fetchrow("SELECT id FROM sentinel.users WHERE email = $1", body.email)
    # Always return success to prevent email enumeration
    if row:
        import secrets
        from datetime import datetime, timezone, timedelta
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await pool.execute(
            "UPDATE sentinel.users SET reset_token = $1, reset_token_expires_at = $2 WHERE id = $3",
            token, expires, row["id"],
        )
        send_password_reset_email(body.email, token)
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)


@router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Reset password using token from email."""
    from app.auth import hash_password
    pool = __import__("app.database", fromlist=["get_pool"]).get_pool()
    row = await pool.fetchrow(
        """UPDATE sentinel.users
           SET password_hash = $1, reset_token = NULL, reset_token_expires_at = NULL, updated_at = now()
           WHERE reset_token = $2 AND reset_token_expires_at > now()
           RETURNING id""",
        hash_password(body.password), body.token,
    )
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return {"ok": True}


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("sentinel_session")
    if token:
        await delete_session(token)
    response.delete_cookie("sentinel_session", path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(session: SessionInfo = Depends(require_user)):
    # Ensure workspace exists and return it
    from app.routes.workspaces import ensure_default_workspace
    ws = None
    if session.workspace_id:
        pool = __import__("app.database", fromlist=["get_pool"]).get_pool()
        row = await pool.fetchrow(
            "SELECT * FROM sentinel.workspaces WHERE id = $1",
            __import__("uuid").UUID(session.workspace_id),
        )
        if row:
            from app.routes.workspaces import _row_to_dict
            ws = _row_to_dict(row)
    if not ws:
        ws = await ensure_default_workspace(session.user.id)
    return {"user": session.user.model_dump(), "workspace": ws}


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@router.get("/admin/users")
async def admin_list_users(session: SessionInfo = Depends(require_admin)):
    users = await list_users()
    return {"users": [u.model_dump() for u in users]}


@router.patch("/admin/users/{user_id}/status")
async def admin_update_status(
    user_id: str,
    body: UserStatusRequest,
    session: SessionInfo = Depends(require_admin),
):
    user = await update_user_status(user_id, body.status)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user.model_dump()}


@router.patch("/admin/users/{user_id}/role")
async def admin_update_role(
    user_id: str,
    body: UserRoleRequest,
    session: SessionInfo = Depends(require_admin),
):
    user = await update_user_role(user_id, body.role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user.model_dump()}


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: str,
    session: SessionInfo = Depends(require_admin),
):
    if user_id == session.user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    deleted = await delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}

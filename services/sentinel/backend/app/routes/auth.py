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
    return {
        "user": user.model_dump(),
        "message": "Registration successful. An admin must approve your account before you can log in.",
    }


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

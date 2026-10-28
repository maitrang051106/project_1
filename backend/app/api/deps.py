from fastapi import Cookie, Depends, Header, HTTPException, Request, WebSocket, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.enums import UserStatus
from app.models.user import User
from app.services.store import store_service


def get_client_ip(request: Request | WebSocket) -> str:
    """Extract client IP safely from trusted reverse proxy or direct socket."""
    trusted = [
        p.strip() for p in getattr(settings, "trusted_proxies", "127.0.0.1,::1").split(",")
    ]
    client_host = request.client.host if request.client else "127.0.0.1"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for and (client_host in trusted or "127.0.0.1" in trusted):
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    return client_host


def is_allowed_websocket_origin(origin: str | None) -> bool:
    return origin is not None and origin in settings.allowed_origins


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = access_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user information",
        )

    jti = payload.get("jti")
    if not jti or not await store_service.is_session_active(user_id, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked or expired",
        )

    stmt = select(User).where(User.id == user_id).options(selectinload(User.profile))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account does not exist",
        )

    if user.status == UserStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended",
        )

    return user

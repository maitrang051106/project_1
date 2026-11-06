import asyncio
from collections import deque
import json
import logging
import time
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, is_allowed_websocket_origin
from app.core.constants import (
    DEFAULT_AVATAR,
    MAX_DIRECT_MESSAGE_LENGTH,
    MAX_WS_CONNECTIONS_PER_IP,
    MAX_WS_CONNECTIONS_PER_USER,
)
from app.core.db import SessionLocal, get_db
from app.core.security import decode_access_token
from app.models.direct_message import DirectMessage
from app.models.enums import UserStatus
from app.models.friendship import Friendship
from app.models.user import User
from app.services.store import store_service

logger = logging.getLogger(__name__)

WS_RATE_LIMIT_MESSAGES = 5
WS_RATE_LIMIT_WINDOW_SECONDS = 3.0

router = APIRouter(tags=["direct_messages"])


@router.get("/friends")
async def get_friends(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return paginated friends of the current user with their latest message info.
    Eliminates N+1 queries by using a single window function SQL query.
    """
    partner_id_expr = case(
        (DirectMessage.sender_id == user.id, DirectMessage.receiver_id),
        else_=DirectMessage.sender_id,
    ).label("partner_id")

    # Subquery: Rank direct messages involving current user by created_at desc per partner
    subq = (
        select(
            DirectMessage.content.label("last_msg_content"),
            DirectMessage.created_at.label("last_msg_at"),
            partner_id_expr,
            func.row_number().over(
                partition_by=partner_id_expr,
                order_by=(DirectMessage.created_at.desc(), DirectMessage.id.desc()),
            ).label("rn"),
        )
        .where(or_(DirectMessage.sender_id == user.id, DirectMessage.receiver_id == user.id))
        .subquery()
    )

    friend_id_expr = case(
        (Friendship.user_a == user.id, Friendship.user_b),
        else_=Friendship.user_a,
    ).label("friend_id")

    # Main query joining Friendship, User, and the ranked latest message subquery
    stmt = (
        select(
            User,
            subq.c.last_msg_content,
            subq.c.last_msg_at,
        )
        .select_from(Friendship)
        .join(
            User,
            User.id == friend_id_expr,
        )
        .outerjoin(
            subq,
            and_(
                subq.c.partner_id == User.id,
                subq.c.rn == 1,
            ),
        )
        .where(
            or_(Friendship.user_a == user.id, Friendship.user_b == user.id),
            Friendship.status == "accepted",
        )
        .order_by(func.coalesce(subq.c.last_msg_at, Friendship.created_at).desc())
        .offset(offset)
        .limit(limit + 1)
    )

    res = await db.execute(stmt)
    rows = res.all()

    has_more = len(rows) > limit
    paged_rows = rows[:limit]

    friends_data = [
        {
            "id": friend_user.id,
            "email": friend_user.email,
            "nickname": friend_user.nickname,
            "avatar": friend_user.avatar or DEFAULT_AVATAR,
            "last_message": last_msg_content,
            "last_message_at": last_msg_at.isoformat() if last_msg_at else None,
        }
        for friend_user, last_msg_content, last_msg_at in paged_rows
    ]

    return {
        "friends": friends_data,
        "has_more": has_more,
    }


@router.get("/messages/{friend_id}")
async def get_messages(
    friend_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    before_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve cursor-paginated direct message history between user and friend."""
    f_check = await db.execute(
        select(Friendship).where(
            and_(
                or_(
                    (Friendship.user_a == user.id) & (Friendship.user_b == friend_id),
                    (Friendship.user_a == friend_id) & (Friendship.user_b == user.id),
                ),
                Friendship.status == "accepted",
            )
        )
    )
    if not f_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view messages with accepted friends.",
        )

    stmt = (
        select(DirectMessage)
        .where(
            or_(
                and_(DirectMessage.sender_id == user.id, DirectMessage.receiver_id == friend_id),
                and_(DirectMessage.sender_id == friend_id, DirectMessage.receiver_id == user.id),
            )
        )
    )
    if before_id is not None:
        stmt = stmt.where(DirectMessage.id < before_id)

    stmt = stmt.order_by(DirectMessage.id.desc()).limit(limit + 1)
    res = await db.execute(stmt)
    messages = res.scalars().all()

    has_more = len(messages) > limit
    paged_messages = list(messages[:limit])
    # Reverse to chronological order (oldest -> newest) for display
    paged_messages.reverse()

    return {
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "receiver_id": m.receiver_id,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in paged_messages
        ],
        "has_more": has_more,
    }


@router.websocket("/ws/direct/{friend_id}")
async def direct_message_websocket(
    websocket: WebSocket,
    friend_id: int,
    token: str | None = Query(default=None),
) -> None:
    if not is_allowed_websocket_origin(websocket.headers.get("origin")):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    auth_token = token or websocket.cookies.get("access_token")
    if not auth_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(auth_token)
    if not payload or "sub" not in payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    jti = payload.get("jti")
    if not jti or not await store_service.is_session_active(user_id, jti):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Check friendship & user eligibility before acquiring any WS slot
    async with SessionLocal() as db:
        f_check = await db.execute(
            select(Friendship).where(
                and_(
                    or_(
                        (Friendship.user_a == user_id) & (Friendship.user_b == friend_id),
                        (Friendship.user_a == friend_id) & (Friendship.user_b == user_id),
                    ),
                    Friendship.status == "accepted",
                )
            )
        )
        if not f_check.scalar_one_or_none():
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        u_res = await db.execute(select(User).where(User.id == user_id))
        user = u_res.scalar_one_or_none()
        if (
            not user
            or user.status == UserStatus.BANNED
            or user.trust_score <= 0
        ):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        nickname = user.nickname
        avatar = user.avatar or DEFAULT_AVATAR

    # 3. Acquire WebSocket connection slot (guaranteed to be released in finally)
    client_ip = get_client_ip(websocket)
    slot_ok, slot_reason = await store_service.acquire_ws_slot(
        user_id=user_id,
        client_ip=client_ip,
        max_user=MAX_WS_CONNECTIONS_PER_USER,
        max_ip=MAX_WS_CONNECTIONS_PER_IP,
    )
    if not slot_ok:
        logger.warning("Rejecting direct WS for user %s: %s", user_id, slot_reason)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    room_key = f"dm_{min(user_id, friend_id)}_{max(user_id, friend_id)}"
    listener_queue = await store_service.subscribe_room(room_key)

    async def send_messages_to_client() -> None:
        try:
            while True:
                msg = await listener_queue.get()
                await websocket.send_text(json.dumps(msg))
        except (asyncio.CancelledError, Exception):
            pass

    send_task = asyncio.create_task(send_messages_to_client())
    message_timestamps: deque[float] = deque()

    try:
        while True:
            raw_text = await websocket.receive_text()
            stripped = raw_text.strip()
            if not stripped:
                continue

            now = time.time()
            while message_timestamps and message_timestamps[0] <= now - WS_RATE_LIMIT_WINDOW_SECONDS:
                message_timestamps.popleft()

            if len(message_timestamps) >= WS_RATE_LIMIT_MESSAGES:
                await websocket.send_text(
                    json.dumps({
                        "type": "error",
                        "message": "You are sending messages too quickly. Please wait a moment.",
                    })
                )
                continue

            message_timestamps.append(now)

            content = stripped[:MAX_DIRECT_MESSAGE_LENGTH]
            async with SessionLocal() as db:
                dm = DirectMessage(
                    sender_id=user_id,
                    receiver_id=friend_id,
                    content=content,
                )
                db.add(dm)
                await db.commit()
                await db.refresh(dm)

            msg_dict = {
                "type": "direct_message",
                "id": dm.id,
                "sender_id": dm.sender_id,
                "receiver_id": dm.receiver_id,
                "content": dm.content,
                "created_at": dm.created_at.isoformat(),
                "sender_name": nickname,
                "sender_avatar": avatar,
            }
            await store_service.broadcast_to_room(room_key, msg_dict)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("Direct WS error: %s", e)
    finally:
        send_task.cancel()
        await store_service.unsubscribe_room(room_key, listener_queue)
        await store_service.release_ws_slot(user_id=user_id, client_ip=client_ip)

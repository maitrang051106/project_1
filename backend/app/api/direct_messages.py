import asyncio
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
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.constants import DEFAULT_AVATAR, MAX_DIRECT_MESSAGE_LENGTH
from app.core.db import SessionLocal, get_db
from app.core.security import decode_access_token
from app.models.direct_message import DirectMessage
from app.models.friendship import Friendship
from app.models.user import User
from app.services.store import store_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["direct_messages"])


class SendDirectMessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_DIRECT_MESSAGE_LENGTH)


@router.get("/friends")
async def get_friends(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Return all accepted friends of the current user with latest message info."""
    stmt = select(Friendship).where(
        and_(
            or_(Friendship.user_a == user.id, Friendship.user_b == user.id),
            Friendship.status == "accepted",
        )
    )
    res = await db.execute(stmt)
    friendships = res.scalars().all()

    if not friendships:
        return []

    friend_ids = [
        f.user_b if f.user_a == user.id else f.user_a for f in friendships
    ]

    u_stmt = select(User).where(User.id.in_(friend_ids))
    u_res = await db.execute(u_stmt)
    friends_map = {u.id: u for u in u_res.scalars().all()}

    result = []
    for friend_id in friend_ids:
        friend_user = friends_map.get(friend_id)
        if not friend_user:
            continue

        # Get latest message
        msg_stmt = (
            select(DirectMessage)
            .where(
                or_(
                    and_(DirectMessage.sender_id == user.id, DirectMessage.receiver_id == friend_id),
                    and_(DirectMessage.sender_id == friend_id, DirectMessage.receiver_id == user.id),
                )
            )
            .order_by(desc(DirectMessage.created_at))
            .limit(1)
        )
        msg_res = await db.execute(msg_stmt)
        last_msg = msg_res.scalar_one_or_none()

        result.append(
            {
                "id": friend_user.id,
                "email": friend_user.email,
                "anon_name": friend_user.anon_name,
                "avatar": friend_user.avatar,
                "last_message": last_msg.content if last_msg else None,
                "last_message_at": last_msg.created_at.isoformat() if last_msg else None,
            }
        )

    # Sort friends by last message time (most recent first)
    result.sort(key=lambda x: x["last_message_at"] or "", reverse=True)
    return result


@router.get("/messages/{friend_id}")
async def get_messages(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve direct message history between user and friend."""
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
        .order_by(DirectMessage.created_at.asc())
    )
    res = await db.execute(stmt)
    messages = res.scalars().all()

    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "receiver_id": m.receiver_id,
            "content": m.content,
            "is_read": m.is_read,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/messages/{friend_id}")
async def send_direct_message(
    friend_id: int,
    payload: SendDirectMessageIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Send a direct message to a friend and broadcast via Redis/In-memory store."""
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
            detail="You can only send messages to accepted friends.",
        )

    dm = DirectMessage(
        sender_id=user.id,
        receiver_id=friend_id,
        content=payload.content.strip(),
    )
    db.add(dm)
    await db.commit()
    await db.refresh(dm)

    room_key = f"dm_{min(user.id, friend_id)}_{max(user.id, friend_id)}"
    msg_dict = {
        "type": "direct_message",
        "id": dm.id,
        "sender_id": dm.sender_id,
        "receiver_id": dm.receiver_id,
        "content": dm.content,
        "created_at": dm.created_at.isoformat(),
        "sender_name": user.anon_name,
        "sender_avatar": user.avatar,
    }
    await store_service.broadcast_to_room(room_key, msg_dict)

    return msg_dict


@router.websocket("/ws/direct/{friend_id}")
async def direct_message_websocket(
    websocket: WebSocket,
    friend_id: int,
    token: str | None = Query(default=None),
) -> None:
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
        anon_name = user.anon_name if user else "Friend"
        avatar = user.avatar if user else DEFAULT_AVATAR

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

    try:
        while True:
            raw_text = await websocket.receive_text()
            if not raw_text.strip():
                continue

            content = raw_text[:MAX_DIRECT_MESSAGE_LENGTH]
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
                "sender_name": anon_name,
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


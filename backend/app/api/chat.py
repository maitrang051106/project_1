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
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, is_allowed_websocket_origin
from app.core.config import settings
from app.core.constants import (
    DEFAULT_AVATAR,
    MAX_CHAT_MESSAGE_LENGTH,
    MAX_WS_CONNECTIONS_PER_IP,
    MAX_WS_CONNECTIONS_PER_USER,
)
from app.core.db import SessionLocal, get_db
from app.core.security import decode_access_token
from datetime import datetime, timezone
from app.models.conversation import Conversation
from app.models.enums import UserStatus
from app.models.friendship import Friendship
from app.models.user import User
from app.services.store import store_service

logger = logging.getLogger(__name__)

WS_RATE_LIMIT_MESSAGES = 5
WS_RATE_LIMIT_WINDOW_SECONDS = 3.0

router = APIRouter(tags=["chat"])


async def _transition_chat_to_dm(
    db: AsyncSession,
    room_id: int,
    user_id: int,
    opp_id: int,
    already_friends: bool = False,
) -> None:
    """Auto-end anonymous conversation and broadcast redirect to direct messages.
    Note: Anonymous chat messages remain ephemeral in Redis and are NOT migrated into direct_messages.
    """
    u_res = await db.execute(select(User).where(User.id.in_([user_id, opp_id])))
    users = {u.id: u for u in u_res.scalars().all()}
    u1 = users.get(user_id)
    u2 = users.get(opp_id)

    # Auto-end conversation in MySQL
    conv_res = await db.execute(
        select(Conversation).where(Conversation.id == room_id)
    )
    conv = conv_res.scalar_one_or_none()
    if conv and conv.ended_at is None:
        conv.ended_at = func.now()

    await db.commit()

    if u1 and u2:
        msg_text = (
            "You are already friends! Redirecting to private messages..."
            if already_friends
            else "You are now friends! Redirecting to private messages..."
        )
        await store_service.broadcast_to_room(
            room_id,
            {
                "type": "friend_accepted",
                "message": msg_text,
                "already_friends": already_friends,
                "user_a": {
                    "id": u1.id,
                    "email": u1.email,
                    "nickname": u1.nickname,
                    "avatar": u1.avatar,
                },
                "user_b": {
                    "id": u2.id,
                    "email": u2.email,
                    "nickname": u2.nickname,
                    "avatar": u2.avatar,
                },
                "timestamp": time.time(),
                "redirect_to_dm": True,
            },
        )
        async def _delayed_cancel() -> None:
            await asyncio.sleep(0.5)
            await store_service.cancel_room_pubsub(room_id)

        asyncio.create_task(_delayed_cancel())


async def _handle_ws_friend_request(
    user_id: int,
    opp_id: int,
    room_id: int,
    nickname: str,
    avatar: str,
) -> None:
    """Handle incoming friend request event over WebSocket."""
    lower_user_id = min(user_id, opp_id)
    upper_user_id = max(user_id, opp_id)
    async with SessionLocal() as db:
        f_check = await db.execute(
            select(Friendship)
            .where(
                (Friendship.user_a == lower_user_id)
                & (Friendship.user_b == upper_user_id)
            )
            .with_for_update()
        )
        friendship = f_check.scalar_one_or_none()

        # If already friends, immediately transition to existing direct messages!
        if friendship and friendship.status == "accepted":
            await _transition_chat_to_dm(
                db=db,
                room_id=room_id,
                user_id=user_id,
                opp_id=opp_id,
                already_friends=True,
            )
            return

        if friendship and friendship.status == "pending":
            if friendship.requested_by == opp_id:
                # The other user previously sent a request -> mutual acceptance!
                friendship.status = "accepted"
                await _transition_chat_to_dm(
                    db=db,
                    room_id=room_id,
                    user_id=user_id,
                    opp_id=opp_id,
                    already_friends=False,
                )
                return
            else:
                # Current user already requested, waiting for response
                return
        else:
            if friendship is None:
                friendship = Friendship(
                    user_a=lower_user_id,
                    user_b=upper_user_id,
                )
                db.add(friendship)
            friendship.requested_by = user_id
            friendship.status = "pending"
            await db.commit()

    await store_service.broadcast_to_room(
        room_id,
        {
            "type": "friend_request_received",
            "from_user_id": user_id,
            "from_name": nickname,
            "from_avatar": avatar,
            "timestamp": time.time(),
        },
    )


async def _handle_ws_friend_response(
    user_id: int,
    opp_id: int,
    room_id: int,
    data: dict[str, Any],
) -> None:
    """Handle acceptance/rejection of a friend request over WebSocket."""
    accepted = data.get("accepted")
    if not isinstance(accepted, bool):
        return

    lower_user_id = min(user_id, opp_id)
    upper_user_id = max(user_id, opp_id)

    async with SessionLocal() as db:
        f_check = await db.execute(
            select(Friendship)
            .where(
                (Friendship.user_a == lower_user_id)
                & (Friendship.user_b == upper_user_id)
            )
            .with_for_update()
        )
        friendship = f_check.scalar_one_or_none()
        if (
            not friendship
            or not friendship.can_be_responded_to_by(
                responder_id=user_id,
                requester_id=opp_id,
            )
        ):
            return

        friendship.status = "accepted" if accepted else "declined"
        if accepted:
            await _transition_chat_to_dm(
                db=db,
                room_id=room_id,
                user_id=user_id,
                opp_id=opp_id,
                already_friends=False,
            )
        else:
            await db.commit()
            await store_service.broadcast_to_room(
                room_id,
                {
                    "type": "friend_declined",
                    "from_user_id": user_id,
                    "message": "Friend request was declined.",
                    "timestamp": time.time(),
                },
            )


async def _get_conversation_meta_dict(
    conv: Conversation,
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Helper to extract participant metadata for an anonymous conversation."""
    opp_id = conv.user_b if conv.user_a == user_id else conv.user_a
    opp_res = await db.execute(select(User).where(User.id == opp_id))
    opp_user = opp_res.scalar_one_or_none()

    return {
        "room_id": conv.id,
        "started_at": conv.started_at.isoformat(),
        "ended_at": conv.ended_at.isoformat() if conv.ended_at else None,
        "opponent": {
            "id": opp_id,
            "nickname": opp_user.nickname if opp_user else "Anonymous Partner",
            "avatar": opp_user.avatar if opp_user else DEFAULT_AVATAR,
            "email": None,  # NEVER leak email in anonymous match chat
        },
    }


@router.websocket("/ws/{room_id}")
async def chat_websocket(
    websocket: WebSocket,
    room_id: int,
    token: str | None = Query(default=None),
) -> None:
    origin = websocket.headers.get("origin")
    if not is_allowed_websocket_origin(origin):
        logger.warning("[WS REJECT] origin '%s' not allowed in %s", origin, settings.allowed_origins)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 1. Authenticate user from JWT token
    auth_token = token or websocket.cookies.get("access_token")
    if not auth_token:
        logger.warning("[WS REJECT] missing auth token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(auth_token)
    if not payload or "sub" not in payload:
        logger.warning("[WS REJECT] invalid payload: %s", payload)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        logger.warning("[WS REJECT] sub not int: %s", payload.get("sub"))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    jti = payload.get("jti")
    if not jti or not await store_service.is_session_active(user_id, jti):
        logger.warning("[WS REJECT] session not active: user_id=%s, jti=%s", user_id, jti)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Check room membership & user validity before acquiring any WS slot
    async with SessionLocal() as db:
        stmt = select(Conversation).where(Conversation.id == room_id)
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()

        if not conv or (conv.user_a != user_id and conv.user_b != user_id):
            logger.warning("[WS REJECT] not participant in room %s: user_id=%s, conv=%s", room_id, user_id, conv)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if conv.ended_at is not None:
            logger.warning("[WS REJECT] room %s ended at %s", room_id, conv.ended_at)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        opp_id = conv.user_b if conv.user_a == user_id else conv.user_a
        users_res = await db.execute(select(User).where(User.id.in_([user_id, opp_id])))
        users_map = {u.id: u for u in users_res.scalars().all()}

        current_user = users_map.get(user_id)
        opp_user = users_map.get(opp_id)

        if (
            not current_user
            or current_user.status == UserStatus.BANNED
            or current_user.trust_score <= 0
        ):
            logger.warning("[WS REJECT] user status/trust invalid: %s", current_user)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        nickname = current_user.nickname if current_user else "You"
        avatar = current_user.avatar if current_user else DEFAULT_AVATAR

    # 3. Acquire WebSocket connection slot (guaranteed to be released in finally)
    client_ip = get_client_ip(websocket)
    slot_ok, slot_reason = await store_service.acquire_ws_slot(
        user_id=user_id,
        client_ip=client_ip,
        max_user=MAX_WS_CONNECTIONS_PER_USER,
        max_ip=MAX_WS_CONNECTIONS_PER_IP,
    )
    if not slot_ok:
        logger.warning("[WS REJECT] chat websocket for user %s: %s", user_id, slot_reason)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # Send room initialization data to the connected client (never leak email in anonymous room)
    await websocket.send_text(
        json.dumps(
            {
                "type": "room_info",
                "room_id": room_id,
                "user_id": user_id,
                "opponent": {
                    "id": opp_user.id if opp_user else opp_id,
                    "nickname": opp_user.nickname if opp_user else "Partner",
                    "avatar": opp_user.avatar if opp_user else DEFAULT_AVATAR,
                    "email": None,
                },
            }
        )
    )

    listener_queue = await store_service.subscribe_room(room_id)

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
            if not raw_text.strip():
                continue

            # Check if this is a structured JSON event or a regular message
            is_json = False
            data = None
            if raw_text.startswith("{") and raw_text.endswith("}"):
                try:
                    data = json.loads(raw_text)
                    is_json = True
                except Exception:
                    is_json = False

            if is_json and data and "type" in data:
                event_type = data["type"]

                if event_type == "friend_request":
                    try:
                        await _handle_ws_friend_request(
                            user_id=user_id,
                            opp_id=opp_id,
                            room_id=room_id,
                            nickname=nickname,
                            avatar=avatar,
                        )
                    except Exception as exc:
                        logger.exception("Error handling friend request: %s", exc)
                    continue

                elif event_type == "friend_response":
                    try:
                        await _handle_ws_friend_response(
                            user_id=user_id,
                            opp_id=opp_id,
                            room_id=room_id,
                            data=data,
                        )
                    except Exception as exc:
                        logger.exception("Error handling friend response: %s", exc)
                    continue

                elif event_type == "message":
                    content = str(data.get("content", ""))[:MAX_CHAT_MESSAGE_LENGTH]
                else:
                    continue
            else:
                # Standard text message
                content = raw_text[:MAX_CHAT_MESSAGE_LENGTH]

            if not content.strip():
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

            msg = {
                "type": "message",
                "sender_id": user_id,
                "sender_name": nickname,
                "sender_avatar": avatar,
                "content": content,
                "timestamp": time.time(),
            }
            await store_service.broadcast_to_room(room_id, msg)
            await store_service.append_chat_message(room_id, msg)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket error: %s", e)
    finally:
        send_task.cancel()
        # Unsubscribe this connection's queue from the room listener set.
        # The Redis pub/sub task for the room is kept alive so that reconnecting
        # users can re-subscribe seamlessly. It is torn down only when the room
        # is explicitly ended via end_conversation().
        await store_service.unsubscribe_room(room_id, listener_queue)
        await store_service.release_ws_slot(user_id=user_id, client_ip=client_ip)


@router.post("/conversations/{room_id}/end")
async def end_conversation(
    room_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(Conversation).where(Conversation.id == room_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv or (conv.user_a != user.id and conv.user_b != user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation.",
        )

    if conv.ended_at is None:
        conv.ended_at = func.now()
        await db.commit()

        # Fix 1: Only return structured domain data (ended_by, timestamp).
        # Presentation label is owned by the frontend.
        ended_msg = {
            "type": "ended",
            "ended_by": user.id,
            "timestamp": time.time(),
        }
        await store_service.broadcast_to_room(room_id, ended_msg)
        await store_service.append_chat_message(room_id, ended_msg)
        # Room is now permanently closed - tear down the pub/sub channel.
        async def _delayed_cancel() -> None:
            await asyncio.sleep(0.5)
            await store_service.cancel_room_pubsub(room_id)

        asyncio.create_task(_delayed_cancel())

    return {"message": "Conversation ended."}


@router.get("/conversations/{room_id}/init")
async def get_conversation_init(
    room_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    before_timestamp: float | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return atomic room metadata and paginated message history in a single round-trip."""
    stmt = select(Conversation).where(Conversation.id == room_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv or (conv.user_a != user.id and conv.user_b != user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation.",
        )

    meta = await _get_conversation_meta_dict(conv, user.id, db)
    paged_history = await store_service.get_chat_history_paginated(
        room_id, limit=limit, before_timestamp=before_timestamp
    )
    return {
        "meta": meta,
        "history": paged_history["messages"],
        "has_more": paged_history["has_more"],
    }


@router.get("/conversations/{room_id}/meta")
async def get_conversation_meta(
    room_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return basic metadata for a conversation room (active or ended)."""
    stmt = select(Conversation).where(Conversation.id == room_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv or (conv.user_a != user.id and conv.user_b != user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation.",
        )

    return await _get_conversation_meta_dict(conv, user.id, db)


@router.get("/conversations/{room_id}/history")
async def get_conversation_history(
    room_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    before_timestamp: float | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return paginated message history for a room. Accessible by participants only."""
    stmt = select(Conversation).where(Conversation.id == room_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv or (conv.user_a != user.id and conv.user_b != user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation.",
        )

    return await store_service.get_chat_history_paginated(
        room_id, limit=limit, before_timestamp=before_timestamp
    )

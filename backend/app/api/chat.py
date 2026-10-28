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
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, is_allowed_websocket_origin
from app.core.constants import (
    DEFAULT_AVATAR,
    MAX_CHAT_MESSAGE_LENGTH,
    MAX_WS_CONNECTIONS_PER_IP,
    MAX_WS_CONNECTIONS_PER_USER,
)
from app.core.db import SessionLocal, get_db
from app.core.security import decode_access_token
from app.models.conversation import Conversation
from app.models.enums import UserStatus
from app.models.friendship import Friendship
from app.models.user import User
from app.services.store import store_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.websocket("/ws/{room_id}")
async def chat_websocket(
    websocket: WebSocket,
    room_id: int,
    token: str | None = Query(default=None),
) -> None:
    if not is_allowed_websocket_origin(websocket.headers.get("origin")):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 1. Authenticate user from JWT token
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

    client_ip = get_client_ip(websocket)
    slot_ok, slot_reason = await store_service.acquire_ws_slot(
        user_id=user_id,
        client_ip=client_ip,
        max_user=MAX_WS_CONNECTIONS_PER_USER,
        max_ip=MAX_WS_CONNECTIONS_PER_IP,
    )
    if not slot_ok:
        logger.warning("Rejecting chat websocket for user %s: %s", user_id, slot_reason)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Check room membership
    async with SessionLocal() as db:
        stmt = select(Conversation).where(Conversation.id == room_id)
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()

        if not conv or (conv.user_a != user_id and conv.user_b != user_id):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if conv.ended_at is not None:
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
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        nickname = current_user.nickname if current_user else "You"
        avatar = current_user.avatar if current_user else DEFAULT_AVATAR

        # Check existing friendship
        f_stmt = select(Friendship).where(
            or_(
                (Friendship.user_a == user_id) & (Friendship.user_b == opp_id),
                (Friendship.user_a == opp_id) & (Friendship.user_b == user_id),
            )
        )
        f_res = await db.execute(f_stmt)
        friendship = f_res.scalar_one_or_none()
        is_friend = bool(friendship and friendship.status == "accepted")

    await websocket.accept()

    # Send room initialization data to the connected client
    await websocket.send_text(
        json.dumps(
            {
                "type": "room_info",
                "room_id": room_id,
                "user_id": user_id,
                "is_friend": is_friend,
                "opponent": {
                    "id": opp_user.id if opp_user else opp_id,
                    "nickname": opp_user.nickname if opp_user else "Partner",
                    "avatar": opp_user.avatar if opp_user else DEFAULT_AVATAR,
                    "email": opp_user.email if (is_friend and opp_user) else None,
                },
            }
        )
    )

    listener_queue = await store_service.subscribe_room(room_id)

    # Broadcast join
    await store_service.broadcast_to_room(
        room_id,
        {
            "type": "system",
            "content": f"{nickname} joined the chat",
            "timestamp": time.time(),
        },
    )

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
                        if friendship and friendship.status == "accepted":
                            continue
                        if friendship and friendship.status == "pending":
                            if friendship.requested_by != user_id:
                                continue
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
                elif event_type == "friend_response":
                    accepted = data.get("accepted")
                    if not isinstance(accepted, bool):
                        continue

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
                            continue

                        friendship.status = "accepted" if accepted else "declined"
                        if accepted:
                            u_res = await db.execute(
                                select(User).where(User.id.in_([user_id, opp_id]))
                            )
                            users = {u.id: u for u in u_res.scalars().all()}
                            u1 = users.get(user_id)
                            u2 = users.get(opp_id)
                        await db.commit()

                    if accepted and u1 and u2:
                        await store_service.broadcast_to_room(
                            room_id,
                            {
                                "type": "friend_accepted",
                                "message": "You are now friends! Real emails have been revealed.",
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
                            },
                        )
                    else:
                        await store_service.broadcast_to_room(
                            room_id,
                            {
                                "type": "friend_declined",
                                "from_user_id": user_id,
                                "message": "Friend request was declined.",
                                "timestamp": time.time(),
                            },
                        )
                continue

            # Standard text message
            content = raw_text[:MAX_CHAT_MESSAGE_LENGTH]
            msg = {
                "type": "message",
                "sender_id": user_id,
                "sender_name": nickname,
                "sender_avatar": avatar,
                "content": content,
                "timestamp": time.time(),
            }
            await store_service.broadcast_to_room(room_id, msg)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket error: %s", e)
    finally:
        send_task.cancel()
        await store_service.unsubscribe_room(room_id, listener_queue)
        await store_service.release_ws_slot(user_id=user_id, client_ip=client_ip)
        await store_service.broadcast_to_room(
            room_id,
            {
                "type": "system",
                "content": f"{nickname} left the chat",
                "timestamp": time.time(),
            },
        )


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

        await store_service.broadcast_to_room(
            room_id,
            {
                "type": "ended",
                "content": "Conversation has ended.",
                "timestamp": time.time(),
            },
        )

    return {"message": "Conversation ended."}

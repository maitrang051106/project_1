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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import SessionLocal, get_db
from app.core.security import decode_access_token
from app.models.conversation import Conversation
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
    # 1. Xác thực người dùng qua JWT token
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

    # 2. Kiểm tra quyền thuộc phòng chat (membership)
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

        # Lấy anon_name của người gửi
        u_res = await db.execute(select(User).where(User.id == user_id))
        user = u_res.scalar_one_or_none()
        anon_name = user.anon_name if user else "Tôi"

    await websocket.accept()

    # Đăng ký nhận tin nhắn của phòng
    listener_queue = await store_service.subscribe_room(room_id)

    # Báo cho đối phương biết có người vừa kết nối
    await store_service.broadcast_to_room(
        room_id,
        {
            "type": "system",
            "content": f"{anon_name} đã tham gia phòng chat",
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

            # Giới hạn độ dài tin nhắn tối đa 1000 ký tự theo quy định bảo mật
            content = raw_text[:1000]

            msg = {
                "type": "message",
                "sender_id": user_id,
                "sender_name": anon_name,
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
        await store_service.broadcast_to_room(
            room_id,
            {
                "type": "system",
                "content": f"{anon_name} đã rời khỏi phòng chat",
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
            detail="Bạn không phải thành viên của cuộc trò chuyện này",
        )

    if conv.ended_at is None:
        conv.ended_at = func.now()
        await db.commit()

        # Báo cho phòng chat biết cuộc hội thoại đã kết thúc
        await store_service.broadcast_to_room(
            room_id,
            {
                "type": "ended",
                "content": "Cuộc trò chuyện đã kết thúc bởi người dùng",
                "timestamp": time.time(),
            },
        )

    return {"message": "Đã kết thúc cuộc trò chuyện"}


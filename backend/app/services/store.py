import asyncio
import json
import logging
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class StoreService:
    """Quản lý trạng thái tạm thời (OTP, cooldown, hàng đợi matching, kết quả ghép).
    Tự động dùng Redis nếu kết nối được, hoặc chuyển sang in-memory fallback an toàn.
    """

    def __init__(self) -> None:
        self._redis = None
        self._in_memory_kv: dict[str, tuple[Any, float]] = {}  # key -> (value, expire_timestamp)
        self._in_memory_queue: dict[int, dict] = {}  # user_id -> candidate_info
        self._in_memory_matches: dict[int, dict] = {}  # user_id -> match_info
        self._rooms: dict[int, set[asyncio.Queue]] = {}  # room_id -> set of listener queues

    async def get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1.0)
            await r.ping()
            self._redis = r
            logger.info("Connected to Redis successfully.")
            return self._redis
        except Exception:
            self._redis = False  # Mark as unavailable
            logger.info("Redis unavailable, using in-memory store.")
            return None

    # --- OTP & Cooldown ---
    async def set_otp(self, email_hash: str, otp_hashed: str, ttl: int = 300) -> None:
        r = await self.get_redis()
        if r:
            await r.setex(f"otp:{email_hash}", ttl, json.dumps({"hash": otp_hashed, "attempts": 0}))
        else:
            self._in_memory_kv[f"otp:{email_hash}"] = ({"hash": otp_hashed, "attempts": 0}, time.time() + ttl)

    async def verify_otp(self, email_hash: str, otp_hashed: str) -> bool:
        r = await self.get_redis()
        key = f"otp:{email_hash}"
        data = None

        if r:
            val = await r.get(key)
            if val:
                data = json.loads(val)
        else:
            val, exp = self._in_memory_kv.get(key, (None, 0))
            if val and exp > time.time():
                data = val

        if not data:
            return False

        if data.get("attempts", 0) >= 5:
            await self.delete_key(key)
            return False

        if data.get("hash") == otp_hashed:
            await self.delete_key(key)
            return True

        # Tăng số lần thử sai
        data["attempts"] = data.get("attempts", 0) + 1
        if r:
            ttl = await r.ttl(key)
            if ttl > 0:
                await r.setex(key, ttl, json.dumps(data))
        else:
            _, exp = self._in_memory_kv.get(key, (None, 0))
            self._in_memory_kv[key] = (data, exp)

        return False

    async def is_in_cooldown(self, email_hash: str) -> bool:
        r = await self.get_redis()
        key = f"cooldown:{email_hash}"
        if r:
            return bool(await r.exists(key))
        val, exp = self._in_memory_kv.get(key, (None, 0))
        return exp > time.time()

    async def set_cooldown(self, email_hash: str, ttl: int = 60) -> None:
        r = await self.get_redis()
        key = f"cooldown:{email_hash}"
        if r:
            await r.setex(key, ttl, "1")
        else:
            self._in_memory_kv[key] = ("1", time.time() + ttl)

    async def delete_key(self, key: str) -> None:
        r = await self.get_redis()
        if r:
            await r.delete(key)
        else:
            self._in_memory_kv.pop(key, None)

    # --- Matching Queue ---
    async def add_to_queue(self, user_id: int, profile: dict, pref: dict) -> None:
        self._in_memory_queue[user_id] = {
            "user_id": user_id,
            "profile": profile,
            "pref": pref,
            "joined_at": time.time(),
        }

    async def remove_from_queue(self, user_id: int) -> None:
        self._in_memory_queue.pop(user_id, None)

    async def get_queue_candidates(self, exclude_user_id: int) -> list[dict]:
        now = time.time()
        # Loại bỏ các candidate timeout quá 60s
        stale = [uid for uid, item in self._in_memory_queue.items() if now - item["joined_at"] > 60]
        for uid in stale:
            self._in_memory_queue.pop(uid, None)

        return [
            item for uid, item in self._in_memory_queue.items()
            if uid != exclude_user_id
        ]

    async def save_match_result(self, user_a_id: int, user_b_id: int, room_id: int, partner_a_info: dict, partner_b_info: dict) -> None:
        self._in_memory_matches[user_a_id] = {"room_id": room_id, "partner": partner_b_info, "matched_at": time.time()}
        self._in_memory_matches[user_b_id] = {"room_id": room_id, "partner": partner_a_info, "matched_at": time.time()}

    async def get_match_result(self, user_id: int) -> dict | None:
        match = self._in_memory_matches.get(user_id)
        if match and time.time() - match["matched_at"] < 300:
            return match
        return None

    async def clear_match_result(self, user_id: int) -> None:
        self._in_memory_matches.pop(user_id, None)

    # --- Realtime Chat Room Broadcast ---
    async def subscribe_room(self, room_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        self._rooms[room_id].add(q)
        return q

    async def unsubscribe_room(self, room_id: int, q: asyncio.Queue) -> None:
        if room_id in self._rooms:
            self._rooms[room_id].discard(q)
            if not self._rooms[room_id]:
                self._rooms.pop(room_id, None)

    async def broadcast_to_room(self, room_id: int, message: dict) -> None:
        queues = self._rooms.get(room_id, set()).copy()
        for q in queues:
            await q.put(message)


store_service = StoreService()


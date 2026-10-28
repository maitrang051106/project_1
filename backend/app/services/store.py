import asyncio
import json
import logging
import time
from typing import Any

from app.core.config import settings
from app.core.constants import MATCH_RESULT_TTL_SECONDS, MATCH_TIMEOUT_SECONDS
from app.core.security import compare_otp_hash

logger = logging.getLogger(__name__)


class RedisUnavailable(RuntimeError):
    pass


# Redis Lua Script for atomic reservation of a candidate in matching queue
RESERVE_CANDIDATE_LUA = """
local candidate_key = KEYS[1]
local queue_set_key = KEYS[2]
local cand_id = ARGV[1]

local exists = redis.call('SISMEMBER', queue_set_key, cand_id)
if exists == 1 then
    redis.call('SREM', queue_set_key, cand_id)
    redis.call('DEL', candidate_key)
    return 1
else
    return 0
end
"""


class StoreService:
    """Manage shared transient state:
    - OTP storage & verification with domain separation
    - Rate limits (IP and email)
    - Distributed matching queue with 60s timeout & atomic reservation
    - Real-time Pub/Sub room broadcast (Redis with in-memory fallback for local dev)
    """

    def __init__(self) -> None:
        self._redis = None
        self._redis_lock = asyncio.Lock()
        self._memory_lock = asyncio.Lock()

        # In-memory fallbacks for local dev / testing
        self._in_memory_kv: dict[str, tuple[Any, float]] = {}
        self._in_memory_sessions: dict[str, tuple[int, float]] = {}
        self._in_memory_user_sessions: dict[int, set[str]] = {}
        self._in_memory_queue: dict[int, dict[str, Any]] = {}
        self._in_memory_matches: dict[int, dict[str, Any]] = {}
        self._in_memory_not_found: dict[int, dict[str, Any]] = {}
        self._rooms: dict[str, set[asyncio.Queue]] = {}
        self._pubsub_tasks: dict[str, asyncio.Task] = {}
        self._in_memory_user_ws: dict[int, int] = {}
        self._in_memory_ip_ws: dict[str, int] = {}

    def _handle_redis_failure(self, error: Exception) -> None:
        self._redis = None
        if settings.environment.lower() == "production":
            logger.error("Redis operation failed in production: %s", type(error).__name__)
            raise RedisUnavailable("Redis is temporarily unavailable.") from error

    def _ensure_redis_in_production(self, r: Any) -> None:
        if r is None and settings.environment.lower() == "production":
            raise RedisUnavailable("Shared storage (Redis) is temporarily unavailable in production.")

    async def init_redis(self) -> None:
        """Initialize Redis connection during application lifespan startup."""
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            await r.ping()
            self._redis = r
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            self._redis = None
            if settings.environment.lower() == "production":
                logger.error("Failed to connect to Redis in production: %s", type(e).__name__)
                raise RuntimeError("Redis is required in production environment.") from e
            logger.info("Redis unavailable (%s), using in-memory store for development.", type(e).__name__)

    async def close_redis(self) -> None:
        """Close Redis connection and active Pub/Sub tasks during shutdown."""
        for task in self._pubsub_tasks.values():
            task.cancel()
        self._pubsub_tasks.clear()

        if self._redis:
            try:
                await self._redis.close()
            except Exception as exc:
                self._handle_redis_failure(exc)
            self._redis = None

    async def get_redis(self):
        """Get or lazily connect to Redis. Recovers gracefully if Redis restarts."""
        if self._redis is not None:
            return self._redis

        async with self._redis_lock:
            if self._redis is not None:
                return self._redis
            try:
                import redis.asyncio as aioredis

                r = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_timeout=1.5,
                    socket_connect_timeout=1.5,
                )
                await r.ping()
                self._redis = r
                return self._redis
            except Exception as exc:
                self._handle_redis_failure(exc)
                return None

    async def is_redis_healthy(self) -> bool:
        """Check if Redis responds to PING within timeout."""
        try:
            r = await self.get_redis()
            if not r:
                return False
            res = await asyncio.wait_for(r.ping(), timeout=1.0)
            return bool(res)
        except Exception:
            return False

    # --------------------------------------------------------------------------
    # RATE LIMITING (IP & Email)
    # --------------------------------------------------------------------------
    async def check_rate_limit(self, key_suffix: str, max_requests: int, window_seconds: int) -> bool:
        """Fixed-window rate limiter using Redis INCR or in-memory fallback.
        Returns True if request is allowed, False if rate limit is exceeded.
        """
        r = await self.get_redis()
        key = f"hust:v1:ratelimit:{key_suffix}"

        if r:
            try:
                current = await r.incr(key)
                if current == 1:
                    await r.expire(key, window_seconds)
                return current <= max_requests
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            now = time.time()
            val, exp = self._in_memory_kv.get(key, (0, 0))
            if now > exp:
                self._in_memory_kv[key] = (1, now + window_seconds)
                return True
            if val < max_requests:
                self._in_memory_kv[key] = (val + 1, exp)
                return True
            return False

    async def clear_rate_limit(self, key_suffix: str) -> None:
        key = f"hust:v1:ratelimit:{key_suffix}"
        r = await self.get_redis()
        if r:
            try:
                await r.delete(key)
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            self._in_memory_kv.pop(key, None)

    # --------------------------------------------------------------------------
    # JWT SESSION ALLOWLIST
    # --------------------------------------------------------------------------
    async def create_session(self, user_id: int, jti: str, ttl: int) -> None:
        session_key = f"hust:v1:auth:session:{jti}"
        user_sessions_key = f"hust:v1:auth:user_sessions:{user_id}"
        expires_at = time.time() + ttl
        r = await self.get_redis()
        if r:
            try:
                async with r.pipeline(transaction=True) as pipe:
                    pipe.setex(session_key, ttl, str(user_id))
                    pipe.zadd(user_sessions_key, {jti: expires_at})
                    pipe.expire(user_sessions_key, ttl)
                    await pipe.execute()
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            self._in_memory_sessions[jti] = (user_id, expires_at)
            self._in_memory_user_sessions.setdefault(user_id, set()).add(jti)

    async def is_session_active(self, user_id: int, jti: str) -> bool:
        session_key = f"hust:v1:auth:session:{jti}"
        r = await self.get_redis()
        if r:
            try:
                return await r.get(session_key) == str(user_id)
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            session = self._in_memory_sessions.get(jti)
            return bool(session and session[0] == user_id and session[1] > time.time())

    async def revoke_session(self, user_id: int, jti: str) -> None:
        session_key = f"hust:v1:auth:session:{jti}"
        user_sessions_key = f"hust:v1:auth:user_sessions:{user_id}"
        r = await self.get_redis()
        if r:
            try:
                async with r.pipeline(transaction=True) as pipe:
                    pipe.delete(session_key)
                    pipe.zrem(user_sessions_key, jti)
                    await pipe.execute()
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            self._in_memory_sessions.pop(jti, None)
            self._in_memory_user_sessions.get(user_id, set()).discard(jti)

    async def revoke_user_sessions(self, user_id: int) -> None:
        user_sessions_key = f"hust:v1:auth:user_sessions:{user_id}"
        r = await self.get_redis()
        if r:
            try:
                session_ids = await r.zrange(user_sessions_key, 0, -1)
                keys = [f"hust:v1:auth:session:{jti}" for jti in session_ids]
                async with r.pipeline(transaction=True) as pipe:
                    if keys:
                        pipe.delete(*keys)
                    pipe.delete(user_sessions_key)
                    await pipe.execute()
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            for jti in self._in_memory_user_sessions.pop(user_id, set()):
                self._in_memory_sessions.pop(jti, None)

    # --------------------------------------------------------------------------
    # WEBSOCKET CONNECTION LIMITS (PER-USER & PER-IP)
    # --------------------------------------------------------------------------
    async def acquire_ws_slot(
        self,
        user_id: int,
        client_ip: str,
        max_user: int = 3,
        max_ip: int = 10,
    ) -> tuple[bool, str | None]:
        """Atomically acquire a WebSocket slot for (user_id, client_ip).
        Returns (True, None) if allowed, or (False, reason) if limit exceeded.
        """
        r = await self.get_redis()
        if r:
            user_key = f"hust:v1:ws:user:{user_id}"
            ip_key = f"hust:v1:ws:ip:{client_ip}"
            lua = """
            local user_cnt = tonumber(redis.call('GET', KEYS[1]) or '0')
            if user_cnt >= tonumber(ARGV[1]) then
                return 'USER_LIMIT'
            end
            local ip_cnt = tonumber(redis.call('GET', KEYS[2]) or '0')
            if ip_cnt >= tonumber(ARGV[2]) then
                return 'IP_LIMIT'
            end
            redis.call('INCR', KEYS[1])
            redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
            redis.call('INCR', KEYS[2])
            redis.call('EXPIRE', KEYS[2], tonumber(ARGV[3]))
            return 'OK'
            """
            try:
                res = await r.eval(lua, 2, user_key, ip_key, max_user, max_ip, 86400)
                if res == "OK":
                    return True, None
                elif res == "USER_LIMIT":
                    return False, f"Maximum {max_user} concurrent WebSocket connections reached for this user."
                elif res == "IP_LIMIT":
                    return False, f"Maximum {max_ip} concurrent WebSocket connections reached for this IP."
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            user_cnt = self._in_memory_user_ws.get(user_id, 0)
            if user_cnt >= max_user:
                return False, f"Maximum {max_user} concurrent WebSocket connections reached for this user."
            ip_cnt = self._in_memory_ip_ws.get(client_ip, 0)
            if ip_cnt >= max_ip:
                return False, f"Maximum {max_ip} concurrent WebSocket connections reached for this IP."
            self._in_memory_user_ws[user_id] = user_cnt + 1
            self._in_memory_ip_ws[client_ip] = ip_cnt + 1
            return True, None

    async def release_ws_slot(self, user_id: int, client_ip: str) -> None:
        """Release an acquired WebSocket slot for (user_id, client_ip)."""
        r = await self.get_redis()
        if r:
            user_key = f"hust:v1:ws:user:{user_id}"
            ip_key = f"hust:v1:ws:ip:{client_ip}"
            lua = """
            local u = tonumber(redis.call('GET', KEYS[1]) or '0')
            if u > 1 then
                redis.call('DECR', KEYS[1])
            else
                redis.call('DEL', KEYS[1])
            end
            local ip = tonumber(redis.call('GET', KEYS[2]) or '0')
            if ip > 1 then
                redis.call('DECR', KEYS[2])
            else
                redis.call('DEL', KEYS[2])
            end
            return 'OK'
            """
            try:
                await r.eval(lua, 2, user_key, ip_key)
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            if user_id in self._in_memory_user_ws:
                self._in_memory_user_ws[user_id] = max(0, self._in_memory_user_ws[user_id] - 1)
                if self._in_memory_user_ws[user_id] == 0:
                    del self._in_memory_user_ws[user_id]
            if client_ip in self._in_memory_ip_ws:
                self._in_memory_ip_ws[client_ip] = max(0, self._in_memory_ip_ws[client_ip] - 1)
                if self._in_memory_ip_ws[client_ip] == 0:
                    del self._in_memory_ip_ws[client_ip]

    # --------------------------------------------------------------------------
    # OTP & COOLDOWN (Keys based strictly on HMAC, never raw email)
    # --------------------------------------------------------------------------
    async def set_otp(self, email_hash: str, otp_hashed: str, purpose: str = "register", ttl: int = 300) -> None:
        r = await self.get_redis()
        key = f"hust:v1:otp:{purpose}:{email_hash}"
        data = json.dumps({"hash": otp_hashed, "attempts": 0})

        if r:
            try:
                await r.setex(key, ttl, data)
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            self._in_memory_kv[key] = ({"hash": otp_hashed, "attempts": 0}, time.time() + ttl)

    async def verify_otp(self, email_hash: str, otp_hashed: str, purpose: str = "register") -> bool:
        """Verify OTP using constant-time comparison.
        Enforces maximum 5 attempts. Deletes key on successful verification or attempt exhaustion.
        """
        r = await self.get_redis()
        key = f"hust:v1:otp:{purpose}:{email_hash}"

        if r:
            try:
                raw = await r.get(key)
                if not raw:
                    return False
                data = json.loads(raw)
                attempts = data.get("attempts", 0)
                if attempts >= 5:
                    await r.delete(key)
                    return False

                expected_hash = data.get("hash", "")
                if compare_otp_hash(otp_hashed, expected_hash):
                    await r.delete(key)
                    return True

                # Increment attempts atomically while preserving remaining TTL
                data["attempts"] = attempts + 1
                ttl = await r.ttl(key)
                if ttl > 0:
                    await r.setex(key, ttl, json.dumps(data))
                else:
                    await r.delete(key)
                return False
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            val, exp = self._in_memory_kv.get(key, (None, 0))
            if not val or exp <= time.time():
                return False

            attempts = val.get("attempts", 0)
            if attempts >= 5:
                self._in_memory_kv.pop(key, None)
                return False

            expected_hash = val.get("hash", "")
            if compare_otp_hash(otp_hashed, expected_hash):
                self._in_memory_kv.pop(key, None)
                return True

            val["attempts"] = attempts + 1
            self._in_memory_kv[key] = (val, exp)
            return False

    async def clear_otp(self, email_hash: str, purpose: str = "register") -> None:
        """Remove OTP and cooldown keys (e.g. after SMTP send failure)."""
        r = await self.get_redis()
        otp_key = f"hust:v1:otp:{purpose}:{email_hash}"
        cd_key = f"hust:v1:cooldown:{purpose}:{email_hash}"

        if r:
            try:
                await r.delete(otp_key, cd_key)
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            self._in_memory_kv.pop(otp_key, None)
            self._in_memory_kv.pop(cd_key, None)

    async def is_in_cooldown(self, email_hash: str, purpose: str = "register") -> bool:
        r = await self.get_redis()
        key = f"hust:v1:cooldown:{purpose}:{email_hash}"

        if r:
            try:
                return bool(await r.exists(key))
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            val, exp = self._in_memory_kv.get(key, (None, 0))
            return exp > time.time()

    async def set_cooldown(self, email_hash: str, purpose: str = "register", ttl: int = 60) -> None:
        r = await self.get_redis()
        key = f"hust:v1:cooldown:{purpose}:{email_hash}"

        if r:
            try:
                await r.setex(key, ttl, "1")
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        self._ensure_redis_in_production(r)

        async with self._memory_lock:
            self._in_memory_kv[key] = ("1", time.time() + ttl)

    # --------------------------------------------------------------------------
    # MATCHING QUEUE (60s TTL, attempt isolation, atomic reservation)
    # --------------------------------------------------------------------------
    async def add_to_queue(
        self, user_id: int, profile: dict, pref: dict, attempt_id: str
    ) -> None:
        now = time.time()
        record = {
            "user_id": user_id,
            "profile": profile,
            "pref": pref,
            "attempt_id": attempt_id,
            "joined_at": now,
        }
        r = await self.get_redis()
        if r:
            try:
                entry_key = f"hust:v1:match:queue:entry:{user_id}"
                set_key = "hust:v1:match:queue:set"
                await r.setex(entry_key, MATCH_TIMEOUT_SECONDS + 5, json.dumps(record))
                await r.sadd(set_key, str(user_id))
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            self._in_memory_queue[user_id] = record

    async def remove_from_queue(self, user_id: int) -> None:
        r = await self.get_redis()
        if r:
            try:
                await r.srem("hust:v1:match:queue:set", str(user_id))
                await r.delete(f"hust:v1:match:queue:entry:{user_id}")
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            self._in_memory_queue.pop(user_id, None)

    async def get_queue_candidates(self, exclude_user_id: int) -> list[dict]:
        """Retrieve all active candidate entries in the matching queue.
        Evicts candidates who joined more than 60 seconds ago.
        """
        now = time.time()
        r = await self.get_redis()
        if r:
            try:
                set_key = "hust:v1:match:queue:set"
                members = await r.smembers(set_key)
                candidates = []
                for uid_str in members:
                    uid = int(uid_str)
                    if uid == exclude_user_id:
                        continue
                    entry_key = f"hust:v1:match:queue:entry:{uid}"
                    raw = await r.get(entry_key)
                    if not raw:
                        await r.srem(set_key, uid_str)
                        continue
                    item = json.loads(raw)
                    if now - item["joined_at"] >= MATCH_TIMEOUT_SECONDS:
                        # Stale / expired candidate -> mark not_found and evict
                        await r.srem(set_key, uid_str)
                        await r.delete(entry_key)
                        await self.save_not_found_result(uid, item.get("attempt_id", ""))
                        continue
                    candidates.append(item)
                return candidates
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            stale = [
                uid
                for uid, item in self._in_memory_queue.items()
                if now - item["joined_at"] >= MATCH_TIMEOUT_SECONDS
            ]
            for uid in stale:
                expired_item = self._in_memory_queue.pop(uid, None)
                if expired_item:
                    self._in_memory_not_found[uid] = {
                        "attempt_id": expired_item.get("attempt_id", ""),
                        "timed_out_at": now,
                    }

            return [
                item
                for uid, item in self._in_memory_queue.items()
                if uid != exclude_user_id
            ]

    async def reserve_candidate(self, candidate_user_id: int) -> bool:
        """Atomically reserve/remove candidate from queue to prevent race conditions."""
        r = await self.get_redis()
        if r:
            try:
                candidate_key = f"hust:v1:match:queue:entry:{candidate_user_id}"
                queue_set_key = "hust:v1:match:queue:set"
                res = await r.eval(
                    RESERVE_CANDIDATE_LUA,
                    2,
                    candidate_key,
                    queue_set_key,
                    str(candidate_user_id),
                )
                return bool(res == 1)
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            if candidate_user_id in self._in_memory_queue:
                self._in_memory_queue.pop(candidate_user_id)
                return True
            return False

    async def restore_queue_entry(self, record: dict[str, Any]) -> None:
        """Restore a reserved candidate without extending its original timeout."""
        user_id = int(record["user_id"])
        elapsed = time.time() - record["joined_at"]
        remaining_ttl = max(1, MATCH_TIMEOUT_SECONDS + 5 - int(elapsed))
        r = await self.get_redis()
        if r:
            try:
                entry_key = f"hust:v1:match:queue:entry:{user_id}"
                set_key = "hust:v1:match:queue:set"
                await r.setex(entry_key, remaining_ttl, json.dumps(record))
                await r.sadd(set_key, str(user_id))
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            self._in_memory_queue[user_id] = record

    async def get_queue_entry(self, user_id: int) -> dict | None:
        """Get the current queue entry for a user, or None if not waiting."""
        r = await self.get_redis()
        if r:
            try:
                entry_key = f"hust:v1:match:queue:entry:{user_id}"
                raw = await r.get(entry_key)
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            return self._in_memory_queue.get(user_id)

    async def save_match_result(
        self,
        user_a_id: int,
        user_b_id: int,
        room_id: int,
        partner_a_info: dict,
        partner_b_info: dict,
        attempt_a_id: str = "",
        attempt_b_id: str = "",
    ) -> None:
        now = time.time()
        res_a = {
            "status": "matched",
            "room_id": room_id,
            "partner": partner_b_info,
            "attempt_id": attempt_a_id,
            "matched_at": now,
        }
        res_b = {
            "status": "matched",
            "room_id": room_id,
            "partner": partner_a_info,
            "attempt_id": attempt_b_id,
            "matched_at": now,
        }

        r = await self.get_redis()
        if r:
            try:
                await r.setex(
                    f"hust:v1:match:result:{user_a_id}",
                    MATCH_RESULT_TTL_SECONDS,
                    json.dumps(res_a),
                )
                await r.setex(
                    f"hust:v1:match:result:{user_b_id}",
                    MATCH_RESULT_TTL_SECONDS,
                    json.dumps(res_b),
                )
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            self._in_memory_matches[user_a_id] = res_a
            self._in_memory_matches[user_b_id] = res_b

    async def get_match_result(self, user_id: int) -> dict | None:
        r = await self.get_redis()
        if r:
            try:
                raw = await r.get(f"hust:v1:match:result:{user_id}")
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            match = self._in_memory_matches.get(user_id)
            if match and time.time() - match["matched_at"] < MATCH_RESULT_TTL_SECONDS:
                return match
            return None

    async def save_not_found_result(self, user_id: int, attempt_id: str) -> None:
        """Record terminal not_found status when 60s matching times out."""
        record = {
            "status": "not_found",
            "attempt_id": attempt_id,
            "timed_out_at": time.time(),
        }
        r = await self.get_redis()
        if r:
            try:
                await r.setex(
                    f"hust:v1:match:terminal:{user_id}",
                    MATCH_RESULT_TTL_SECONDS,
                    json.dumps(record),
                )
                return
            except Exception as exc:
                self._handle_redis_failure(exc)

        async with self._memory_lock:
            self._in_memory_not_found[user_id] = record

    async def get_not_found_result(self, user_id: int) -> dict | None:
        r = await self.get_redis()
        if r:
            try:
                raw = await r.get(f"hust:v1:match:terminal:{user_id}")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass

        async with self._memory_lock:
            res = self._in_memory_not_found.get(user_id)
            if res and time.time() - res["timed_out_at"] < MATCH_RESULT_TTL_SECONDS:
                return res
            return None

    async def clear_match_result(self, user_id: int) -> None:
        """Clear all active and terminal matching results for a user."""
        r = await self.get_redis()
        if r:
            try:
                await r.delete(
                    f"hust:v1:match:result:{user_id}",
                    f"hust:v1:match:terminal:{user_id}",
                )
            except Exception:
                pass

        async with self._memory_lock:
            self._in_memory_matches.pop(user_id, None)
            self._in_memory_not_found.pop(user_id, None)

    # --------------------------------------------------------------------------
    # REALTIME ROOM BROADCAST (Redis Pub/Sub with local in-memory fallback)
    # --------------------------------------------------------------------------
    def _room_channel(self, room_id: int | str) -> str:
        return f"hust:v1:chat:room:{room_id}"

    async def subscribe_room(self, room_id: int | str) -> asyncio.Queue:
        """Subscribe client WebSocket to room broadcast channel."""
        q: asyncio.Queue = asyncio.Queue()
        room_str = str(room_id)

        async with self._memory_lock:
            if room_str not in self._rooms:
                self._rooms[room_str] = set()
            self._rooms[room_str].add(q)

        # Connect to Redis Pub/Sub if available and not yet subscribed
        r = await self.get_redis()
        if r and room_str not in self._pubsub_tasks:
            try:
                pubsub = r.pubsub()
                channel = self._room_channel(room_str)
                await pubsub.subscribe(channel)

                async def _reader():
                    try:
                        async for message in pubsub.listen():
                            if message.get("type") == "message":
                                raw_data = message.get("data")
                                if raw_data:
                                    msg_obj = json.loads(raw_data)
                                    async with self._memory_lock:
                                        listeners = self._rooms.get(room_str, set()).copy()
                                    for listener in listeners:
                                        await listener.put(msg_obj)
                    except (asyncio.CancelledError, Exception):
                        pass
                    finally:
                        try:
                            await pubsub.unsubscribe(channel)
                            await pubsub.close()
                        except Exception:
                            pass

                self._pubsub_tasks[room_str] = asyncio.create_task(_reader())
            except Exception:
                pass

        return q

    async def unsubscribe_room(self, room_id: int | str, q: asyncio.Queue) -> None:
        room_str = str(room_id)
        async with self._memory_lock:
            if room_str in self._rooms:
                self._rooms[room_str].discard(q)
                if not self._rooms[room_str]:
                    self._rooms.pop(room_str, None)
                    task = self._pubsub_tasks.pop(room_str, None)
                    if task:
                        task.cancel()

    async def broadcast_to_room(self, room_id: int | str, message: dict) -> None:
        """Broadcast message to all subscribers across instances via Redis Pub/Sub."""
        room_str = str(room_id)
        r = await self.get_redis()

        if r:
            try:
                channel = self._room_channel(room_str)
                await r.publish(channel, json.dumps(message))
                return
            except Exception:
                pass

        # Fallback to local in-memory subscribers
        async with self._memory_lock:
            queues = self._rooms.get(room_str, set()).copy()
        for q in queues:
            await q.put(message)


store_service = StoreService()

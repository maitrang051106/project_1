from datetime import timedelta
from unittest.mock import AsyncMock

import anyio
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import (
    compare_otp_hash,
    create_access_token,
    create_email_hash,
    decode_access_token,
    generate_default_nickname,
    generate_otp,
    hash_otp,
    hash_password,
    is_valid_hust_email,
    normalize_email,
    verify_password,
)
from app.schemas.auth import LoginIn
from app.services.auth_service import AuthService
from app.services.email_service import build_otp_email_message
from app.services.store import StoreService


def test_normalize_email() -> None:
    assert normalize_email("  SV2026@SIS.HUST.EDU.VN  ") == "sv2026@sis.hust.edu.vn"


def test_is_valid_hust_email_strictly_sis() -> None:
    # Only @sis.hust.edu.vn is allowed
    assert is_valid_hust_email("student@sis.hust.edu.vn") is True
    # @hust.edu.vn and other domains must be rejected
    assert is_valid_hust_email("teacher@hust.edu.vn") is False
    assert is_valid_hust_email("user@gmail.com") is False
    assert is_valid_hust_email("invalid-email") is False


def test_password_hashing_and_verification() -> None:
    raw = "HustChatSecret123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert "$" in hashed
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_create_email_hash() -> None:
    h1 = create_email_hash("user1@sis.hust.edu.vn")
    h2 = create_email_hash("user1@sis.hust.edu.vn")
    h3 = create_email_hash("user2@sis.hust.edu.vn")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_hash_otp_domain_separation_and_compare() -> None:
    otp = "654321"
    reg_hash = hash_otp(otp, purpose="register")
    reset_hash = hash_otp(otp, purpose="reset")

    # Domain separation ensures different purpose yields different hash for same OTP
    assert reg_hash != reset_hash
    assert len(reg_hash) == 64

    # Constant-time comparison
    assert compare_otp_hash(reg_hash, reg_hash) is True
    assert compare_otp_hash(reg_hash, reset_hash) is False
    assert compare_otp_hash(reg_hash, "invalid_hash_string") is False


def test_generate_otp() -> None:
    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_default_nickname() -> None:
    name = generate_default_nickname()
    assert "#" in name
    assert len(name.split()) >= 2


def test_jwt_token_flow() -> None:
    token = create_access_token({"sub": "42"})
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert "exp" in decoded


def test_expired_jwt_is_rejected() -> None:
    token = create_access_token({"sub": "42"}, expires_delta=timedelta(seconds=-1))

    assert decode_access_token(token) is None


def test_login_rate_limit_blocks_before_database(monkeypatch) -> None:
    async def scenario() -> None:
        limiter = AsyncMock(return_value=False)
        monkeypatch.setattr("app.services.auth_service.store_service.check_rate_limit", limiter)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await AuthService.login(
                LoginIn(email="student@sis.hust.edu.vn", password="wrong"), db
            )

        assert exc_info.value.status_code == 429
        assert limiter.await_args.args[1] == settings.login_rate_limit_email_attempts
        assert limiter.await_args.args[2] == settings.login_rate_limit_email_window_seconds
        db.execute.assert_not_awaited()

    anyio.run(scenario)


def test_session_allowlist_revoke_and_user_revoke() -> None:
    async def scenario() -> None:
        store = StoreService()
        async def memory_only_redis():
            return None

        store.get_redis = memory_only_redis
        await store.create_session(user_id=7, jti="session-one", ttl=60)
        await store.create_session(user_id=7, jti="session-two", ttl=60)

        assert await store.is_session_active(user_id=7, jti="session-one")
        assert not await store.is_session_active(user_id=8, jti="session-one")

        await store.revoke_session(user_id=7, jti="session-one")
        assert not await store.is_session_active(user_id=7, jti="session-one")
        assert await store.is_session_active(user_id=7, jti="session-two")

        await store.revoke_user_sessions(user_id=7)
        assert not await store.is_session_active(user_id=7, jti="session-two")

    anyio.run(scenario)


def test_build_otp_email_message() -> None:
    msg = build_otp_email_message(
        to_email="student@sis.hust.edu.vn",
        otp="123456",
        subject_prefix="Registration Code",
    )

    assert msg["To"] == "student@sis.hust.edu.vn"
    assert "123456" in msg["Subject"]
    assert "Registration Code" in msg["Subject"]
    payload_text = msg.get_body(preferencelist=("plain",)).get_content()
    assert "123456" in payload_text
    assert "5 minutes" in payload_text

    payload_html = msg.get_body(preferencelist=("html",)).get_content()
    assert "123456" in payload_html
    assert "HUST Student" in payload_html


def test_get_current_user_validates_active_session(monkeypatch) -> None:
    from unittest.mock import MagicMock
    from app.api.deps import get_current_user
    from app.models.enums import UserRole, UserStatus
    from app.models.user import User
    from app.services.store import store_service

    async def scenario() -> None:
        user_id = 99
        mock_user = User(
            id=user_id,
            email="test.session@sis.hust.edu.vn",
            nickname="Test User",
            avatar="🦉",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        # 1. Issue token and create active session in store
        token = create_access_token({"sub": str(user_id)})
        claims = decode_access_token(token)
        jti = claims["jti"]
        await store_service.create_session(user_id, jti, ttl=60)

        # Active session: get_current_user succeeds
        user = await get_current_user(access_token=token, authorization=None, db=mock_db)
        assert user.id == user_id

        # 2. Revoke session: get_current_user raises 401
        await store_service.revoke_session(user_id, jti)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(access_token=token, authorization=None, db=mock_db)
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail.lower()

    anyio.run(scenario)


def test_logout_endpoint_revokes_session() -> None:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.store import store_service

    async def scenario() -> None:
        user_id = 88
        token = create_access_token({"sub": str(user_id)})
        claims = decode_access_token(token)
        jti = claims["jti"]
        await store_service.create_session(user_id, jti, ttl=60)
        assert await store_service.is_session_active(user_id, jti) is True

        client = TestClient(app)
        client.cookies.set("access_token", token)
        res = client.post("/api/auth/logout")
        assert res.status_code == 200
        assert await store_service.is_session_active(user_id, jti) is False

    anyio.run(scenario)


def test_ws_connection_slots_limit_and_release() -> None:
    from app.services.store import StoreService

    async def scenario() -> None:
        store = StoreService()
        async def memory_only_redis():
            return None
        store.get_redis = memory_only_redis

        user_id = 101
        ip = "192.168.1.50"

        # Acquire 3 slots for user
        for _ in range(3):
            allowed, reason = await store.acquire_ws_slot(user_id, ip, max_user=3, max_ip=10)
            assert allowed is True
            assert reason is None

        # 4th connection for same user is rejected
        allowed, reason = await store.acquire_ws_slot(user_id, ip, max_user=3, max_ip=10)
        assert allowed is False
        assert "Maximum 3 concurrent WebSocket connections" in reason

        # Another user on same IP can still connect
        allowed_other, _ = await store.acquire_ws_slot(user_id=102, client_ip=ip, max_user=3, max_ip=10)
        assert allowed_other is True

        # Release one slot for user_id 101
        await store.release_ws_slot(user_id, ip)

        # Now user_id 101 can connect again
        allowed_retry, _ = await store.acquire_ws_slot(user_id, ip, max_user=3, max_ip=10)
        assert allowed_retry is True

        # Test IP limit: fill remaining slots up to 10
        # currently: user 101 has 3, user 102 has 1 -> total 4 on this IP
        for next_user in range(103, 109):
            ok, _ = await store.acquire_ws_slot(user_id=next_user, client_ip=ip, max_user=3, max_ip=10)
            assert ok is True

        # Now 10 slots on this IP are filled; 11th on same IP is rejected
        ok, ip_reason = await store.acquire_ws_slot(user_id=110, client_ip=ip, max_user=3, max_ip=10)
        assert ok is False
        assert "Maximum 10 concurrent WebSocket connections reached for this IP" in ip_reason

    anyio.run(scenario)


def test_redis_outage_raises_503_in_production(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.store import store_service

    monkeypatch.setattr(settings, "environment", "production")
    async def broken_redis():
        return None
    monkeypatch.setattr(store_service, "get_redis", broken_redis)

    client = TestClient(app, raise_server_exceptions=False)
    # Rate limit check or session verification calls _ensure_redis_in_production in production mode
    res = client.post("/api/auth/request-register-otp", json={"email": "student@sis.hust.edu.vn"})
    assert res.status_code == 503
    assert "temporarily unavailable" in res.json()["detail"].lower()

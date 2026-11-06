"""End-to-End (E2E) integration test for the full HUST Anonymous Chat lifecycle.

Flow covered:
1. 2 users request OTP, register, log in, and complete profile onboarding.
2. Select filters -> 1st match attempt fails due to incompatible filters (mismatch) -> leave queue.
3. Re-select compatible filters -> 2nd match attempt succeeds (Room 1).
4. Exchange anonymous messages over WebSocket in Room 1 -> End chat.
5. Re-match into Room 2 -> Exchange anonymous messages -> Send & accept Friend Request ->
   Verify anonymous conversation (Room 2) automatically ends and directs users to Direct Messages.
6. Exchange persistent Direct Messages over WebSocket & REST -> Log out -> Verify session revocation.
"""

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from app.core.db import get_db
from app.main import app
from app.models import Base
from app.services.store import StoreService


class _AsyncSqliteSessionAdapter:
    """Thin async adapter over a synchronous SQLite Session for full SQL execution in tests."""

    def __init__(self, sync_session: Session) -> None:
        self._session = sync_session

    def add(self, instance: Any) -> None:
        self._session.add(instance)

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return self._session.execute(statement, *args, **kwargs)

    async def commit(self) -> None:
        self._session.commit()

    async def rollback(self) -> None:
        self._session.rollback()

    async def refresh(self, instance: Any, *args: Any, **kwargs: Any) -> None:
        self._session.refresh(instance, *args, **kwargs)

    async def close(self) -> None:
        self._session.close()

    async def __aenter__(self) -> "_AsyncSqliteSessionAdapter":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self._session.close()
        return False


def _create_in_memory_db_factory():
    """Create an in-memory SQLite relational engine with MySQL-compatible `now()` function."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _register_sqlite_functions(dbapi_connection, _connection_record) -> None:
        dbapi_connection.create_function(
            "now",
            0,
            lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
        )

    Base.metadata.create_all(engine)

    def make_session() -> _AsyncSqliteSessionAdapter:
        return _AsyncSqliteSessionAdapter(Session(engine, expire_on_commit=False))

    return engine, make_session


def _receive_until_type(ws, expected_type: str, max_messages: int = 10) -> dict[str, Any]:
    """Read JSON frames from a WebSocketTestSession until `data['type'] == expected_type`."""
    seen: list[dict[str, Any]] = []
    for _ in range(max_messages):
        data = ws.receive_json()
        seen.append(data)
        if data.get("type") == expected_type:
            return data
    raise AssertionError(f"Did not receive {expected_type!r} within {max_messages} frames. Seen: {seen}")


def test_e2e_two_users_full_journey(monkeypatch) -> None:
    engine, session_factory = _create_in_memory_db_factory()

    async def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.api.chat.SessionLocal", session_factory)
    monkeypatch.setattr("app.api.direct_messages.SessionLocal", session_factory)

    # Fresh isolated in-memory StoreService (no external Redis needed)
    isolated_store = StoreService()

    async def _no_redis():
        return None

    isolated_store.get_redis = _no_redis
    monkeypatch.setattr("app.services.store.store_service", isolated_store)
    monkeypatch.setattr("app.services.auth_service.store_service", isolated_store)
    monkeypatch.setattr("app.api.deps.store_service", isolated_store)
    monkeypatch.setattr("app.api.auth.store_service", isolated_store)
    monkeypatch.setattr("app.api.matching.store_service", isolated_store)
    monkeypatch.setattr("app.api.chat.store_service", isolated_store)
    monkeypatch.setattr("app.api.direct_messages.store_service", isolated_store)

    # Capture OTP codes sent during registration
    captured_otps: dict[str, str] = {}

    async def fake_send_otp_email(to_email: str, otp: str, **kwargs: Any) -> bool:
        captured_otps[to_email] = otp
        return True

    monkeypatch.setattr("app.services.auth_service.send_otp_email", fake_send_otp_email)

    email_a = "minh.a225001@sis.hust.edu.vn"
    email_b = "lan.b235002@sis.hust.edu.vn"
    password_a = "HustStudentA#2026"
    password_b = "HustStudentB#2026"

    try:
        with TestClient(app) as client:
            # =========================================================================
            # STEP 1: 2 NGƯỜI DÙNG ĐĂNG KÝ, ĐĂNG NHẬP & ĐĂNG KÝ THÔNG TIN (ONBOARDING)
            # =========================================================================
            res_otp_a = client.post("/api/auth/request-register-otp", json={"email": email_a})
            assert res_otp_a.status_code == 200
            assert email_a in captured_otps

            res_otp_b = client.post("/api/auth/request-register-otp", json={"email": email_b})
            assert res_otp_b.status_code == 200
            assert email_b in captured_otps

            res_reg_a = client.post(
                "/api/auth/register",
                json={
                    "email": email_a,
                    "otp": captured_otps[email_a],
                    "password": password_a,
                },
            )
            assert res_reg_a.status_code == 200
            reg_a_body = res_reg_a.json()
            assert reg_a_body["has_profile"] is False
            user_a_id = reg_a_body["user"]["id"]

            res_reg_b = client.post(
                "/api/auth/register",
                json={
                    "email": email_b,
                    "otp": captured_otps[email_b],
                    "password": password_b,
                },
            )
            assert res_reg_b.status_code == 200
            reg_b_body = res_reg_b.json()
            assert reg_b_body["has_profile"] is False
            user_b_id = reg_b_body["user"]["id"]
            assert user_a_id != user_b_id

            # Login both users explicitly via /api/auth/login
            res_login_a = client.post(
                "/api/auth/login",
                json={"email": email_a, "password": password_a},
            )
            assert res_login_a.status_code == 200
            token_a = res_login_a.json()["token"]
            headers_a = {"Authorization": f"Bearer {token_a}"}
            ws_headers_a = {
                "Origin": "http://localhost:5173",
                "Cookie": f"access_token={token_a}",
            }

            res_login_b = client.post(
                "/api/auth/login",
                json={"email": email_b, "password": password_b},
            )
            assert res_login_b.status_code == 200
            token_b = res_login_b.json()["token"]
            headers_b = {"Authorization": f"Bearer {token_b}"}
            ws_headers_b = {
                "Origin": "http://localhost:5173",
                "Cookie": f"access_token={token_b}",
            }

            # Clear shared TestClient cookie jar so per-user headers_a / headers_b control auth
            client.cookies.clear()

            # Before profile setup, joining matchmaking must fail with 400
            res_pre_match = client.post(
                "/api/match/join",
                headers=headers_a,
                json={
                    "target_gender": "any",
                    "target_major_faculty": "any",
                    "target_cohort": "any",
                },
            )
            assert res_pre_match.status_code == 400
            assert "profile" in res_pre_match.json()["detail"].lower()

            # Check catalog and complete profile onboarding for User A & User B
            soict_code = "school-of-information-and-communication-technology-soict"
            res_catalog = client.get("/api/profile/catalog")
            assert res_catalog.status_code == 200
            catalog_items = res_catalog.json()
            assert any(item["major_code"] == "IT1" and item["faculty_code"] == soict_code for item in catalog_items)
            assert any(item["major_code"] == "IT2" and item["faculty_code"] == soict_code for item in catalog_items)

            res_prof_a = client.post(
                "/api/profile",
                headers=headers_a,
                json={
                    "gender": "male",
                    "major_code": "IT1",
                    "cohort": 68,
                    "nickname": "Bách Khoa A",
                    "avatar": "🦊",
                },
            )
            assert res_prof_a.status_code == 200
            assert res_prof_a.json()["profile"]["major_code"] == "IT1"
            assert res_prof_a.json()["profile"]["faculty_code"] == soict_code
            assert res_prof_a.json()["profile"]["cohort"] == 68

            res_prof_b = client.post(
                "/api/profile",
                headers=headers_b,
                json={
                    "gender": "female",
                    "major_code": "IT2",
                    "cohort": 69,
                    "nickname": "Bách Khoa B",
                    "avatar": "🐱",
                },
            )
            assert res_prof_b.status_code == 200
            assert res_prof_b.json()["profile"]["major_code"] == "IT2"
            assert res_prof_b.json()["profile"]["faculty_code"] == soict_code
            assert res_prof_b.json()["profile"]["cohort"] == 69

            # Verify /auth/me reflects updated nicknames and has_profile=True
            me_a = client.get("/api/auth/me", headers=headers_a).json()
            assert me_a["has_profile"] is True
            assert me_a["user"]["nickname"] == "Bách Khoa A"

            me_b = client.get("/api/auth/me", headers=headers_b).json()
            assert me_b["has_profile"] is True
            assert me_b["user"]["nickname"] == "Bách Khoa B"

            # =========================================================================
            # STEP 2: CHỌN BỘ LỌC -> LẦN THỨ NHẤT MATCH LỆCH (MISMATCH)
            # =========================================================================
            # User A (IT1, K68) requires `same_major` (only matches with IT1), while User B is IT2.
            res_join1_a = client.post(
                "/api/match/join",
                headers=headers_a,
                json={
                    "target_gender": "female",
                    "target_major_faculty": "same_major",
                    "target_cohort": "any",
                },
            )
            assert res_join1_a.status_code == 200
            assert res_join1_a.json()["status"] == "waiting"
            assert res_join1_a.json()["room_id"] is None

            # User B (IT2, K69) selects `same_faculty` (SOICT), which accepts User A,
            # but 2-way mutual matching fails because User A required `same_major` (IT1 != IT2).
            res_join1_b = client.post(
                "/api/match/join",
                headers=headers_b,
                json={
                    "target_gender": "male",
                    "target_major_faculty": "same_faculty",
                    "target_cohort": "any",
                },
            )
            assert res_join1_b.status_code == 200
            assert res_join1_b.json()["status"] == "waiting"
            assert res_join1_b.json()["room_id"] is None

            # Both remain waiting and have no active room
            assert client.get("/api/match/status", headers=headers_a).json()["status"] == "waiting"
            assert client.get("/api/match/status", headers=headers_b).json()["status"] == "waiting"
            assert client.get("/api/match/active-room", headers=headers_a).json()["has_active"] is False
            assert client.get("/api/match/active-room", headers=headers_b).json()["has_active"] is False

            # Leave queue before re-selecting filters
            assert client.post("/api/match/leave", headers=headers_a).status_code == 200
            assert client.post("/api/match/leave", headers=headers_b).status_code == 200
            assert client.get("/api/match/status", headers=headers_a).json()["status"] == "idle"
            assert client.get("/api/match/status", headers=headers_b).json()["status"] == "idle"

            # =========================================================================
            # STEP 3: CHỌN LẠI BỘ LỌC -> MATCH ĐƯỢC (ROOM 1)
            # =========================================================================
            # User A (male, SOICT/IT1, K68) relaxes major filter to `same_faculty` and asks for `junior` cohort (K69)
            res_join2_a = client.post(
                "/api/match/join",
                headers=headers_a,
                json={
                    "target_gender": "female",
                    "target_major_faculty": "same_faculty",
                    "target_cohort": "junior",
                },
            )
            assert res_join2_a.status_code == 200
            assert res_join2_a.json()["status"] == "waiting"

            # User B (female, SOICT/IT2, K69) asks for `male`, `same_faculty`, and `senior` cohort (K68)
            res_join2_b = client.post(
                "/api/match/join",
                headers=headers_b,
                json={
                    "target_gender": "male",
                    "target_major_faculty": "same_faculty",
                    "target_cohort": "senior",
                },
            )
            assert res_join2_b.status_code == 200
            match1_data = res_join2_b.json()
            assert match1_data["status"] == "matched"
            room1_id = match1_data["room_id"]
            assert room1_id is not None
            assert match1_data["partner"]["nickname"] == "Bách Khoa A"

            # User A polls status and sees the same room1_id
            status_a = client.get("/api/match/status", headers=headers_a).json()
            assert status_a["status"] == "matched"
            assert status_a["room_id"] == room1_id
            assert status_a["partner"]["nickname"] == "Bách Khoa B"
            assert client.get("/api/match/active-room", headers=headers_a).json() == {
                "has_active": True,
                "room_id": room1_id,
            }

            # =========================================================================
            # STEP 4: NHẮN TIN ẨN DANH (ROOM 1) -> ENDCHAT
            # =========================================================================
            init_a = client.get(f"/api/conversations/{room1_id}/init", headers=headers_a)
            assert init_a.status_code == 200
            init_a_body = init_a.json()
            assert init_a_body["meta"]["ended_at"] is None
            assert init_a_body["meta"]["opponent"]["nickname"] == "Bách Khoa B"
            # Anonymity check: email must NOT be exposed during anonymous chat
            assert init_a_body["meta"]["opponent"]["email"] is None

            with (
                client.websocket_connect(f"/api/ws/{room1_id}", headers=ws_headers_a) as ws_a,
                client.websocket_connect(f"/api/ws/{room1_id}", headers=ws_headers_b) as ws_b,
            ):
                info_a = _receive_until_type(ws_a, "room_info")
                info_b = _receive_until_type(ws_b, "room_info")
                assert info_a["opponent"]["nickname"] == "Bách Khoa B"
                assert info_a["opponent"]["email"] is None
                assert info_b["opponent"]["nickname"] == "Bách Khoa A"
                assert info_b["opponent"]["email"] is None

                # User A sends anonymous message -> both receive it
                ws_a.send_json({"type": "message", "content": "Chào bạn, mình bên IT1 K68!"})
                msg1_a = _receive_until_type(ws_a, "message")
                msg1_b = _receive_until_type(ws_b, "message")
                assert msg1_a["content"] == "Chào bạn, mình bên IT1 K68!"
                assert msg1_a["sender_id"] == user_a_id
                assert msg1_b["content"] == "Chào bạn, mình bên IT1 K68!"
                assert msg1_b["sender_id"] == user_a_id

                # User B replies -> both receive it
                ws_b.send_json({"type": "message", "content": "Chào tiền bối, em học IT2 K69 ạ!"})
                msg2_a = _receive_until_type(ws_a, "message")
                msg2_b = _receive_until_type(ws_b, "message")
                assert msg2_a["content"] == "Chào tiền bối, em học IT2 K69 ạ!"
                assert msg2_a["sender_id"] == user_b_id
                assert msg2_b["content"] == "Chào tiền bối, em học IT2 K69 ạ!"

                # Verify 24h ephemeral history endpoint contains the 2 messages
                hist_room1 = client.get(
                    f"/api/conversations/{room1_id}/history", headers=headers_a
                ).json()
                assert len(hist_room1["messages"]) == 2

                # User A ends the chat via REST -> both WS clients receive `ended`
                res_end1 = client.post(
                    f"/api/conversations/{room1_id}/end", headers=headers_a
                )
                assert res_end1.status_code == 200
                assert res_end1.json()["message"] == "Conversation ended."

                ended_a = _receive_until_type(ws_a, "ended")
                ended_b = _receive_until_type(ws_b, "ended")
                assert ended_a["ended_by"] == user_a_id
                assert ended_b["ended_by"] == user_a_id

            # Verify Room 1 is marked ended and neither user has an active room
            meta_room1 = client.get(
                f"/api/conversations/{room1_id}/meta", headers=headers_a
            ).json()
            assert meta_room1["ended_at"] is not None
            assert client.get("/api/match/active-room", headers=headers_a).json() == {
                "has_active": False,
                "room_id": None,
            }
            assert client.get("/api/match/active-room", headers=headers_b).json() == {
                "has_active": False,
                "room_id": None,
            }

            # =========================================================================
            # STEP 5: MATCH LẠI -> NHẮN TIN -> ADD FRIEND -> CHUYỂN ĐẾN MESSAGE,
            #         ĐOẠN TIN NHẮN ẨN DANH PHẢI TỰ ĐỘNG END
            # =========================================================================
            res_rejoin_a = client.post(
                "/api/match/join",
                headers=headers_a,
                json={
                    "target_gender": "female",
                    "target_major_faculty": "same_faculty",
                    "target_cohort": "junior",
                },
            )
            assert res_rejoin_a.status_code == 200
            assert res_rejoin_a.json()["status"] == "waiting"

            res_rejoin_b = client.post(
                "/api/match/join",
                headers=headers_b,
                json={
                    "target_gender": "male",
                    "target_major_faculty": "same_faculty",
                    "target_cohort": "senior",
                },
            )
            assert res_rejoin_b.status_code == 200
            match2_data = res_rejoin_b.json()
            assert match2_data["status"] == "matched"
            room2_id = match2_data["room_id"]
            assert room2_id is not None
            assert room2_id != room1_id

            with (
                client.websocket_connect(f"/api/ws/{room2_id}", headers=ws_headers_a) as ws2_a,
                client.websocket_connect(f"/api/ws/{room2_id}", headers=ws_headers_b) as ws2_b,
            ):
                _receive_until_type(ws2_a, "room_info")
                _receive_until_type(ws2_b, "room_info")

                # Exchange anonymous messages in Room 2
                ws2_a.send_json({"type": "message", "content": "Ơ lại match trúng nhau lần nữa nè!"})
                assert _receive_until_type(ws2_a, "message")["content"] == "Ơ lại match trúng nhau lần nữa nè!"
                assert _receive_until_type(ws2_b, "message")["content"] == "Ơ lại match trúng nhau lần nữa nè!"

                ws2_b.send_json({"type": "message", "content": "Có duyên ghê, kết bạn qua nhắn trực tiếp nha!"})
                assert _receive_until_type(ws2_a, "message")["content"] == "Có duyên ghê, kết bạn qua nhắn trực tiếp nha!"
                assert _receive_until_type(ws2_b, "message")["content"] == "Có duyên ghê, kết bạn qua nhắn trực tiếp nha!"

                # User A sends friend request over Room 2 WebSocket
                ws2_a.send_json({"type": "friend_request"})
                req_recv_a = _receive_until_type(ws2_a, "friend_request_received")
                req_recv_b = _receive_until_type(ws2_b, "friend_request_received")
                assert req_recv_a["from_user_id"] == user_a_id
                assert req_recv_b["from_user_id"] == user_a_id
                assert req_recv_b["from_name"] == "Bách Khoa A"

                # User B accepts friend request -> triggers `friend_accepted` + auto-end of Room 2
                ws2_b.send_json({"type": "friend_response", "accepted": True})
                accepted_a = _receive_until_type(ws2_a, "friend_accepted")
                accepted_b = _receive_until_type(ws2_b, "friend_accepted")

                assert accepted_a["redirect_to_dm"] is True
                assert accepted_b["redirect_to_dm"] is True

                revealed_emails = {
                    accepted_a["user_a"]["email"],
                    accepted_a["user_b"]["email"],
                }
                assert revealed_emails == {email_a, email_b}

            # Verify anonymous Room 2 was AUTOMATICALLY ENDED upon friend acceptance:
            # 1) `ended_at` is set on Room 2 metadata
            meta_room2 = client.get(
                f"/api/conversations/{room2_id}/meta", headers=headers_a
            ).json()
            assert meta_room2["ended_at"] is not None

            # 2) Neither user has an active anonymous room anymore
            assert client.get("/api/match/active-room", headers=headers_a).json() == {
                "has_active": False,
                "room_id": None,
            }
            assert client.get("/api/match/active-room", headers=headers_b).json() == {
                "has_active": False,
                "room_id": None,
            }

            # 3) Reconnecting to ended Room 2 WebSocket is rejected with WS_1008_POLICY_VIOLATION
            with pytest.raises(WebSocketDisconnect) as ws_exc:
                with client.websocket_connect(f"/api/ws/{room2_id}", headers=ws_headers_a) as ws_closed:
                    ws_closed.receive_json()
            assert ws_exc.value.code == 1008

            # 4) Anonymous messages from Room 2 were NOT migrated into Direct Messages
            dm_initial_a = client.get(f"/api/messages/{user_b_id}", headers=headers_a)
            assert dm_initial_a.status_code == 200
            assert dm_initial_a.json()["messages"] == []

            # =========================================================================
            # STEP 6: CHUYỂN ĐẾN DIRECT MESSAGE -> NHẮN TIN -> ĐĂNG XUẤT
            # =========================================================================
            friends_a = client.get("/api/friends", headers=headers_a).json()["friends"]
            assert len(friends_a) == 1
            assert friends_a[0]["id"] == user_b_id
            assert friends_a[0]["email"] == email_b
            assert friends_a[0]["nickname"] == "Bách Khoa B"
            assert friends_a[0]["last_message"] is None

            friends_b = client.get("/api/friends", headers=headers_b).json()["friends"]
            assert len(friends_b) == 1
            assert friends_b[0]["id"] == user_a_id
            assert friends_b[0]["email"] == email_a
            assert friends_b[0]["nickname"] == "Bách Khoa A"

            # Both users connect to Direct Message WebSockets and exchange messages
            with (
                client.websocket_connect(f"/api/ws/direct/{user_b_id}", headers=ws_headers_a) as dm_ws_a,
                client.websocket_connect(f"/api/ws/direct/{user_a_id}", headers=ws_headers_b) as dm_ws_b,
            ):
                dm_ws_a.send_text("Chào Lan, mình chuyển qua Direct Message rồi nhé!")
                dm1_a = _receive_until_type(dm_ws_a, "direct_message")
                dm1_b = _receive_until_type(dm_ws_b, "direct_message")
                assert dm1_a["sender_id"] == user_a_id
                assert dm1_a["receiver_id"] == user_b_id
                assert dm1_a["content"] == "Chào Lan, mình chuyển qua Direct Message rồi nhé!"
                assert dm1_b["content"] == "Chào Lan, mình chuyển qua Direct Message rồi nhé!"

                dm_ws_b.send_text("Ok Minh, nhắn bên này không lo hết hạn 24h nữa!")
                dm2_a = _receive_until_type(dm_ws_a, "direct_message")
                dm2_b = _receive_until_type(dm_ws_b, "direct_message")
                assert dm2_a["sender_id"] == user_b_id
                assert dm2_a["receiver_id"] == user_a_id
                assert dm2_a["content"] == "Ok Minh, nhắn bên này không lo hết hạn 24h nữa!"
                assert dm2_b["content"] == "Ok Minh, nhắn bên này không lo hết hạn 24h nữa!"

            # Verify persistent Direct Message history via REST
            dm_hist_a = client.get(f"/api/messages/{user_b_id}", headers=headers_a).json()["messages"]
            assert len(dm_hist_a) == 2
            assert dm_hist_a[0]["content"] == "Chào Lan, mình chuyển qua Direct Message rồi nhé!"
            assert dm_hist_a[1]["content"] == "Ok Minh, nhắn bên này không lo hết hạn 24h nữa!"

            # Verify /api/friends now surfaces the latest direct message preview
            friends_a_after = client.get("/api/friends", headers=headers_a).json()["friends"]
            assert friends_a_after[0]["last_message"] == "Ok Minh, nhắn bên này không lo hết hạn 24h nữa!"
            assert friends_a_after[0]["last_message_at"] is not None

            # Verify all WebSocket slots were cleanly released after closing connections
            assert isolated_store._in_memory_user_ws.get(user_a_id, 0) == 0
            assert isolated_store._in_memory_user_ws.get(user_b_id, 0) == 0

            # Both users log out
            res_logout_a = client.post("/api/auth/logout", headers=headers_a)
            assert res_logout_a.status_code == 200
            assert "signed out" in res_logout_a.json()["message"].lower()

            res_logout_b = client.post("/api/auth/logout", headers=headers_b)
            assert res_logout_b.status_code == 200
            assert "signed out" in res_logout_b.json()["message"].lower()

            # Subsequent requests with logged-out tokens must be rejected with 401
            res_me_after_a = client.get("/api/auth/me", headers=headers_a)
            assert res_me_after_a.status_code == 401
            assert "revoked" in res_me_after_a.json()["detail"].lower()

            res_me_after_b = client.get("/api/auth/me", headers=headers_b)
            assert res_me_after_b.status_code == 401
            assert "revoked" in res_me_after_b.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

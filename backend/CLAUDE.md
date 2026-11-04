# Backend — FastAPI (`backend/`)

## Cấu trúc thư mục
- `app/main.py` — Khởi tạo FastAPI app, Lifespan Redis, CORS, Exception handler `RedisUnavailable` (HTTP 503), gắn routers.
- `app/core/` — Hạ tầng nền tảng:
  - `config.py`: `Settings` (`pydantic-settings`), tự chuẩn hóa `DATABASE_URL` (`mysql+aiomysql://`) và `FRONTEND_ORIGIN`, kiểm tra nghiêm ngặt khi `ENVIRONMENT=production`.
  - `constants.py`: Hằng số domain (`STUDENT_EMAIL_DOMAIN`, `AVATAR_OPTIONS`, `COHORTS`, `MATCH_TIMEOUT_SECONDS=60`, `MAX_WS_CONNECTIONS_PER_USER=3`, `MAX_WS_CONNECTIONS_PER_IP=10`).
  - `db.py`: Lazy AsyncEngine (`pool_pre_ping=False`, `pool_recycle=3600`), SSL context cho Aiven Cloud, `get_db`, và `_SessionLocalProxy`.
  - `security.py`: Chuẩn hóa email, HMAC-SHA256 `email_hash`, PBKDF2-SHA256 password hash, HMAC OTP tách biệt theo `purpose` (`register` vs `reset`), tạo/giải mã JWT kèm `jti`.
- `app/models/` — SQLAlchemy 2.0 Declarative Models (`user.py`, `profile.py`, `conversation.py`, `friendship.py`, `direct_message.py`, `enums.py`, `base.py`).
- `app/schemas/` — Pydantic v2 request/response schemas (`auth.py`, `profile.py`, `matching.py`).
- `app/services/` — Tầng nghiệp vụ & trạng thái:
  - `auth_service.py`: Xử lý đăng ký OTP, đăng nhập mật khẩu, đặt lại mật khẩu, chống dò tài khoản (anti-enumeration), quản lý session `jti`.
  - `email_service.py`: Gửi email OTP HTML bất đồng bộ qua `aiosmtplib`.
  - `catalog.py`: Đọc 68 ngành đào tạo từ `db/seed/hust-68-nganh-2026.csv` (`lru_cache`, `encoding="utf-8-sig"`).
  - `matching.py`: Thuật toán kiểm tra ghép đôi 2 chiều (`is_mutual_match`), hạn mức ghép đôi theo `trust_score`, khung giờ ngày Việt Nam (`UTC+7`).
  - `store.py`: Quản lý trạng thái dùng chung trên Redis (kèm fallback in-memory cho dev/test và Fail-Fast `RedisUnavailable` cho production).
- `app/api/` — HTTP & WebSocket routers (`auth.py`, `profile.py`, `matching.py`, `chat.py`, `direct_messages.py`, `health.py`, `deps.py`).
- `migrations/` — Alembic migrations (`0001_initial_schema` → `0004_expand_faculty_code`).
- `tests/` — Bộ kiểm thử `pytest` (`test_auth.py`, `test_config.py`, `test_health.py`, `test_main.py`, `test_matching.py`, `test_models.py`).

## Anti-Regression Guardrails (Quy tắc chống lặp lại lỗi — BẮT BUỘC)

1. **An toàn Slot WebSocket (Chống rò rỉ Slot)**:
   - Trong cả `chat_websocket` (`/ws/{room_id}`) và `direct_message_websocket` (`/ws/direct/{friend_id}`), **bắt buộc** phải hoàn tất kiểm tra Origin, xác thực JWT/session `jti`, và **kiểm tra điều kiện DB** (phòng tồn tại & `ended_at is None`, hoặc `Friendship.status == "accepted"`, và `user.status != BANNED`) **TRƯỚC KHI** gọi `store_service.acquire_ws_slot(...)`.
   - Sau khi `acquire_ws_slot` thành công, không được có bất kỳ câu lệnh `return` sớm nào trước khi vào khối `try...finally: await store_service.release_ws_slot(...)`.
2. **Vòng đời Kênh Pub/Sub khi Reconnect / F5**:
   - Hàm `store_service.unsubscribe_room(room_id, queue)` chỉ gỡ queue của kết nối vừa đóng khỏi `self._rooms`, **tuyệt đối không hủy task Redis Pub/Sub** của phòng để người dùng F5/reconnect vẫn nhận được tin nhắn.
   - Chỉ gọi `store_service.cancel_room_pubsub(room_id)` khi cuộc trò chuyện thực sự kết thúc (`end_conversation` hoặc tự động đóng khi `friend_accepted`).
3. **Tách biệt Kênh Pub/Sub & Quyền riêng tư**:
   - Phòng chat ẩn danh dùng kênh `hust:v1:channel:match:{room_id}` và lưu lịch sử tạm 24h tại `hust:v1:chat:history:{room_id}`. Không bao giờ trả về email thật (`opponent.email = None`) hoặc copy tin nhắn ẩn danh sang bảng `direct_messages`.
   - Chat bạn bè dùng kênh `hust:v1:channel:dm:{min_id}_{max_id}` và chỉ gửi tin nhắn qua WebSocket `/ws/direct/{friend_id}` (đã bỏ `POST /messages/{friend_id}`).
4. **Cạm bẫy SQLAlchemy 2.0 Async & `aiomysql`**:
   - Quan hệ `User.profile` phải giữ `lazy="selectin"` (hoặc dùng `.options(selectinload(User.profile))`) để tránh lỗi `sqlalchemy.exc.MissingGreenlet` sau khi `await db.commit()`.
   - Trong `app/core/db.py`, giữ `pool_pre_ping=False` vì `aiomysql` không tương thích với hàm `ping(reconnect)` mặc định của SQLAlchemy.
   - Trong model `Conversation`, tên thuộc tính Python là `conversation_type` (ánh xạ vào cột SQL `"type"`). Không truyền `Conversation(type=...)`.
5. **Đọc CSV & Xử lý lỗi Redis**:
   - Mọi file CSV seed phải mở bằng `encoding="utf-8-sig"` và `.lstrip("\ufeff")` để khử ký tự BOM ẩn.
   - Trong `store.py`, không dùng `except Exception: pass` cho các lệnh gọi Redis; luôn gọi `self._handle_redis_failure(exc)` và `self._ensure_redis_in_production(r)`.

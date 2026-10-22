# backend/ – FastAPI

Đọc `../CLAUDE.md` trước. File này mô tả riêng phần backend.

## Nhiệm vụ
API xác thực OTP, hồ sơ, hàng đợi ghép cặp, worker ghép cặp, WebSocket chat. Sau này: Trust Score/Report/Admin, chatbot RAG, Identity Reveal.

## Cấu trúc
```
backend/
  app/
    main.py                 # tạo FastAPI app, include routers, khởi động worker
    core/
      config.py             # pydantic-settings, đọc biến môi trường
      db.py                 # async engine + get_db()
      redis.py              # redis.asyncio client (decode_responses=True)
      security.py           # HMAC, JWT, cookie helper
    api/
      health.py             # GET /health
      auth.py               # POST /auth/request-otp, /auth/verify-otp, /auth/logout
      me.py                 # GET /me
      profile.py            # PUT /profile (mục tiêu, sở thích)
      match.py              # POST /match/join, /match/leave, GET /match/status
      ws.py                 # WebSocket /ws/{room_id}
    services/
      otp.py                # sinh/băm/kiểm tra OTP (Redis)
      email.py              # gửi email (SMTP/dịch vụ email)
      matching.py           # cosine_matrix, greedy_match
      chat.py               # phòng chat, Pub/Sub
    models/                 # SQLAlchemy models (User, Profile, Conversation, ...)
    schemas/                # Pydantic request/response
    workers/
      matching_worker.py    # vòng lặp ghép cặp mỗi ~4 giây
  tests/
  migrations/               # Alembic
  alembic.ini
  requirements.txt
  Dockerfile
  .env.example
```
Chạy app: `uvicorn app.main:app --reload` (lưu ý đường dẫn module là `app.main:app`).

## Quy tắc
- Route chỉ nhận/trả dữ liệu và gọi `services/`; không viết logic nghiệp vụ trong route.
- Dùng `async/await` nhất quán; không gọi hàm chặn (blocking) trong route async.
- Gửi email bằng `BackgroundTasks`, không chặn request.
- Lỗi trả về bằng `HTTPException` với thông báo tiếng Việt, ngắn gọn; **không lộ** email có tồn tại hay không.
- Không `print` dữ liệu nhạy cảm; dùng `logging`, không log OTP/email đầy đủ.

## Luồng OTP (T-07…T-13)
1. `request-otp`: chuẩn hóa email → kiểm tra tên miền → cooldown `otp_cd:{email_hash}` (SET NX EX 60) → sinh OTP bằng `secrets.randbelow(10**6)` → lưu `otp:{email_hash}` = HMAC(email:otp), TTL 300 → gửi email nền → luôn trả thông báo chung.
2. `verify-otp`: tăng `otp_try:{email_hash}` (>5 thì xóa OTP, 429) → so sánh `hmac.compare_digest` → xóa OTP → tạo/tìm user theo `email_hash`, gán `anon_name` → phát JWT cookie.
3. JWT access token 15 phút; cookie `HttpOnly`, `Secure`, `SameSite` theo biến cấu hình.

## WebSocket (T-21, T-22)
- Xác thực JWT, kiểm tra user thuộc `conversation`; sai thì đóng mã 4401 trước khi accept.
- Mỗi phòng một kênh Redis `room:{conversation_id}`; một task đọc từ Redis gửi cho client, vòng lặp chính nhận từ client rồi publish.
- Giới hạn tin nhắn 1000 ký tự và tốc độ gửi; hủy task + unsubscribe khi ngắt kết nối.
- **Không** lưu nội dung tin nhắn vào MySQL.

## Ghép cặp (T-27…T-30)
- Hồ sơ → vector multi-hot (theo danh sách mục tiêu/sở thích cố định trong `matching.py`).
- Hàng đợi `queue:matching` (Redis); mỗi tài khoản một vị trí. Worker quét ~4 giây: dựng ma trận, `cosine_matrix`, `greedy_match` với ngưỡng (mặc định 0.5, cấu hình được), tạo `conversation`, báo cho hai người.
- Chờ quá 60 giây: trả trạng thái "chưa tìm thấy" (chatbot nối ở Sprint 3).
- Nếu chạy nhiều worker: dùng khóa Redis (SET NX) để chỉ một worker ghép tại một thời điểm.

## Biến môi trường (xem `.env.example`)
`DATABASE_URL`, `REDIS_URL`, `OTP_SECRET`, `JWT_SECRET`, `EMAIL_*`/`SMTP_*`, `FRONTEND_ORIGIN`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `MATCH_THRESHOLD`.

## Test
- `pytest` + `httpx.AsyncClient`. Bắt buộc có test: tên miền email (kể cả `fakehust.edu.vn`), OTP đúng/sai/khóa/cooldown, `cosine_matrix`/`greedy_match`.
- Redis/MySQL trong test: dùng instance Docker local hoặc fake; ghi rõ cách chạy trong `README.md`.

## Deploy (Render)
Root Directory `backend`; Build: `pip install -r requirements.txt`; Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`; Health Check `/health`. Chi tiết: `../docs/DEPLOY.md`.

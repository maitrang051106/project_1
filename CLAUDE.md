# HUST Match — Nền tảng Ghép đôi & Chat Ẩn danh Sinh viên Bách Khoa Hà Nội

Ứng dụng web kết nối sinh viên HUST (`@sis.hust.edu.vn`), ghép đôi ẩn danh 2 chiều dựa trên 3 tiêu chí cứng (Giới tính, Trường/Viện/Ngành, Khóa K63–K71), chat realtime qua WebSocket (lưu tạm Redis 24h hỗ trợ F5/reconnect) và kết bạn 2 chiều để nhắn tin lâu dài (`/messages`).

## Tech Stack
- **Frontend**: React 19 + Vite 6 + Tailwind CSS v4 + Zustand + React Router v7
- **Backend**: Python 3.11+ + FastAPI + SQLAlchemy 2.0 (async `aiomysql`) + Alembic + `aiosmtplib`
- **Database**: MySQL 8.0 (chứa 5 bảng MVP: `users`, `profiles`, `conversations`, `friendships`, `direct_messages`)
- **Cache / Queue / PubSub**: Redis 7 (OTP, Rate-limit, Session `jti`, WS Slot, Hàng đợi 60s Lua, Kênh Pub/Sub `match` & `dm`, Lịch sử chat ẩn danh 24h)
- **Catalog Ngành**: 68 ngành đào tạo HUST 2026 đọc trực tiếp từ `db/seed/hust-68-nganh-2026.csv` (`utf-8-sig`) kèm fallback tĩnh `frontend/src/lib/hustCatalog.js`

## Phạm vi hiện tại (MVP Core — Đã hoàn thành)
- **Xác thực**: Đăng ký bằng OTP 6 số gửi qua email `@sis.hust.edu.vn` + Mật khẩu; Đăng nhập bằng Email + Mật khẩu; Quên mật khẩu qua OTP; Quản lý phiên bằng JWT `HttpOnly` cookie kèm Redis Session Allowlist (`jti`).
- **Hồ sơ (Onboarding)**: Nickname, 11 Avatar thú (`🦉`, `🦊`, `🐼`...), Giới tính (`male`/`female`), Cascading Dropdown Trường/Viện (`faculty_code` `VARCHAR(100)`) → Ngành (`major_code`), Khóa (`K63`–`K71`).
- **Ghép đôi 2 chiều (60s)**: Kiểm tra thỏa mãn đồng thời 3 tiêu chí của cả A và B, dùng Redis Lua Script tránh race condition, tự động trả `not_found` khi hết 60s, hỗ trợ `GET /match/active-room`.
- **Chat ẩn danh & Reconnect 24h**: Kênh Pub/Sub `hust:v1:channel:match:{room_id}`, lưu lịch sử tạm 24h trên Redis (`hust:v1:chat:history:{room_id}`), API khởi tạo 1 bước `GET /conversations/{room_id}/init` và phân trang cursor `before_timestamp`. **Tuyệt đối không lộ email (`email: null`) trong phòng ẩn danh và không chép tin nhắn ẩn danh sang `direct_messages`.**
- **Kết bạn & Direct Messages (`/messages`)**: Gửi/nhận lời mời kết bạn 2 chiều (`requested_by`) ngay trong phòng chat; khi đồng ý (`friend_accepted`), tự động đóng phòng ẩn danh và đếm ngược 2s chuyển sang `/messages`. Nhắn tin bạn bè gửi 100% qua WebSocket `/ws/direct/{friend_id}` (kênh `hust:v1:channel:dm:{low}_{high}`), lưu vĩnh viễn vào bảng `direct_messages`.

## Các lệnh thường dùng (Chạy từ thư mục gốc `project_1`)
```powershell
# Khởi chạy hạ tầng local (MySQL port 3307->3306, Redis port 6379, Mailpit port 1025/8025)
docker compose up -d

# Chạy migration database
cd backend; .\backend\.venv\Scripts\python.exe -m alembic upgrade head # hoặc từ trong backend/: .\.venv\Scripts\python.exe -m alembic upgrade head

# Chạy Backend dev server (từ thư mục backend/)
cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Chạy Frontend dev server (tự động proxy /api và /ws sang cổng 8000)
npm --prefix frontend run dev

# Chạy toàn bộ Unit Test Backend (từ thư mục gốc nhờ pytest.ini)
.\backend\.venv\Scripts\python.exe -m pytest -v

# Chạy Unit Test & Build Frontend
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

## Quy tắc cốt lõi (Bắt buộc tuân thủ)
- **Bảo mật Email & Quyền riêng tư**: Chỉ chấp nhận `@sis.hust.edu.vn`. Lưu song song `email` (để hiển thị khi đã là bạn bè `accepted`) và `email_hash` (HMAC-SHA256 để rate-limit/OTP). Trong phòng chat ẩn danh, `opponent.email` luôn phải là `None`.
- **Quản lý cấu hình & Bí mật**: Mọi secret đọc qua `backend/app/core/config.py`. Production bắt buộc khai báo đủ biến môi trường, secret >= 32 bytes, `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none`.
- **Chính sách Redis**: Trên `production`, mọi sự cố mất kết nối Redis phải **Fail-Fast trả về HTTP 503 (`RedisUnavailable`)**; chỉ dùng fallback in-memory ở `development`/`test`.
- **Thao tác Git**: Không tự ý `git commit` hoặc `git push` khi chưa có yêu cầu rõ ràng từ người dùng.

## Bản đồ Tài liệu AI Harness (3 Tầng)
- **Tầng 1 (Guardrails theo thư mục)**: `backend/CLAUDE.md`, `frontend/CLAUDE.md`, `db/CLAUDE.md`
- **Tầng 2 (Single Source of Truth)**:
  - Kiến trúc, Danh mục API & Bảng Redis Keys: `docs/ARCHITECTURE.md`
  - Kịch bản 7 luồng nghiệp vụ tuần tự: `docs/SYSTEM_FLOWS.md`
  - Cấu trúc 5 bảng DB & Mermaid ERD: `db/schema.md`
  - Các quyết định kiến trúc (ADR-016 → ADR-021): `docs/DECISIONS.md`
- **Tầng 3 (Vận hành & Gỡ lỗi)**:
  - Trạng thái hoàn thành & Kiểm thử: `docs/PROGRESS.md`
  - Lộ trình Backlog Sprint 2 & 3: `docs/PLAN.md`
  - Sổ tay 16 lỗi thực chiến & Cách xử lý: `docs/TROUBLESHOOTING.md`
  - Hướng dẫn Deploy Cloud & Lưu ý SMTP: `docs/DEPLOY.md`

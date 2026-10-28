# Tiến độ & nhật ký quá trình

> Cập nhật checkbox sau mỗi task; ghi nhật ký ngắn ở cuối. Đây là nguồn trạng
> thái của repo. T-xx khớp backlog dự án.

## Trạng thái hiện tại
- **Sprint đang chạy:** Sprint 1 – MVP chạy trên Internet & Bảo mật Vận hành
- **Hoàn thành nổi bật:** Hoàn tất bảo mật OTP HMAC domain separation, gỡ PII khỏi log/Redis, synchronous matching với atomic Lua reservation, 60s timeout contract, Redis Pub/Sub đa instance, `/health` readiness và `/live` liveness probes, Alembic backfill migration.
- **Bị chặn bởi:** Không có.
- **Bản deploy:** Frontend: (Vercel) · Backend: (Render) · Aiven / Upstash

## Tổng quan các Sprint
| Sprint | Mục tiêu | Trạng thái |
|---|---|---|
| 1 | Đăng nhập OTP/Password, hồ sơ K63-K71, matching 3 bộ lọc, chat realtime, DM & Kết bạn, bảo mật Redis & probes | Hoàn tất nền tảng cốt lõi |
| 2 | Report sau khi kết thúc chat, moderation/trust score, blocking | Kế hoạch |
| 3 | Chatbot HUST Buddy (RAG), nối vào luồng "phòng trống" | Chưa bắt đầu |
| 4 | Semantic Cache/Intent/Guided Flow | Chưa bắt đầu |
| 5 | Bảo mật nâng cao, load test, sao lưu định kỳ, beta rộng | Chưa bắt đầu |

## Sprint 1 – Checklist theo ngày
`[ ]` chưa làm · `[x]` hoàn tất.

### Ngày 1 – Khởi động
- [x] T-01 Tạo repo GitHub, nhánh main/dev, .gitignore, README.
- [x] T-02 Docker Compose MySQL + Redis (+ Mailpit), .env.example (1.5h)
- [x] T-03 Khung FastAPI: routers/services/core, /health, /live, đọc biến môi trường (2h)
- [x] T-04 Khung frontend: Vite + React + Tailwind + Router + Zustand (2h)
- [x] T-05 Cấu hình Aiven SSL trong db.py/env.py (1.5h)
- [x] T-06 ERD, model SQLAlchemy users/profiles/conversations/friendships/direct_messages, migration Alembic đầu (3h)

### Ngày 2 – Đăng nhập OTP (backend)
- [x] T-07 Chuẩn hóa email + kiểm tra tên miền chính xác `@sis.hust.edu.vn` + test (1h)
- [x] T-08 API request-otp: sinh OTP (secrets), HMAC domain separation, lưu Redis TTL 5 phút (2h)
- [x] T-09 Cooldown 60s, tối đa 5 lần thử sai, rate limiting IP & email HMAC (2h)
- [x] T-10 Gửi email OTP nền; log sạch PII (3h)
- [x] T-11 API verify-otp: tạo user, email_hash, nickname (2h)
- [x] T-12 JWT cookie HttpOnly; /me, /logout; get_current_user (2h)
- [x] T-13 pytest cho luồng OTP và Auth (test_auth.py) (1.5h)

### Ngày 3 – Giao diện đăng nhập, Onboarding, deploy sớm
- [x] T-14 UI đăng nhập, đăng ký, quên mật khẩu (Login.jsx, Register.jsx, ResetPassword.jsx) (3h)
- [x] T-15 ProtectedRoute + kho user (Zustand) + gọi /me (1.5h)
- [x] T-16 Onboarding: Giới tính, Ngành học (68 ngành HUST), Khóa K63-K71 (Onboarding.jsx)
- [x] T-17 Cấu hình deploy backend lên Render (2h)
- [x] T-18 Cấu hình migration lên Aiven qua Render Start Command (1.5h)
- [x] T-19 Cấu hình deploy frontend lên Vercel (1.5h)
- [x] T-20 CORS + cookie cross-site và Vercel routing (2h)

### Ngày 4 – Chat realtime & Kết bạn
- [x] T-21 WebSocket /ws/{room}: xác thực JWT, kiểm tra thuộc phòng (3h)
- [x] T-22 Broadcast tin nhắn qua Redis Pub/Sub; giới hạn 1000 ký tự (3h)
- [x] T-23 Model/API conversations: tạo/kết thúc phòng; đặt `ended_at` (1.5h)
- [x] T-24 UI khung chat: bong bóng, auto-scroll, Enter gửi (Chat.jsx) (3h)
- [x] T-25 Client WebSocket hiển thị thông báo đối phương tham gia/rời (2h)
- [x] T-26 Kết bạn & Direct Messages: gửi lời mời, tiết lộ danh tính, chat 1-1 (Friends.jsx) (2h)

### Ngày 5 – Ghép cặp & Bảo mật Hệ thống
- [x] T-27 Matching 3 bộ lọc cứng hai chiều (matching.py + unit tests)
- [x] T-28 Hàng đợi Redis/Store: /match/join, /match/leave, /match/status, attempt_id (2h)
- [x] T-29 Ghép cặp đồng bộ (synchronous join) với Redis Lua script đặt chỗ nguyên tử, thay thế worker nền chu kỳ (3.5h)
- [x] T-30 Timeout 60s: trạng thái terminal `not_found`, retry attempt, UI xử lý thử lại hoặc đổi tiêu chí (1h)
- [x] T-31 UI "Đang tìm người phù hợp…" + tự vào phòng chat + xử lý timeout/hủy tìm kiếm (Matching.jsx) (2.5h)
- [ ] T-32 Script sinh 100 user giả đo thời gian ghép (1.5h) *(Could)*

### Ngày 6 – Tích hợp & deploy chính thức
- [ ] T-33 Deploy production lần 2: biến môi trường, wss://, xác thực WebSocket (2.5h)
- [ ] T-34 Test end-to-end: điện thoại 4G + laptop (2h)
- [ ] T-35 Sửa lỗi cookie/CORS/WebSocket khi deploy (3h)
- [x] T-36 Xử lý Render spin-down: probe `/health` readiness (DB + Redis) & `/live` liveness (1.5h)
- [x] T-37 Bảo mật: không lộ secret, CORS chặt, rate limit IP/email, chống account enumeration (1.5h)
- [ ] T-38 Trang "Quyền riêng tư" + checkbox đồng ý (1h) *(Should)*

### Ngày 7 – Beta, demo, retro
- [ ] T-39 Beta nhỏ 5–10 bạn, thu phản hồi (2h)
- [ ] T-40 Sửa lỗi ưu tiên cao từ beta (3h)
- [ ] T-41 README: chạy local + deploy + sơ đồ kiến trúc (1.5h)
- [ ] T-42 Sprint Review + Retrospective + chốt backlog Sprint 2 (1.5h)

## Kế hoạch tiếp theo
- [x] P-01 Chuẩn hóa catalog thành CSV seed; 68 mã duy nhất và 10 đơn vị.
- [x] P-02 Chốt contract questionnaire; 3 bộ lọc cứng hai chiều.
- [x] P-03 Migration schema: users, profiles, conversations, friendships, direct_messages.
- [x] P-04 API profile và UI onboarding theo 68 ngành & K63-K71.
- [x] P-05 Matching hai chiều: `is_mutual_match` với 3 bộ lọc cứng.
- [x] P-06 Ghép đôi đồng bộ, atomic Lua reservation, attempt lifecycle và timeout 60s.
- [ ] P-07/P-08 Report trong 30 phút sau khi kết thúc chat; Redis buffer 1 MiB; DB evidence mã hóa TTL 30 phút.
- [ ] P-09/P-10 Thu thập dữ liệu report (placeholder 50), trust/ban, quota, block, appeals.
- [ ] P-11 Test tích hợp, migration/rollback, kiểm tra riêng tư và rollout.

## Nhật ký

### Bảo mật OTP, matching đồng bộ và vận hành Redis – 28/10/2026
- **Giai đoạn 1 (Bảo mật OTP & Email)**:
  - Tách `EMAIL_HASH_SECRET` khỏi `OTP_SECRET`; sinh HMAC OTP có domain separation (`hust:otp:{purpose}:{otp}`).
  - Redis key cho OTP và cooldown dựa strictly trên HMAC email (`users.email_hash`), không lưu email thô trong Redis.
  - Xóa sạch raw email và OTP khỏi application logs; sanitize exception của SMTP.
  - Chống account enumeration: API trả về thông báo trung tính giống nhau (`"Nếu địa chỉ hợp lệ, mã xác nhận sẽ được gửi."`) bất kể email có tài khoản hay không.
  - Bổ sung rate limiting theo IP và HMAC email; hỗ trợ reverse proxy tin cậy qua `get_client_ip`.
  - Tạo migration Alembic `0002_backfill_email_hash.py` để cập nhật `email_hash` trong DB an toàn.
- **Giai đoạn 2 (Kết thúc match sau 60 giây)**:
  - Thiết lập contract trạng thái `waiting | matched | not_found | idle` kèm `attempt_id`.
  - Quét ứng viên đồng bộ tại `POST /match/join`, khóa nguyên tử ứng viên bằng Lua script (`RESERVE_CANDIDATE_LUA`) trên Redis, loại bỏ hoàn toàn worker nền chu kỳ (T-29).
  - Timeout 60s kích hoạt trạng thái terminal `not_found`; frontend `Matching.jsx` dừng đếm giờ, hiển thị nút "Thử lại ngay" (tạo attempt mới) và "Đổi tiêu chí tìm kiếm".
- **Giai đoạn 3 (Redis làm shared state)**:
  - Thiết kế lại `StoreService` sử dụng Redis tập trung cho OTP, cooldown, rate limiting, queue và kết quả matching; in-memory chỉ dùng fallback cho dev/test.
  - Sử dụng Redis Pub/Sub đa instance cho room chat và Direct Messages WebSocket; quản lý đóng mở qua FastAPI lifespan.
- **Giai đoạn 4 (Health Checks & Docs)**:
  - Nâng cấp `/health` thành readiness probe chẩn đoán kiểm tra DB (`SELECT 1`) và Redis (`PING`), trả về 503 khi lỗi và phản hồi sanitized.
  - Bổ sung `/live` cho liveness probe.
  - Đồng bộ toàn bộ tài liệu: `CLAUDE.md`, `backend/CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/SYSTEM_FLOWS.md`, `docs/PLAN.md`.
  - Kiểm thử đạt 29/29 pytest backend và build frontend Vite production thành công.

### Bổ sung kiểm soát auth, friendship và trust quota – 28/10/2026
- Production từ chối secret mặc định/placeholder; dev dùng secret ngẫu nhiên
  theo process. Cấu hình login throttling 10 lần/email/15 phút.
- Friendship lưu requester và trạng thái pending; chỉ đúng người nhận được
  chấp thuận/từ chối, email chỉ tiết lộ sau khi accept.
- WebSocket dùng allowlist Origin; JWT hết hạn được kiểm tra khi decode; user
  banned hoặc trust score <= 0 bị từ chối ở HTTP/matching/WebSocket.
- Enforce trust quota theo ngày UTC+7 và một conversation hoạt động/user.
- Chuẩn hóa response khi SMTP lỗi để không phân biệt trạng thái tài khoản.
- Bảo vệ ghép đồng thời bằng khóa user theo thứ tự ID và locking reads cho
  quota/active conversation.
- Kiểm tra: 38/38 backend tests pass; Alembic có một head (`0003_friendship_requester`).

### Rà soát cấu hình chạy – 28/10/2026
- Tách `.env.example` gốc cho Docker Compose; backend mặc định gửi OTP vào Mailpit local; đồng bộ tên biến SMTP trong hướng dẫn deploy.
- Xác minh `docker compose config`, backend pytest và Vite production build đều đạt.


### Sẵn sàng Production: Xử lý Redis Outage, Thu hồi phiên & Giới hạn WebSocket – 28/10/2026
- **Xử lý sự cố Redis (Outage Fail-Fast)**:
  - Ở production (`ENVIRONMENT=production`), `StoreService` kích hoạt `RedisUnavailable` khi mất kết nối Redis, được bọc qua Exception Handler toàn cục trả về **HTTP 503 Service Unavailable** (`Service temporarily unavailable due to shared storage outage. Please retry shortly.`).
  - Tránh nguy cơ mất đồng bộ và rò rỉ matching state giữa các instance khi fallback in-memory ở production.
- **Thu hồi phiên đăng nhập (Session Revocation)**:
  - Bổ sung `iat` và `jti` cho mọi JWT access token.
  - Tích hợp kiểm tra phiên hoạt động `is_session_active(user_id, jti)` trong middleware xác thực `get_current_user` và handshake WebSocket.
  - `POST /auth/logout` tự động thu hồi session `jti` trên Redis (`revoke_session`).
  - `POST /auth/reset-password` tự động thu hồi toàn bộ phiên đang mở của tài khoản (`revoke_user_sessions`) trước khi cấp token mới.
  - Phân định rõ ràng: Banned user bị chặn tham gia ghép cặp (`/match/join`), không thu hồi JWT đăng nhập để người dùng vẫn xem được hồ sơ.
- **Giới hạn kết nối WebSocket (WebSocket Rate Limit)**:
  - Khống chế tối đa 3 kết nối đồng thời / tài khoản (`MAX_WS_CONNECTIONS_PER_USER`) và 10 kết nối / IP (`MAX_WS_CONNECTIONS_PER_IP`).
  - Đảm bảo giải phóng vị trí (slot) an toàn trong khối `finally` ngay khi socket ngắt kết nối.
- **Kiểm thử & Xác minh**:
  - Đạt 45/45 unit tests pass trong `backend/tests` (bao gồm các test case cho session revocation, ws slot limits, và production 503 outage).
  - 3/3 frontend tests pass.
  - Alembic duy trì một head duy nhất (`0003_friendship_requester`).

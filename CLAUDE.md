# HUST Chatbox

Nguồn trạng thái: [docs/PROGRESS.md](docs/PROGRESS.md). Đọc file hướng dẫn
trong thư mục trước khi sửa backend, frontend hoặc database.

## Sản phẩm và công nghệ
Chat ẩn danh 1–1 cho sinh viên HUST: email OTP, hồ sơ K63–K71, 3 bộ lọc cứng và
chat realtime. Stack: React/Vite, FastAPI/Python 3.12, SQLAlchemy async,
MySQL, Redis Pub/Sub, Mailpit/SMTP Gmail. Triển khai Render, Vercel và Aiven/Upstash.

Ưu tiên code đơn giản, dễ đọc, type hints và chú thích tiếng Việt khi cần.
Nghiệp vụ nằm trong `services/`; route chỉ điều phối.

## Phạm vi
- Hoàn thành: Email/password auth, OTP xác thực sinh viên (@sis.hust.edu.vn), hồ sơ K63–K71, 3 bộ lọc cứng, matching đồng bộ 60s timeout, chat realtime qua Redis Pub/Sub, kết bạn & Direct Messages, `/health` readiness & `/live` liveness probes.
- Tiếp theo: report/trust, HUST Buddy.
- Không thêm Microsoft Entra ID, kiểm duyệt từng tin nhắn hoặc lưu lịch sử
  chat phòng ẩn danh lâu dài.

## Lệnh local
```powershell
docker compose up -d
cd backend; python -m uvicorn app.main:app --reload
cd backend; python -m pytest
cd frontend; npm run dev
```
API readiness: `http://localhost:8000/health`; Liveness: `http://localhost:8000/live`; Mailpit: `http://localhost:8025`.
Chi tiết cài đặt: [README.md](README.md).

## Bảo mật bắt buộc
- Không commit `.env`, mật khẩu, khóa hoặc CA certificate.
- OTP dùng `secrets`, HMAC có domain separation (`hust:otp:{purpose}:{otp}`), chỉ lưu HMAC trong Redis (TTL 5 phút, dùng một lần);
  cooldown 60 giây, tối đa 5 lần thử sai; rate limit theo IP và HMAC email.
- Chỉ chấp nhận email sinh viên domain chính xác `@sis.hust.edu.vn`.
- Email thô được lưu trong DB theo ADR-018 phục vụ đăng nhập, khôi phục mật khẩu và chia sẻ danh tính khi kết bạn thành công.
- Tuyệt đối không log email thô hoặc OTP; không dùng email thô làm Redis key (dùng `EMAIL_HASH_SECRET`).
- Chống account enumeration: API phản hồi thông báo trung tính giống nhau cho email có hay không có tài khoản.
- Đăng nhập giới hạn 10 lần sai/email trong 15 phút; thành công thì xóa bộ đếm.
- Production phải cấu hình secrets, DB/Redis, SMTP, frontend origin và cookie
  an toàn; secret ngẫu nhiên mặc định chỉ dành cho dev.
- JWT dùng cookie `HttpOnly`, `Secure`, `SameSite`; không dùng `localStorage`.
- Logout thu hồi session `jti`; Reset password thu hồi toàn bộ phiên tài khoản trên Redis.
- Xác thực JWT, session allowlist và quyền thuộc phòng trước khi chấp nhận WebSocket;
  giới hạn tối đa 3 kết nối WebSocket / user và 10 kết nối / IP.
- Production fail-fast HTTP 503 khi Redis outage; không fallback in-memory ở production.
- WebSocket phải kiểm tra `Origin` theo allowlist; lời mời kết bạn phải ở trạng
  thái `pending` và chỉ người nhận được accept/decline.
- Không render HTML tin nhắn; CORS chỉ cho origin được phép.
- Kiểm tra mọi quyền ở backend.

## Quy trình
- Đọc `PROGRESS.md` và hướng dẫn liên quan; làm đúng một task, chạy kiểm thử.
- Ghi trạng thái vào `docs/PROGRESS.md`, quyết định vào `docs/DECISIONS.md`,
  lỗi khó vào `docs/TROUBLESHOOTING.md`.
- Không thêm dependency nếu chưa cần; ghi lý do khi thêm.
- Commit theo tiền tố `feat:`, `fix:`, `docs:`, `test:` hoặc `chore:`.

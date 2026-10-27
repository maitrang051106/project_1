# HUST Chatbox

Nguồn trạng thái: [docs/PROGRESS.md](docs/PROGRESS.md). Đọc file hướng dẫn
trong thư mục trước khi sửa backend, frontend hoặc database.

## Sản phẩm và công nghệ
Chat ẩn danh 1–1 cho sinh viên HUST: email OTP, hồ sơ K63–K71, 3 bộ lọc cứng và
chat realtime. Stack: React/Vite, FastAPI/Python 3.12, SQLAlchemy async,
MySQL, Redis Pub/Sub, Mailpit. Thử nghiệm deploy trên Render, Vercel và Aiven.

Ưu tiên code đơn giản, dễ đọc, type hints và chú thích tiếng Việt khi cần.
Nghiệp vụ nằm trong `services/`; route chỉ điều phối.

## Phạm vi
- MVP: OTP, hồ sơ, matching, chat realtime và deploy.
- Tiếp theo: report/trust, HUST Buddy, Identity Reveal.
- Không thêm Microsoft Entra ID, kiểm duyệt từng tin nhắn hoặc lưu lịch sử
  chat lâu dài. Evidence chỉ được lưu mã hóa sau report hợp lệ và hết hạn sau
  30 phút; xem [DECISIONS.md](docs/DECISIONS.md).

## Lệnh local
```powershell
docker compose up -d
cd backend; python -m uvicorn app.main:app --reload
cd backend; python -m pytest
cd frontend; npm run dev
```
API: `http://localhost:8000/health`; Mailpit: `http://localhost:8025`.
Chi tiết cài đặt: [README.md](README.md).

## Bảo mật bắt buộc
- Không commit `.env`, mật khẩu, khóa hoặc CA certificate.
- OTP dùng `secrets`, chỉ lưu HMAC trong Redis (TTL 5 phút, dùng một lần);
  cooldown 60 giây, tối đa 5 lần thử sai và rate limit theo IP.
- Chỉ chấp nhận domain chính xác `hust.edu.vn` hoặc `sis.hust.edu.vn`.
- Không lưu email thô hoặc ghi OTP/email đầy đủ vào log.
- JWT dùng cookie `HttpOnly`, `Secure`, `SameSite`; không dùng `localStorage`.
- Xác thực JWT và quyền thuộc phòng trước khi chấp nhận WebSocket.
- Không render HTML tin nhắn; CORS chỉ cho origin được phép.
- Kiểm tra mọi quyền ở backend.

## Quy trình
- Đọc `PROGRESS.md` và hướng dẫn liên quan; làm đúng một task, chạy kiểm thử.
- Ghi trạng thái vào `docs/PROGRESS.md`, quyết định vào `docs/DECISIONS.md`,
  lỗi khó vào `docs/TROUBLESHOOTING.md`.
- Không thêm dependency nếu chưa cần; ghi lý do khi thêm.
- Commit theo tiền tố `feat:`, `fix:`, `docs:`, `test:` hoặc `chore:`.

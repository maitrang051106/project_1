# Backend – FastAPI

Đọc hướng dẫn gốc [../CLAUDE.md](../CLAUDE.md). Tài liệu chuẩn: [roadmap](../docs/PLAN.md), [tiến độ](../docs/PROGRESS.md).

## Quy tắc triển khai
- Route xác thực/điều phối; nghiệp vụ đặt trong `services/`.
- Dùng async nhất quán; không chạy tác vụ blocking trong route async.
- Gửi email nền; lỗi và log được lọc sạch, không tiết lộ email/OTP hoặc chi tiết exception.
- Lỗi API ngắn gọn, chống account enumeration (dùng thông báo trung tính cho mọi trường hợp).
- Production không được dùng secret mặc định; yêu cầu cấu hình DB/Redis, SMTP,
  origin và cookie `Secure`/`SameSite=None`. Dev mới dùng secret tạm thời.
- Login giới hạn 10 lần sai/email trong 15 phút; thành công thì xóa bộ đếm.
- Chạy app từ `backend/`: `python -m uvicorn app.main:app --reload`.

## Bảo mật Email & OTP
- Chuẩn hóa email, so khớp domain chính xác `@sis.hust.edu.vn`.
- Email thô được lưu trong MySQL theo ADR-018 để đăng nhập, reset password và tiết lộ danh tính khi kết bạn.
- Băm email bằng `EMAIL_HASH_SECRET` để định danh trong Redis và bảng `users.email_hash`.
- OTP 6 số sinh bằng `secrets`, băm HMAC có domain separation (`hust:otp:{purpose}:{otp}`).
- Redis lưu HMAC OTP với TTL 300 giây, dùng một lần; cooldown 60 giây; tối đa 5 lần thử sai; rate limit theo IP và HMAC email. So sánh bằng `hmac.compare_digest`.
- JWT cookie có `HttpOnly`, `Secure`, `SameSite`; không ghi bí mật vào log.
  Logout thu hồi session `jti`; Reset password thu hồi toàn bộ session của tài khoản trên Redis.
- Production fail-fast HTTP 503 (`RedisUnavailable`) khi Redis outage; không fallback in-memory ở production.
- WebSocket giới hạn tối đa 3 kết nối / user và 10 kết nối / IP.

## Chat và ghép cặp
- Matching đồng bộ tại `POST /match/join`: không dùng worker chạy nền.
- Thời gian chờ ghép tối đa 60 giây. Trạng thái gồm `waiting | matched | not_found | idle`, có `attempt_id` phân lập từng lượt.
- Đặt chỗ candidate nguyên tử (atomic reservation) qua Lua script trên Redis để chống ghép trùng đồng thời.
- Khi hết hạn 60 giây, kết quả `not_found` được lưu tạm thời, giao diện hiển thị tùy chọn "Thử lại ngay" hoặc "Đổi tiêu chí".
- WebSocket xác thực JWT và quyền phòng trước `accept()`. Giới hạn tin nhắn 1000 ký tự; dùng Redis Pub/Sub đa phiên bản để broadcast realtime.
- WebSocket chỉ nhận `Origin` trong allowlist. Friendship lưu requester + `pending`;
  chỉ người nhận lời mời được chấp thuận và làm lộ email.
- Matching áp quota/ngày Việt Nam theo trust: `>=90` không giới hạn, `70-89` là 5,
  `50-69` là 3, `1-49` là 1, `<=0` không được match; một chat hoạt động/user.

## Health Check & Triển khai
- Readiness probe `/health`: kiểm tra DB (`SELECT 1`) và Redis (`PING`), trả 503 khi thành phần bắt buộc lỗi, response sanitized không lộ URL hay mật khẩu.
- Liveness probe `/live`: kiểm tra trạng thái tiến trình web.
- Lifespan quản lý kết nối và đóng Redis client chuẩn xác.
- Deploy Render: Root `backend`; build `pip install -r requirements.txt`;
  start `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`;
  health check `/health`.

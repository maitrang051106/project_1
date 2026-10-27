# Deploy thử nghiệm

Giới hạn nhà cung cấp thay đổi; kiểm tra trước khi triển khai.

## MySQL – Aiven
- Tạo database, lưu URL/credential/CA trong secret môi trường; bật SSL.
- Kết nối thử rồi chạy migration từ `backend/`: `python -m alembic upgrade head`.
- Sao lưu và kiểm tra migration trước khi chạy trên dữ liệu thật.

## Backend – Render
- Root: `backend`; build: `pip install -r requirements.txt`.
- Start: `python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`.
- Health check: `/health`.
- Cấu hình `DATABASE_URL`, `REDIS_URL`, `OTP_SECRET`, `JWT_SECRET`,
  `EMAIL_*`/`SMTP_*`, `FRONTEND_ORIGIN`, `COOKIE_SECURE`, `COOKIE_SAMESITE`.
- Xác nhận dịch vụ Redis hỗ trợ Pub/Sub và kiểm tra giới hạn gói hiện tại.

## Frontend – Vercel
- Root: `frontend`; build `npm run build`; output `dist`.
- Đặt `VITE_API_URL=https://<backend>` và `VITE_WS_URL=wss://<backend>`.
  Cập nhật biến cần build/deploy lại.

## Kết nối và kiểm thử
- CORS chỉ cho `FRONTEND_ORIGIN`, bật credentials; không dùng `*`.
- Cookie cross-site cần `SameSite=None; Secure`; trình duyệt có thể chặn cookie
  bên thứ ba. Cân nhắc rewrite `/api` để dùng cùng site.
- WebSocket phải xác thực người dùng và membership phía backend.
- Kiểm tra luồng OTP → matching → chat trên hai thiết bị/mạng khác nhau.

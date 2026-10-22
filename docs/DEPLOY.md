# Hướng dẫn deploy: Aiven → Render → Vercel

> Giới hạn gói miễn phí có thể thay đổi; kiểm tra trên trang chính thức trước khi dựa vào.

## 1. Aiven (MySQL)
1. Tạo dịch vụ MySQL gói Free. Lấy host, port, user, password, CA certificate.
2. Thử kết nối bằng `mysql` client (SSL) từ máy local.
3. Đặt `DATABASE_URL` (theo driver async bạn dùng, kèm tham số SSL) trong biến môi trường.
4. Chạy `alembic upgrade head` trỏ vào Aiven; kiểm tra bảng đã tạo.

## 2. Render (backend)
- Web Service từ GitHub, **Root Directory = `backend`**.
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`
- Health Check Path: `/health`
- Redis: tạo Render Key Value hoặc dịch vụ Redis khác → `REDIS_URL` (kiểm tra giới hạn và hỗ trợ Pub/Sub).
- Biến môi trường: `DATABASE_URL`, `REDIS_URL`, `OTP_SECRET`, `JWT_SECRET`, `EMAIL_*`/`SMTP_*`, `FRONTEND_ORIGIN`, `COOKIE_SECURE`, `COOKIE_SAMESITE`.
- Lưu ý: gói free tự tắt sau 15 phút không có lưu lượng, bật lại mất khoảng 1 phút; ổ đĩa tạm thời.

## 3. Vercel (frontend)
- Import repo, **Root Directory = `frontend`**, Framework Vite; Build `npm run build`; Output `dist`.
- Biến môi trường: `VITE_API_URL=https://<backend>.onrender.com`, `VITE_WS_URL=wss://<backend>.onrender.com`; đổi biến xong phải Redeploy.
- `vercel.json`: rewrite mọi đường dẫn về `/index.html`; có thể thêm rewrite `/api/*` sang backend để cookie cùng site.

## 4. Nối ghép (lỗi hay gặp nhất)
- **CORS:** `allow_origins=[FRONTEND_ORIGIN]` (không `*`), `allow_credentials=True`.
- **Cookie khác tên miền:** `SameSite=None; Secure` (một số trình duyệt chặn cookie khác site → ưu tiên rewrite `/api`).
- **WebSocket:** kết nối thẳng `wss://<backend>…`; cookie của Vercel không đi kèm nên cần xác thực bằng token (query/tin đầu tiên) và kiểm tra ở backend.
- **Kiểm thử cuối:** điện thoại dùng 4G + laptop khác mạng: đăng nhập OTP → ghép → chat.

## 5. Nhật ký deploy
| Ngày | Môi trường | Việc làm | Kết quả / lỗi |
|---|---|---|---|
| | | | |

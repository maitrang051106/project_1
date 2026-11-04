# Hướng dẫn Triển khai Cloud (Deployment Guide)

Dự án **HUST Match** được thiết kế để triển khai theo mô hình tách biệt:
- **Frontend**: Vercel (Static Vite SPA)
- **Backend**: Render Web Service (Python 3.11 + FastAPI + Uvicorn)
- **Database**: Aiven for MySQL (hoặc Managed MySQL 8.0)
- **Cache / PubSub**: Render Key Value / Upstash Redis

---

## 1. Triển khai Backend trên Render

### Cấu hình Dịch vụ (Service Settings)
- **Root Directory**: `backend`
- **Runtime**: `Python 3` (đảm bảo có file `backend/.python-version` ghi `3.11.9` hoặc đặt biến `PYTHON_VERSION=3.11.9`).
- **Build Command**:
  ```bash
  pip install -r requirements.txt && alembic upgrade head
  ```
- **Start Command**:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
  *(Lưu ý: `requirements.txt` bắt buộc dùng `uvicorn[standard]==0.34.0` và `websockets>=12.0` để hỗ trợ kết nối WebSocket `/ws/*`)*.

### Biến Môi trường Bắt buộc trên Production (`ENVIRONMENT=production`)
Khi đặt `ENVIRONMENT=production`, bộ kiểm tra trong `backend/app/core/config.py` sẽ từ chối khởi động nếu thiếu bất kỳ biến nào dưới đây:
- `ENVIRONMENT=production`
- `DATABASE_URL`: Chuỗi kết nối MySQL (hệ thống tự động chuyển `mysql://` thành `mysql+aiomysql://` và tự bật TLS cho `aivencloud.com`).
- `REDIS_URL`: Chuỗi kết nối Redis (`redis://...` hoặc `rediss://...`). Trên production, nếu mất Redis hệ thống sẽ trả về HTTP `503 Service Unavailable`.
- `OTP_SECRET`, `EMAIL_HASH_SECRET`, `JWT_SECRET`: Các chuỗi bí mật ngẫu nhiên dài **tối thiểu 32 bytes** (tuyệt đối không dùng chuỗi mặc định `replace-with...`).
- `FRONTEND_ORIGIN`: URL chính thức của Vercel (VD: `https://project-1-hust-chatbox.vercel.app`, không có dấu `/` ở cuối).
- `COOKIE_SECURE=true` và `COOKIE_SAMESITE=none` (bắt buộc để trình duyệt cho phép gửi cookie `HttpOnly` giữa domain Vercel và domain Render).
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM`, `EMAIL_USE_TLS`.

> [!WARNING]
> **Lưu ý quan trọng về cổng SMTP trên Render Free Tier**:
> Render đã **chặn hoàn toàn các cổng outbound SMTP (`25`, `465`, `587`)** đối với các Web Service thuộc gói **Free**. Do đó, kết nối `aiosmtplib` tới `smtp.gmail.com:587` sẽ bị timeout nếu chạy trên Render Free (dù chạy ở máy local hoặc VPS/Render Paid vẫn hoạt động bình thường). Nếu triển khai trên Render Free, cần nâng cấp instance hoặc tích hợp dịch vụ gửi mail qua cổng HTTPS `443` (như Resend/Brevo API, xem `docs/PLAN.md`).

---

## 2. Triển khai Frontend trên Vercel

- **Root Directory**: `frontend`
- **Framework Preset**: `Vite`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Biến Môi trường trên Vercel**:
  - `VITE_API_URL=https://<ten-service-backend>.onrender.com/api`
  - `VITE_WS_URL=wss://<ten-service-backend>.onrender.com`
- File `frontend/vercel.json` đã cấu hình sẵn rewrite SPA (`/(.*) -> /index.html`).

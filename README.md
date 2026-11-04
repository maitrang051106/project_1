# 🦅 HUST Match (HUST Chatbox)

Nền tảng ghép đôi ẩn danh 2 chiều và trò chuyện thời gian thực dành riêng cho sinh viên Đại học Bách Khoa Hà Nội (`@sis.hust.edu.vn`).

---

## ✨ Tính năng nổi bật (MVP Core)

1. **Xác thực Sinh viên Bách Khoa (`@sis.hust.edu.vn`)**:
   - Đăng ký tài khoản với mã OTP 6 số gửi qua email sinh viên, đăng nhập bằng mật khẩu (`PBKDF2-HMAC-SHA256`), quản lý phiên an toàn bằng JWT `HttpOnly` cookie và Redis Session Allowlist (`jti`).
2. **Hồ sơ Cá nhân & 68 Ngành đào tạo HUST 2026**:
   - Tùy chỉnh biệt danh (`nickname`), chọn 1 trong 11 linh vật thú (`🦉`, `🦊`, `🐼`...), chọn Giới tính, Khóa học (`K63`–`K71`) và **Cascading Dropdown Trường/Viện/Khoa → Ngành học**.
3. **Ghép đôi 2 Chiều Nguyên tử trong 60 Giây**:
   - Chỉ ghép đôi khi cả hai người dùng thỏa mãn đồng thời cả 3 tiêu chí lọc của nhau (Giới tính, Cùng ngành / Cùng trường khác ngành / Khác trường, Cùng khóa / Khóa trên / Khóa dưới).
   - Sử dụng Redis Lua Script chống tranh chấp (race condition) và kiểm tra hạn mức ghép đôi hàng ngày theo `trust_score`.
4. **Phòng Chat Ẩn danh Realtime & Khôi phục Lịch sử 24h**:
   - Trò chuyện ẩn danh qua WebSocket (`/ws/{room_id}`), bảo mật tuyệt đối địa chỉ email thật (`email: null`).
   - Tự động lưu lịch sử phòng chat trên Redis trong **24 giờ** để không mất tin nhắn khi F5 hoặc rớt mạng tạm thời; hỗ trợ cuộn xem lại tin nhắn cũ (cursor pagination).
5. **Kết bạn 2 Chiều & Nhắn tin Trực tiếp (`/messages`)**:
   - Gửi lời mời kết bạn ngay trong phòng chat ẩn danh; khi đối phương đồng ý, phòng ẩn danh tự động khép lại và chuyển tiếp sau 2 giây sang trang `/messages` để trò chuyện lâu dài qua `/ws/direct/{friend_id}`.

---

## 🚀 Hướng dẫn Chạy Dự án ở Máy Local

### 1. Khởi chạy Hạ tầng (MySQL 8.0, Redis 7, Mailpit)
```powershell
Copy-Item .env.example .env
docker compose up -d
```
- **MySQL**: `127.0.0.1:3307` (ánh xạ vào cổng `3306` trong container)
- **Redis**: `127.0.0.1:6379`
- **Mailpit (Xem email OTP khi test local)**: Mở trình duyệt tại `http://localhost:8025` (SMTP lắng nghe tại `127.0.0.1:1025`)

### 2. Khởi chạy Backend (FastAPI)
```powershell
cd backend
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 3. Khởi chạy Frontend (React + Vite)
```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```
Truy cập ứng dụng tại: `http://localhost:5173`

> [!TIP]
> **Mẹo kiểm thử ghép đôi & chat 2 tài khoản trên cùng 1 máy**:
> Vì hệ thống dùng cookie `access_token` (`HttpOnly`, `Path=/`), không nên đăng nhập 2 tài khoản trên 2 tab thường của cùng một trình duyệt (sẽ làm ghi đè cookie của nhau). Hãy mở **1 cửa sổ thường + 1 cửa sổ Ẩn danh (Incognito)** (hoặc 1 Chrome + 1 Edge) và cùng truy cập `http://localhost:5173`.

---

## 🧪 Chạy Kiểm thử Tự động (Automated Tests)

Từ thư mục gốc của dự án (`project_1`):
```powershell
# Chạy toàn bộ Unit Test của Backend (pytest tự nhận diện cấu hình qua pytest.ini)
.\backend\.venv\Scripts\python.exe -m pytest -v

# Chạy Unit Test và kiểm tra đóng gói Frontend
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

---

## 📚 Tài liệu Kiến trúc & Vận hành
- Tổng quan & Quy tắc dự án: [CLAUDE.md](file:///d:/laptrinh/fullstack/project_1/CLAUDE.md)
- Kiến trúc, Danh mục API & Bảng Redis Keys: [docs/ARCHITECTURE.md](file:///d:/laptrinh/fullstack/project_1/docs/ARCHITECTURE.md)
- Kịch bản 7 luồng nghiệp vụ tuần tự: [docs/SYSTEM_FLOWS.md](file:///d:/laptrinh/fullstack/project_1/docs/SYSTEM_FLOWS.md)
- Thiết kế Database & Sơ đồ ERD: [db/schema.md](file:///d:/laptrinh/fullstack/project_1/db/schema.md)
- Nhật ký Quyết định Kiến trúc (ADRs): [docs/DECISIONS.md](file:///d:/laptrinh/fullstack/project_1/docs/DECISIONS.md)
- Tiến độ & Lộ trình: [docs/PROGRESS.md](file:///d:/laptrinh/fullstack/project_1/docs/PROGRESS.md) | [docs/PLAN.md](file:///d:/laptrinh/fullstack/project_1/docs/PLAN.md)
- Sổ tay xử lý 16 lỗi thực chiến & Triển khai Cloud: [docs/TROUBLESHOOTING.md](file:///d:/laptrinh/fullstack/project_1/docs/TROUBLESHOOTING.md) | [docs/DEPLOY.md](file:///d:/laptrinh/fullstack/project_1/docs/DEPLOY.md)

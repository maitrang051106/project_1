# Hướng dẫn chạy thử dự án qua mạng LAN (FastAPI + React Vite)

Tài liệu này hướng dẫn chi tiết cách chạy backend FastAPI và frontend React (Vite) để các thiết bị khác trong cùng mạng WiFi/LAN (điện thoại, laptop khác) có thể truy cập và test trực tiếp.

**IP máy host hiện tại:** `192.168.1.163`

---

## 1. Mở cổng Windows Firewall (Chỉ cần làm 1 lần)

Mở **PowerShell (Run as Administrator)** và chạy 2 lệnh sau:

```powershell
New-NetFirewallRule -DisplayName "Dev FE 5173" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow
New-NetFirewallRule -DisplayName "Dev BE 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

> **Lưu ý:** Khi Windows Defender hiển thị popup hỏi quyền mạng cho Python / Node.js, hãy tích chọn **Private network**.

---

## 2. Khởi động Backend (FastAPI)

Mở Terminal 1, di chuyển vào thư mục `backend` và chạy uvicorn lắng nghe trên tất cả interface (`0.0.0.0`):

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* Backend Swagger Docs để kiểm tra nhanh: `http://192.168.1.163:8000/docs`
* CORS đã được cấu hình tự động chấp nhận dải IP LAN: `192.168.*.*`

---

## 3. Khởi động Frontend (React + Vite)

Mở Terminal 2, di chuyển vào thư mục `frontend`:

```powershell
cd frontend
npm run dev -- --host
```

*(Nếu PowerShell báo lỗi ExecutionPolicy chặn file `npm.ps1`, bạn có thể chạy bằng `npm.cmd run dev -- --host` hoặc mở Command Prompt CMD).*

Vite sẽ hiển thị:
```
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.1.163:5173/
```

### Cơ chế Proxy thông minh (Không lo dính CORS hay đổi IP)
- File `frontend/.env.development` đã cấu hình `VITE_DEV_API_TARGET=http://127.0.0.1:8000`.
- Khi điện thoại truy cập vào `http://192.168.1.163:5173`, mọi request `/api/*` và WebSocket `/ws/*` sẽ được máy tính của bạn tự động chuyển tiếp sang backend port 8000.

---

## 4. Truy cập trên điện thoại / thiết bị khác

1. Đảm bảo điện thoại kết nối **cùng mạng WiFi** với máy tính (`192.168.1.163`).
2. Mở trình duyệt trên điện thoại (Chrome / Safari):
   - Truy cập giao diện Web App: **`http://192.168.1.163:5173`**
   - Kiểm tra Backend kết nối: **`http://192.168.1.163:8000/docs`**

---

## 5. Bảng xử lý sự cố thường gặp (Troubleshooting)

| Triệu chứng | Nguyên nhân & Cách khắc phục |
|---|---|
| **Điện thoại không mở được web** | 1. Kiểm tra Firewall (chạy lại lệnh ở Bước 1).<br>2. Kiểm tra mạng WiFi trên Windows đang ở chế độ **Public** (cần đổi sang **Private** trong Windows Settings).<br>3. Router WiFi bật chế độ *AP Isolation* (cô lập thiết bị không cho nói chuyện nội bộ). |
| **Vào được web nhưng gọi API báo lỗi** | Kiểm tra Terminal Backend xem có log request không. Thử mở `http://192.168.1.163:8000/docs` trên điện thoại xem có lên không. |
| **WebSocket chat không kết nối** | Đảm bảo `vite.config.js` đã có proxy `/ws` với `ws: true` (đã được cấu hình sẵn trong dự án). |
| **IP máy tính thay đổi sau khi restart router** | Chạy `ipconfig` trong PowerShell để xem IPv4 mới, sau đó dùng IP mới để truy cập. |

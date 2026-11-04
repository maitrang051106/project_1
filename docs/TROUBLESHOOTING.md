# Sổ tay Xử lý Sự cố Thực chiến (Troubleshooting Guide)

Tài liệu này tổng hợp **16 lỗi thực tế** đã gặp trong suốt quá trình phát triển, kiểm thử và triển khai dự án **HUST Match** (từ 23/10 đến 04/11/2026), được phân thành 4 nhóm để tra cứu nhanh.

---

## Nhóm 1: Lỗi Môi trường Local, Windows & Công cụ Chạy Test

### 1. `ModuleNotFoundError: No module named 'app'` hoặc gọi nhầm Python hệ thống
- **Nguyên nhân**: Chạy `python -m pytest` hoặc `uvicorn` khi đang đứng ở thư mục gốc mà không qua `.venv` của `backend/`, hoặc trước đây thiếu `pytest.ini`.
- **Cách khắc phục**:
  - Dự án đã có sẵn `pytest.ini` (`pythonpath = backend`) ở thư mục gốc. Luôn gọi trình thông dịch trong `.venv`:
    ```powershell
    .\backend\.venv\Scripts\python.exe -m pytest -v
    ```
  - Khi chạy `uvicorn`, đứng tại `backend/`:
    ```powershell
    cd backend
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
    ```

### 2. Sửa code Backend nhưng chạy test E2E không thấy thay đổi (Zombie `uvicorn` trên cổng 8000)
- **Nguyên nhân**: Trên Windows, các tiến trình `uvicorn` bật ngầm từ các phiên trước không tự tắt, vẫn chiếm cổng `8000` và trả về code cũ.
- **Cách khắc phục**: Kiểm tra và tắt toàn bộ tiến trình đang giữ cổng `8000` trước khi bật server mới:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force }
  ```

### 3. Tự động đăng xuất hoặc nhảy nhầm tài khoản khi test 2 người trên cùng trình duyệt
- **Nguyên nhân**: Hệ thống xác thực bằng cookie `access_token` (`HttpOnly`, `Path=/`). Nếu mở 2 tab thường trên cùng một trình duyệt, việc đăng nhập ở Tab 2 sẽ ghi đè cookie của Tab 1. Ngoài ra, nếu mở 1 tab ở `localhost:5173` nhưng WebSocket lại gọi sang `127.0.0.1:8000`, trình duyệt sẽ không gửi kèm cookie của `localhost`.
- **Cách khắc phục**:
  - Khi test 2 tài khoản trên cùng 1 máy: Dùng **1 cửa sổ trình duyệt thường + 1 cửa sổ Ẩn danh (Incognito)** (hoặc 2 trình duyệt khác nhau như Chrome + Edge), cả hai cùng truy cập `http://localhost:5173`.
  - Ở `frontend/.env`, để trống `VITE_WS_URL` để hàm `buildWsUrl()` tự động đi qua proxy `/ws` của Vite trên cùng origin `localhost:5173`.

### 4. Lỗi `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`
- **Nguyên nhân**: Chạy `docker compose up -d` khi ứng dụng Docker Desktop trên Windows chưa được khởi동.
- **Cách khắc phục**: Mở Docker Desktop, đợi biểu tượng trạng thái chuyển sang màu xanh (Engine running) rồi chạy lại lệnh.

---

## Nhóm 2: Lỗi Database, SQLAlchemy Async & Dữ liệu Seed

### 5. `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`
- **Nguyên nhân**: Trong SQLAlchemy 2.0 Async, sau khi gọi `await db.commit()`, các thuộc tính của ORM object bị đánh dấu hết hạn (`expired`) hoặc chưa nạp quan hệ. Truy cập `user.profile` lúc này sẽ kích hoạt lazy-loading đồng bộ (implicit I/O) và làm crash tiến trình async.
- **Cách khắc phục**:
  - Giữ `expire_on_commit=False` trên `async_sessionmaker` tại `backend/app/core/db.py`.
  - Giữ `lazy="selectin"` trên quan hệ `User.profile` tại `backend/app/models/user.py` (hoặc dùng `.options(selectinload(User.profile))` trong câu truy vấn).

### 6. `TypeError: AsyncAdapt_aiomysql_connection.ping() missing 1 required positional argument: 'reconnect'`
- **Nguyên nhân**: Bật `pool_pre_ping=True` trong `create_async_engine()` khi dùng driver `aiomysql==0.2.0`.
- **Cách khắc phục**: Luôn giữ `pool_pre_ping=False` và `pool_recycle=3600` trong `backend/app/core/db.py`.

### 7. `RuntimeError: 'cryptography' package is required for sha256_password or caching_sha2_password`
- **Nguyên nhân**: MySQL 8.0 mặc định dùng chuẩn xác thực `caching_sha2_password`, yêu cầu thư viện `cryptography` khi kết nối qua `PyMySQL`/`aiomysql`.
- **Cách khắc phục**: Đảm bảo `cryptography>=42.0.0` luôn có trong `backend/requirements.txt`.

### 8. `KeyError: 'major_code'` khi đọc CSV & Frontend crash `Unexpected token 'I', "Internal S"...`
- **Nguyên nhân**: File `db/seed/hust-68-nganh-2026.csv` lưu từ Excel có ký tự ẩn **UTF-8 BOM (`\ufeff`)** ở đầu file khiến `csv.DictReader` đọc tên cột đầu tiên thành `'\ufeffmajor_code'`.
- **Cách khắc phục**: Luôn mở file CSV bằng `encoding="utf-8-sig"` và `.lstrip("\ufeff")` trong `backend/app/services/catalog.py`.

### 9. `DataError: (1406, "Data too long for column 'faculty_code' at row 1")`
- **Nguyên nhân**: Mã slug tiếng Anh của các Trường/Viện (VD: `school-of-information-and-communication-technology-soict`) dài tới 56 ký tự, vượt quá giới hạn `VARCHAR(20)` ban đầu.
- **Cách khắc phục**: Chạy `alembic upgrade head` để áp dụng bản migration `0004_expand_faculty_code.py` (`VARCHAR(100)`).

### 10. `TypeError: 'type' is an invalid keyword argument for Conversation`
- **Nguyên nhân**: Trong `backend/app/models/conversation.py`, cột SQL `"type"` được ánh xạ vào thuộc tính Python tên là `conversation_type` để tránh trùng từ khóa `type` của Python.
- **Cách khắc phục**: Luôn khởi tạo bằng `Conversation(user_a=..., user_b=..., conversation_type=ConversationType.HUMAN)`.

---

## Nhóm 3: Lỗi WebSocket, Rò rỉ Slot & Luồng OTP

### 11. WebSocket báo lỗi `404 Not Found` kèm `WARNING: Unsupported upgrade request`
- **Nguyên nhân**: Cài đặt gói `uvicorn` cơ bản mà thiếu phần mở rộng `[standard]` (`websockets` / `wsproto`).
- **Cách khắc phục**: Dùng `uvicorn[standard]==0.34.0` và `websockets>=12.0` trong `backend/requirements.txt`.

### 12. Kẹt kết nối WebSocket (`Maximum 3 concurrent WebSocket connections reached for this user`)
- **Nguyên nhân**: Trước đây `store_service.acquire_ws_slot()` được gọi *trước* bước kiểm tra `conv.ended_at is not None` hoặc `Friendship.status == "accepted"`. Khi phòng đã đóng hoặc chưa kết bạn, hàm `return` sớm mà không đi qua khối `finally: release_ws_slot()`, làm mất dần cả 3 slot của user trong Redis.
- **Cách khắc phục**:
  - Đã sửa triệt để ở cả `chat.py` và `direct_messages.py`: chỉ gọi `acquire_ws_slot` **sau khi** đã hoàn tất mọi bước kiểm tra DB.
  - Nếu cần xóa nhanh bộ đếm slot trong Redis local khi đang debug:
    ```powershell
    docker compose exec redis redis-cli KEYS "hust:v1:ws:*" | ForEach-Object { if ($_) { docker compose exec redis redis-cli DEL $_ } }
    ```

### 13. Gửi yêu cầu OTP đăng ký trả về `200 OK` nhưng Mailpit (`localhost:8025`) không có thư
- **Nguyên nhân**: Cơ chế **chống dò tài khoản (Anti-Enumeration)** trong `AuthService.request_register_otp`: nếu email đó đã được đăng ký (đã có `password_hash` trong bảng `users`), hệ thống cố ý trả về `200 OK` với thông báo chung nhưng không gửi mail OTP mới.
- **Cách khắc phục**: Chuyển sang tab **Sign In** (Đăng nhập) hoặc **Reset** (Quên mật khẩu), hoặc dùng một địa chỉ email `@sis.hust.edu.vn` mới chưa có trong bảng `users`.

---

## Nhóm 4: Lỗi Triển khai Cloud (Render / Aiven / Vercel)

### 14. Render báo lỗi `TypeError: descriptor '__getitem__' requires a 'typing.Union'` khi khởi tạo SQLAlchemy
- **Nguyên nhân**: Render tự chọn phiên bản Python 3.14 preview khi không có cấu hình ghim phiên bản, gây lỗi tương thích với SQLAlchemy 2.0.
- **Cách khắc phục**: Giữ file `.python-version` và `backend/.python-version` ở mức `3.11.9` (hoặc đặt biến môi trường `PYTHON_VERSION=3.11.9` trên Render).

### 15. Lỗi kết nối Aiven MySQL (`SSL Connection Refused` hoặc `SSLCertVerificationError`)
- **Nguyên nhân**: Aiven MySQL yêu cầu kết nối TLS bắt buộc nhưng sử dụng chứng chỉ CA tự ký (self-signed), và tham số `?ssl-mode=REQUIRED` trên chuỗi URL không được driver `aiomysql` hỗ trợ trực tiếp.
- **Cách khắc phục**: `config.py` đã tự động cắt bỏ `?ssl-mode=...` và `db.py` (`get_db_connect_args`) đã tự động gắn `SSLContext` (`CERT_NONE`) khi phát hiện host `aivencloud.com`.

### 16. Gửi email OTP bị timeout khi chạy trên Render Free Tier
- **Nguyên nhân**: **Render gói Free chặn hoàn toàn các kết nối mạng đi ra trên cổng SMTP (`25`, `465`, `587`)** để chống phát tán thư rác.
- **Cách khắc phục**: Xem hướng dẫn chi tiết tại `docs/DEPLOY.md` (sử dụng gói trả phí của Render hoặc chuyển sang dịch vụ gửi mail qua cổng HTTPS `443` như Resend/Brevo).

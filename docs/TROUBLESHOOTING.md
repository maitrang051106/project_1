# Khắc phục sự cố

Ghi lỗi thực tế mất hơn 15 phút theo mẫu: ngày/task, triệu chứng, nguyên nhân,
cách sửa và cách phòng tránh. Mục mới nhất đặt trên cùng.

| Triệu chứng | Kiểm tra |
|---|---|
| Mất phiên khi deploy | Cookie `SameSite`/`Secure`, CORS credentials, domain |
| WebSocket lỗi | `wss://`, xác thực, membership, trạng thái backend |
| Aiven không kết nối | SSL/CA, host/port, `connect_args={"ssl": True}` |
| Redis trả bytes | Dùng `decode_responses=True` |
| `VITE_*` cũ | Biến gắn lúc build; build/deploy lại trên Vercel |
| Vercel tải lại bị 404 | Rewrite SPA về `/index.html` trong `vercel.json` |
| OTP không đến | SMTP, SPF/DKIM, hộp thư đích |
| Render không tìm thấy module | Kiểm tra commit trên GitHub đã có thư viện trong `requirements.txt` chưa |

## Nhật ký

### 27/10/2026 – Uvicorn: ImportError cannot import name 'SessionLocal' from 'app.core.db'
- **Triệu chứng:** Alembic upgrade thành công nhưng Uvicorn crash lúc khởi động với lỗi: `ImportError: cannot import name 'SessionLocal' from 'app.core.db' (/opt/render/project/src/backend/app/core/db.py)`.
- **Nguyên nhân:** Các router WebSocket (`chat.py` và `direct_messages.py`) import `SessionLocal` để tự mở session DB bất đồng bộ trong vòng lặp socket (`async with SessionLocal() as db:`). Trong đợt refactor DB sang lazy-loading, `SessionLocal` chưa được khai báo lại trong `db.py`.
- **Cách sửa:** Khai báo `_SessionLocalProxy` trong `backend/app/core/db.py` và gán `SessionLocal = _SessionLocalProxy()` để tự động ủy quyền cuộc gọi tới `get_session_factory()` mà vẫn bảo toàn cơ chế lazy-load DB engine. Thêm kiểm thử hồi quy `test_main.py` để luôn nạp `app.main` và toàn bộ router khi chạy `pytest`.
- **Phòng tránh:** Luôn có ít nhất 1 bài test kiểm tra import toàn bộ `app.main` và OpenAPI paths trong bộ test tự động.

### 27/10/2026 – Aiven: SSLCertVerificationError certificate verify failed (self-signed certificate)
- **Triệu chứng:** `ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain` khi chạy `python -m alembic upgrade head` trên Render.
- **Nguyên nhân:** Aiven Cloud MySQL sử dụng CA certificate nội bộ (self-signed đối với hệ điều hành Linux tiêu chuẩn trên Render). Khi truyền `connect_args={"ssl": True}`, Python's `ssl.create_default_context()` mặc định yêu cầu CA được hệ điều hành tin cậy (`CERT_REQUIRED`), dẫn đến lỗi từ chối chuỗi chứng chỉ.
- **Cách sửa:** Khởi tạo `ssl.SSLContext` với `check_hostname = False` và `verify_mode = ssl.CERT_NONE`, truyền qua `connect_args={"ssl": ssl_ctx}` trong `db.py` và `migrations/env.py`. Điều này cho phép kết nối được mã hóa TLS đầy đủ mà không bị chặn bởi chứng chỉ self-signed của Aiven.
- **Phòng tránh:** Với các Cloud DB dùng CA riêng mà không gắn kèm file chứng chỉ CA cert (`ca.pem`), cấu hình SSL context linh hoạt theo hostname database.

### 27/10/2026 – Render: TypeError descriptor '__getitem__' requires a 'typing.Union' object but received a 'tuple'
- **Triệu chứng:** Render deploy fail khi chạy `python -m alembic upgrade head` với traceback chỉ tới `/opt/render/project/src/.venv/lib/python3.14/site-packages/sqlalchemy/util/typing.py`.
- **Nguyên nhân:** Render tự động dùng Python 3.14 (bản preview/pre-release). Python 3.14 có thay đổi nội bộ về `typing.Union`, làm xung đột với SQLAlchemy 2.0 khi phân giải kiểu `Mapped[float | None]`.
- **Cách sửa:** Khóa phiên bản Python ổn định `3.12.8` bằng file `.python-version` và biến môi trường `PYTHON_VERSION=3.12.8` trên Render Dashboard -> Environment.
- **Phòng tránh:** Luôn chỉ định rõ phiên bản Python (`.python-version`) trong các dự án production.

### 27/10/2026 – Render: No module named alembic
- **Triệu chứng:** Render deploy thất bại với log `/opt/render/project/src/.venv/bin/python: No module named alembic`.
- **Nguyên nhân:** Commit đang chạy trên Render chưa được commit/push các thư viện `alembic`, `SQLAlchemy`, `aiomysql` và thư mục `migrations/`.
- **Cách sửa:** Chạy `git add .`, commit và `git push origin main`.
- **Phòng tránh:** Luôn kiểm tra `git status` trước khi cập nhật Start Command trên Render.

### 27/10/2026 – Render: Couldn't find a package.json file in backend
- **Triệu chứng:** Render báo lỗi không tìm thấy `package.json` khi build backend.
- **Nguyên nhân:** Web Service trên Render bị chọn nhầm Runtime là `Node` thay vì `Python 3`.
- **Cách sửa:** Vào Settings đổi Runtime thành `Python 3`, Build Command `pip install -r requirements.txt`.

### 27/10/2026 – Aiven MySQL SSL Connection Refused
- **Triệu chứng:** SQLAlchemy async (`aiomysql`) không kết nối được tới Aiven MySQL do thiếu cấu hình TLS/SSL.
- **Nguyên nhân:** Aiven mặc định yêu cầu `SSL mode: REQUIRED`.
- **Cách sửa:** Thêm `connect_args={"ssl": True}` vào `create_async_engine` trong `db.py` và `async_engine_from_config` trong `env.py` khi URL chứa `aivencloud.com`.

### 27/10/2026 – Nhầm lẫn Custom Domain trên Render
- **Triệu chứng:** Render yêu cầu thêm bản ghi DNS CNAME `@` trỏ tới `onrender.com` khi người dùng nhập domain Vercel `*.vercel.app`.
- **Nguyên nhân:** Người dùng hiểu nhầm Custom Domain trên Render là nơi kết nối Frontend.
- **Cách sửa:** Xóa Custom Domain trên Render; kết nối bằng cách đặt `VITE_API_URL` trên Vercel và cấu hình `FRONTEND_ORIGIN` trên Render.

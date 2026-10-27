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

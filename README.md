# HUST Chatbox

Nền tảng chat ẩn danh dành cho sinh viên Đại học Bách khoa Hà Nội. Dự án dùng
FastAPI cho backend, React + Vite cho frontend, MySQL và Redis cho dữ liệu,
Mailpit để xem email trong môi trường phát triển.

## Chạy local

### 1. Cấu hình và khởi động dịch vụ

Sao chép `.env.example` thành `.env` ở thư mục gốc và thay các mật khẩu mẫu
bằng giá trị riêng cho máy local. Sau đó khởi động MySQL, Redis và Mailpit:

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps
```

Mailpit có giao diện tại <http://localhost:8025>. Các cổng dịch vụ chỉ bind vào
loopback của máy local.

### 2. Chạy backend

```powershell
cd backend
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

API health check: <http://localhost:8000/health>.

Trên macOS/Linux, tạo môi trường ảo bằng `python3 -m venv .venv` rồi kích hoạt
với `source .venv/bin/activate`.

Chạy test backend trong thư mục `backend/`:

```powershell
python -m pytest
```

### 3. Chạy frontend

Mở terminal khác:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Giao diện dev mặc định tại <http://localhost:5173>. Proxy `/api` dùng
`VITE_DEV_API_TARGET` trong `frontend/.env`.

Kiểm tra frontend:

```powershell
npm test
npm run build
```

## Tài liệu dự án

- [Kiến trúc](docs/ARCHITECTURE.md)
- [Tiến độ và nhật ký](docs/PROGRESS.md)
- [Quyết định kỹ thuật](docs/DECISIONS.md)
- [Khắc phục sự cố](docs/TROUBLESHOOTING.md)
- [Hướng dẫn deploy](docs/DEPLOY.md)
- [Hướng dẫn backend](backend/CLAUDE.md)
- [Hướng dẫn frontend](frontend/CLAUDE.md)
- [Hướng dẫn cơ sở dữ liệu](db/CLAUDE.md)

## Bảo mật

Không commit `.env`, mật khẩu, khóa bí mật hoặc dữ liệu dump. Chỉ dùng các file
`.env.example` làm mẫu; thay giá trị placeholder trước khi chạy dịch vụ local.

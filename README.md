# HUST Chatbox

Chat ẩn danh 1–1 cho sinh viên HUST. Stack: FastAPI, React/Vite, MySQL và
Redis; Mailpit dùng để nhận email khi phát triển local.

## Chạy local

Tạo ba file cấu hình từ mẫu tương ứng. Mẫu backend dùng Mailpit local; mã OTP
sẽ được gửi vào hộp thư tại <http://localhost:8025>. Không commit các file
`.env`.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
docker compose up -d
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Compose chỉ đọc root `.env`; đảm bảo `MYSQL_DATABASE`, `MYSQL_USER`,
`MYSQL_PASSWORD` và `MYSQL_PORT` khớp database/credential/port trong
`backend/.env` (`DATABASE_URL`). Lệnh tạo cấu hình phía trên không ghi đè các
file `.env` đã tồn tại.

Trong terminal khác:

```powershell
cd frontend
npm install
npm run dev
```

API: <http://localhost:8000/health> · Frontend: <http://localhost:5173> ·
Mailpit: <http://localhost:8025>. Nếu đổi mật khẩu MySQL trong root `.env`, cập
nhật cùng mật khẩu trong `backend/.env` ở `DATABASE_URL`. Nếu cổng MySQL 3306
bận, đổi `MYSQL_PORT` trong root `.env` và cập nhật port trong `DATABASE_URL`.

### Kiểm thử
```powershell
cd backend; python -m pytest
cd frontend; npm test
cd frontend; npm run build
```

macOS/Linux: tạo môi trường bằng `python3 -m venv .venv` và kích hoạt với
`source .venv/bin/activate`.

## Tài liệu
- Quy tắc bắt đầu: [CLAUDE.md](CLAUDE.md)
- [Trạng thái](docs/PROGRESS.md) · [Kiến trúc](docs/ARCHITECTURE.md) ·
  [Quyết định](docs/DECISIONS.md) · [Roadmap](docs/PLAN.md)
- [Luồng hệ thống](docs/SYSTEM_FLOWS.md) ·
  [Deploy](docs/DEPLOY.md) · [Sự cố](docs/TROUBLESHOOTING.md)
- [Backend](backend/CLAUDE.md) · [Frontend](frontend/CLAUDE.md) ·
  [Database](db/CLAUDE.md)

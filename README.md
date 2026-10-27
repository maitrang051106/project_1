# HUST Chatbox

Chat ẩn danh 1–1 cho sinh viên HUST. Stack: FastAPI, React/Vite, MySQL và
Redis; Mailpit dùng để nhận email khi phát triển local.

## Chạy local

Tạo `.env` từ mẫu ở thư mục gốc và trong `backend/`, `frontend/`; thay các giá
trị mẫu bằng thông tin local. Không commit các file `.env`.

```powershell
docker compose up -d
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Trong terminal khác:

```powershell
cd frontend
npm install
npm run dev
```

API: <http://localhost:8000/health> · Frontend: <http://localhost:5173> ·
Mailpit: <http://localhost:8025>. Nếu cổng MySQL 3306 bận, đổi `MYSQL_PORT`
trong `.env` và cập nhật `DATABASE_URL`.

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
- [Questionnaire/matching](docs/QUESTIONNAIRE.md) ·
  [Deploy](docs/DEPLOY.md) · [Sự cố](docs/TROUBLESHOOTING.md)
- [Backend](backend/CLAUDE.md) · [Frontend](frontend/CLAUDE.md) ·
  [Database](db/CLAUDE.md)

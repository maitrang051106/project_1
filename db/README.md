# Database & Seed Data (`db/`)

Thư mục này chứa tài liệu thiết kế schema (`db/schema.md`) và dữ liệu danh mục 68 ngành đào tạo chuẩn của Đại học Bách Khoa Hà Nội (`db/seed/`).

## Danh sách file
- `db/CLAUDE.md` — Quy tắc dành cho AI Agent khi làm việc với Database & Migrations.
- `db/schema.md` — Sơ đồ Mermaid ERD và mô tả chi tiết 5 bảng MySQL (`users`, `profiles`, `conversations`, `friendships`, `direct_messages`).
- `db/seed/hust-68-nganh-2026.csv` — Danh mục 68 ngành đào tạo HUST 2026 (`major_code`, `major_name`, `faculty_code`, `faculty_name`, `program_type`, `is_new_2026`), được nạp trực tiếp bởi `backend/app/services/catalog.py`.
- `db/seed/hust-schools-2026.csv` & `db/seed/generate_hust_catalog.py` — Dữ liệu Trường/Viện/Khoa và script hỗ trợ sinh file CSV.

## Quản lý Migration (Alembic)
Các bản migration nằm tại `backend/migrations/versions/`:
1. `0001_initial_schema.py` — Tạo 5 bảng cốt lõi của MVP.
2. `0002_backfill_email_hash.py` — Cập nhật `email_hash` theo `EMAIL_HASH_SECRET`.
3. `0003_friendship_requester.py` — Bổ sung cột `requested_by` vào bảng `friendships`.
4. `0004_expand_faculty_code.py` — Mở rộng cột `profiles.faculty_code` lên `VARCHAR(100)`.

### Lệnh chạy Migration
```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

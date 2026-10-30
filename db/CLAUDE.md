# Database – MySQL

Đọc [hướng dẫn gốc](../CLAUDE.md). Migration ở `backend/migrations/`;
questionnaire và matching có nguồn chuẩn tại
[SYSTEM_FLOWS.md](../docs/SYSTEM_FLOWS.md).

## Tài liệu

- [schema.md](schema.md): schema đã triển khai và schema mục tiêu.
- [README.md](README.md): migration và seed.

## Mô hình dữ liệu mục tiêu

- `users`: `email_hash`, tên ẩn danh, trust, trạng thái, vai trò.
- `profiles`: `gender` (male/female), `faculty_code` (VARCHAR(100) slug tiếng Anh), `major_code`, `cohort` (K63–K71).

- `faculties`/`majors`: catalog School và ngành; mỗi ngành thuộc một đơn vị.
- `conversations` và bảng report/trust/block/appeal: xem schema.

Schema mục tiêu và thứ tự migration: [schema.md](schema.md) và
[PLAN.md](../docs/PLAN.md). CSV chương trình trong `db/seed/` là nguồn chuẩn;
tạo lại CSV đơn vị và kiểm tra catalog bằng
`python db/seed/generate_hust_catalog.py`. `major_code` giữ mã nguồn;
`faculty_code` là slug nội bộ. Không crawl website khi seed.
Chỉ tạo migration theo đúng task trong plan; schema mục tiêu chưa phải migration
được phê duyệt.

## Quy tắc dữ liệu
- Chỉ lưu email dạng HMAC; không lưu transcript lâu dài.
- Buffer Redis tối đa 1 MiB, bỏ tin cũ trước, hết hạn 30 phút sau chat.
- Report hợp lệ mới được snapshot evidence mã hóa; xóa DB evidence sau 30 phút.
- Dùng Alembic, không sửa schema trực tiếp trên Aiven; đọc migration trước khi
  chạy và sao lưu trước thay đổi rủi ro.
- Dùng truy vấn ORM/tham số hóa; chỉ lưu credential và CA trong cấu hình môi
  trường, bật SSL khi kết nối Aiven.

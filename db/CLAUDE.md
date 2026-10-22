# db/ – Cơ sở dữ liệu (MySQL)

Đọc `../CLAUDE.md` trước. Thư mục này chứa **tài liệu và công cụ hỗ trợ** cho CSDL. Migration (Alembic) nằm ở `backend/migrations/`; `db/` là nơi tham chiếu schema, dữ liệu mẫu và hướng dẫn vận hành.

## Nội dung
```
db/
  CLAUDE.md
  README.md          # cách kết nối local và Aiven (SSL), cách sao lưu/khôi phục
  schema.md          # mô tả bảng/cột (cập nhật sau mỗi migration)
  seed/seed_users.py # sinh người dùng giả để thử ghép cặp (T-32)
  backup/            # script mysqldump (không commit file dump)
```

## Schema Sprint 1
- `users`: `id` PK; `email_hash` CHAR(64) UNIQUE, INDEX; `anon_name` VARCHAR(50); `trust_score` INT mặc định 100; `status` ENUM(`active`,`shadowban`,`banned`); `role` ENUM(`user`,`admin`); `created_at`; `last_login_at`.
- `profiles`: `user_id` PK/FK → users; `goal` VARCHAR; `interests` JSON; `faculty` VARCHAR (tùy chọn); `vector` JSON; `updated_at`.
- `conversations`: `id` PK; `user_a`, `user_b` FK → users; `type` ENUM(`human`,`bot`); `score` FLOAT (điểm cosine); `started_at`; `ended_at`.

## Dự kiến các sprint sau
- Sprint 2: `trust_events` (user_id, conversation_id, delta, reason, created_at), `reports` (reporter_id, target_id, conversation_id, reason, status, reviewed_by), `blocks` (user_id, blocked_id).
- Sprint 4: `identity_requests` (conversation_id, requester_id, status, expires_at); thêm cột `email_encrypted` (AES) vào dữ liệu định danh khi triển khai Identity Reveal.

## Quy tắc
1. **Không lưu email thô**: dùng `email_hash = HMAC-SHA256(OTP_SECRET, email_chuẩn_hóa)`. Chuẩn hóa: chữ thường, bỏ khoảng trắng.
2. **Không lưu nội dung tin nhắn.**
3. Mọi thay đổi cấu trúc bảng đi qua migration Alembic; không sửa tay trên Aiven. Đọc file migration tự sinh trước khi chạy.
4. Chỉ đánh index cho cột thường tìm kiếm (`email_hash`, khóa ngoại).
5. Cập nhật `schema.md` cùng PR với migration.
6. Truy vấn dùng ORM/tham số hóa; không nối chuỗi SQL.

## Aiven (MySQL free)
- Lấy host, port, user, password, CA certificate từ trang dịch vụ; lưu vào biến môi trường, không commit.
- Kết nối cần SSL; thử bằng `mysql` client trước khi cấu hình backend.
- Gói free có giới hạn tài nguyên và có thể bị tắt nếu lâu không dùng; đặt lịch sao lưu `mysqldump`. Kiểm tra giới hạn hiện tại trên trang Aiven.

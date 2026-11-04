# Database — MySQL 8.0 & Alembic (`db/` & `backend/migrations/`)

## Cấu trúc thư mục
- `db/schema.md` — Tài liệu mô tả chi tiết 5 bảng MVP và sơ đồ Mermaid ERD (Single Source of Truth cho Database Schema).
- `db/seed/hust-68-nganh-2026.csv` — Dữ liệu gốc 68 ngành đào tạo và Trường/Viện/Khoa của HUST năm 2026.
- `db/seed/hust-schools-2026.csv` & `db/seed/generate_hust_catalog.py` — Dữ liệu trường/viện và script tái tạo catalog CSV.
- `backend/app/models/` — SQLAlchemy 2.0 ORM models (`user.py`, `profile.py`, `conversation.py`, `friendship.py`, `direct_message.py`, `enums.py`).
- `backend/migrations/versions/` — Chuỗi 4 bản Alembic migrations:
  - `0001_initial_schema.py`: Khởi tạo 5 bảng `users`, `profiles`, `conversations`, `friendships`, `direct_messages`.
  - `0002_backfill_email_hash.py`: Đồng bộ `users.email_hash` bằng `EMAIL_HASH_SECRET`.
  - `0003_friendship_requester.py`: Thêm cột `requested_by` (`FK -> users.id`) vào bảng `friendships`.
  - `0004_expand_faculty_code.py`: Mở rộng `profiles.faculty_code` từ `VARCHAR(20)` lên `VARCHAR(100)`.

## Quy tắc cốt lõi (Database Guardrails)

1. **5 Bảng Vật lý trong MySQL (Không có bảng `faculties`/`majors` trong DB)**:
   - Cơ sở dữ liệu MVP chỉ gồm đúng 5 bảng: `users`, `profiles`, `conversations`, `friendships`, `direct_messages`.
   - Danh mục 68 ngành và Trường/Viện được nạp vào bộ nhớ từ file `db/seed/hust-68-nganh-2026.csv` thông qua `backend/app/services/catalog.py`. `profiles.major_code` (`VARCHAR(20)`) và `profiles.faculty_code` (`VARCHAR(100)`) lưu mã chuỗi trực tiếp, không gắn khóa ngoại SQL.
2. **Lưu trữ Email & Mật khẩu trong `users`**:
   - Bảng `users` lưu cả `email` (`VARCHAR(191) UNIQUE`, dùng để đăng nhập và hiển thị cho bạn bè đã kết bạn `accepted`), `email_hash` (`CHAR(64) UNIQUE`, HMAC-SHA256 dùng cho rate-limit/OTP), và `password_hash` (`VARCHAR(255)` PBKDF2-SHA256).
3. **Chuẩn hóa Cặp User & Quyền Phản hồi trong `friendships`**:
   - Mọi bản ghi trong `friendships` bắt buộc lưu theo thứ tự `user_a = min(uid1, uid2)` và `user_b = max(uid1, uid2)` kèm ràng buộc `UNIQUE(user_a, user_b)`.
   - Cột `requested_by` ghi nhận ID người gửi lời mời. Chỉ người nhận (`responder_id != requested_by`) mới có quyền chấp nhận hoặc từ chối lời mời đang ở trạng thái `pending` (kiểm tra qua `Friendship.can_be_responded_to_by()`).
4. **Ràng buộc Lưu trữ Tin nhắn**:
   - Bảng `conversations` chỉ lưu metadata phiên ghép đôi ẩn danh (`user_a`, `user_b`, `type`, `started_at`, `ended_at`). Nội dung tin nhắn ẩn danh chỉ lưu tạm trên Redis 24h (`hust:v1:chat:history:{room_id}`), không lưu vào MySQL.
   - Bảng `direct_messages` chỉ lưu tin nhắn giữa hai người dùng đã có quan hệ bạn bè `status = 'accepted'`.
5. **Quy định Migration**:
   - Mọi thay đổi trên `backend/app/models/` phải đi kèm file migration mới trong `backend/migrations/versions/` có đủ cả hàm `upgrade()` và `downgrade()`.

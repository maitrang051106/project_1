# Kế hoạch Phát triển Tiếp theo (Roadmap & Backlog — Sprint 2 & 3)

> [!NOTE]
> Toàn bộ hạng mục thuộc **Sprint 1 (MVP Core, Production Hardening, Realtime Chat Reconnect 24h & Direct Messages)** đã hoàn thành. Xem chi tiết trạng thái đã hoàn thành tại `docs/PROGRESS.md`.
> Tài liệu này chỉ lưu trữ **Backlog cho các giai đoạn mở rộng tiếp theo** (chưa triển khai trong code hiện tại).

---

## Sprint 2: An toàn Cộng đồng & Kiểm duyệt (Safety & Moderation)

### 1. Chặn Người dùng (`blocks`)
- **Mục tiêu**: Cho phép người dùng chặn đối phương trong phòng chat ẩn danh hoặc trong danh sách bạn bè để hai bên không bao giờ bị ghép đôi lại với nhau và không thể gửi Direct Messages.
- **Thiết kế dự kiến**:
  - Thêm bảng `blocks` (`id`, `blocker_id`, `blocked_id`, `created_at`, `UNIQUE(blocker_id, blocked_id)`) kèm Alembic migration `0005`.
  - Bổ sung kiểm tra danh sách chặn hai chiều trong `POST /match/join` và `/ws/direct/{friend_id}`.

### 2. Báo cáo Vi phạm (`reports`) & Tự động Trừ điểm `trust_score`
- **Mục tiêu**: Cho phép tố cáo hành vi quấy rối/spam trong phòng chat ẩn danh và tự động điều chỉnh `users.trust_score` (cơ chế hạn mức ghép đôi theo `trust_score` đã có sẵn trong `backend/app/services/matching.py`).
- **Thiết kế dự kiến**:
  - Thêm bảng `reports` (`id`, `reporter_id`, `reported_id`, `conversation_id`, `reason`, `evidence_snapshot`, `status`, `created_at`).
  - Trích xuất tối đa 10 tin nhắn gần nhất từ Redis `hust:v1:chat:history:{room_id}` tại thời điểm bấm tố cáo để lưu vào `evidence_snapshot` phục vụ kiểm duyệt.
  - Áp dụng quy tắc trừ điểm `trust_score` và khóa tài khoản (`UserStatus.BANNED`) khi `trust_score <= 0`.

### 3. Chuyển đổi Gửi Email sang HTTP API cho Cloud Free Tier
- **Mục tiêu**: Khắc phục việc Render Free Tier chặn cổng SMTP (`25`, `465`, `587`).
- **Thiết kế dự kiến**:
  - Mở rộng `backend/app/services/email_service.py` hỗ trợ gửi OTP qua HTTPS API (cổng `443`) của Resend hoặc Brevo khi cấu hình biến `RESEND_API_KEY` / `BREVO_API_KEY`, giữ `aiosmtplib` làm mặc định cho Mailpit local.

---

## Sprint 3: Trải nghiệm Nâng cao & Quản trị (AI Fallback & Admin)

1. **AI Bot Fallback khi chờ quá 60s (`ConversationType.BOT`)**:
   - Khi hết 60s tìm kiếm mà trả về `not_found`, hiển thị nút tùy chọn *"Trò chuyện với Trợ lý Ảo Bách Khoa"* sử dụng Gemini API.
2. **Trang Quản trị (`AdminRole`)**:
   - Giao diện dành riêng cho tài khoản có `role = 'admin'` để duyệt danh sách `reports`, khôi phục `trust_score` hoặc gỡ khóa tài khoản.
3. **Thông báo Tin nhắn chưa đọc (`is_read`)**:
   - Bổ sung sự kiện đánh dấu đã đọc (`mark_read`) trên `/ws/direct/{friend_id}` và hiển thị huy hiệu số tin nhắn mới trên thanh điều hướng `Messages`.

# Nhật ký Quyết định Kiến trúc (Architecture Decision Records — ADRs)

Tài liệu này lưu trữ các quyết định kỹ thuật và sản phẩm của dự án **HUST Match**. Phần 1 liệt kê **các ADR đang có hiệu lực thi hành** (từ mới nhất đến nền tảng); Phần 2 lưu trữ tóm tắt các ADR ban đầu đã được thay thế (`[Superseded]`) để AI Agent không bị nhiễu bởi quy tắc cũ.

---

## Phần 1: Các Quyết định Kiến trúc Đang Có Hiệu Lực (Active ADRs)

### ADR-021: Lưu lịch sử Chat ẩn danh 24h trên Redis, Đồng nhất DM WebSocket & Chuyển tiếp Kết bạn (2026-11-03)
- **Trạng thái**: Đang áp dụng (Active)
- **Bối cảnh**: Khi người dùng F5 hoặc rớt mạng tạm thời trong phòng chat ẩn danh, toàn bộ tin nhắn biến mất và kết nối Pub/Sub của phòng bị hủy. Đồng thời, phần Direct Messages tồn tại song song cả REST `POST /messages/{friend_id}` lẫn WebSocket, truy vấn `GET /friends` bị N+1 query, và phòng ẩn danh chưa tự chuyển sang `/messages` khi kết bạn thành công.
- **Quyết định**:
  1. **Giữ sống Pub/Sub khi F5 & Lưu lịch sử ẩn danh 24h trên Redis**: `unsubscribe_room()` chỉ gỡ queue của socket vừa đóng mà không hủy task Redis Pub/Sub của phòng; chỉ hủy trong `cancel_room_pubsub()` khi phòng thực sự đóng (`ended_at`). Tin nhắn phòng ẩn danh được lưu vào Redis List `hust:v1:chat:history:{room_id}` (TTL 24h = `86400s`) và tải qua API gộp `GET /conversations/{room_id}/init` kèm phân trang cursor `before_timestamp`.
  2. **Bảo mật phòng ẩn danh & Tự động chuyển sang `/messages` khi kết bạn**: Trong phòng ẩn danh, `opponent.email` luôn là `None` và không trả cờ `is_friend`. Khi 2 bên đồng ý kết bạn (hoặc vốn đã là bạn bè mà bấm kết bạn), hệ thống tự động kết thúc phòng ẩn danh (`ended_at = NOW()`), phát sự kiện `friend_accepted` và đếm ngược 2s đưa cả hai sang `/messages`. Tin nhắn trong phòng ẩn danh **không chép** sang bảng `direct_messages`.
  3. **Tách biệt kênh Pub/Sub & Bỏ `POST /messages/{friend_id}`**: Kênh Pub/Sub tách thành `hust:v1:channel:match:{room_id}` và `hust:v1:channel:dm:{low}_{high}`. Xóa endpoint `POST /messages/{friend_id}`, thống nhất gửi tin nhắn bạn bè 100% qua `/ws/direct/{friend_id}`.
  4. **Khử N+1 Query & Vá rò rỉ WS Slot**: Dùng SQL Window Function `ROW_NUMBER() OVER (PARTITION BY partner_id ORDER BY created_at DESC)` trong `GET /friends`. Bắt buộc kiểm tra điều kiện DB (`ended_at is None` / `Friendship.status == 'accepted'`) **trước khi** gọi `acquire_ws_slot` ở cả 2 cổng WebSocket.

### ADR-020: Chính sách Fail-Fast HTTP 503 khi mất Redis trên Production (2026-10-28)
- **Trạng thái**: Đang áp dụng (Active)
- **Quyết định**:
  1. Khi `ENVIRONMENT=production`, nếu Redis không kết nối được lúc khởi động hoặc gặp lỗi trong quá trình chạy, `StoreService` ném `RedisUnavailable` và trả về **HTTP `503 Service Unavailable`** (không fallback sang bộ nhớ RAM của từng tiến trình để tránh lỗi split-brain cho OTP, rate-limit, session và hàng đợi).
  2. Chỉ cho phép fallback sang in-memory store ở môi trường `development` và `test`.

### ADR-019: Hợp đồng Hàng đợi Ghép đôi 60s & Cột `requested_by` cho Kết bạn (2026-10-28)
- **Trạng thái**: Đang áp dụng (Active)
- **Quyết định**:
  1. **Ghép đôi nguyên tử & Timeout 60s**: Sử dụng Redis Lua Script (`RESERVE_CANDIDATE_LUA`) để giữ chỗ ứng viên nguyên tử, kiểm tra lại hạn mức `trust_score`/ngày trong giao dịch MySQL `SELECT ... FOR UPDATE`, và tự động chuyển sang trạng thái `not_found` (`hust:v1:match:terminal:{user_id}`) khi chờ đủ 60s.
  2. **Chống tự chấp nhận lời mời kết bạn**: Bổ sung cột `requested_by` vào bảng `friendships` (migration `0003`). Chỉ người nhận (`responder_id != requested_by`) mới có quyền phản hồi lời mời đang `pending`. Nếu người nhận cũng bấm nút `Add Friend` khi đã có lời mời `pending` từ đối phương, hệ thống coi là đồng thuận 2 chiều và chuyển thẳng sang `accepted`.

### ADR-018: Hardening Bảo mật Xác thực, Tách biệt OTP Domain & Giới hạn Slot WebSocket (2026-10-28)
- **Trạng thái**: Đang áp dụng (Active)
- **Quyết định**:
  1. **Quản lý cấu hình (`config.py`)**: Đọc biến môi trường từ `.env` và `backend/.env`; khi `ENVIRONMENT=production`, bắt buộc khai báo đủ biến, các secret (`OTP_SECRET`, `EMAIL_HASH_SECRET`, `JWT_SECRET`) phải dài tối thiểu 32 bytes, và bắt buộc `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none`.
  2. **Phân tách tầng (`app/schemas/`, `app/services/`)**: Tách toàn bộ Pydantic schemas vào `app/schemas/`, tách logic xác thực vào `app/services/auth_service.py` và gửi mail vào `app/services/email_service.py`.
  3. **Bảo mật OTP & Session (`jti`)**: Khóa HMAC của OTP được phân tách theo mục đích (`purpose="register"` vs `purpose="reset"`). Mỗi JWT phát hành đều chứa `jti` lưu trong Redis để thu hồi ngay khi đăng xuất hoặc đổi mật khẩu.
  4. **Giới hạn kết nối WebSocket**: Tối đa `3` kết nối đồng thời trên mỗi `user_id` và `10` kết nối đồng thời trên mỗi `client_ip` thông qua Lua Script trong `acquire_ws_slot` / `release_ws_slot`.

### ADR-017: Xác thực OTP + Mật khẩu, Chỉ nhận `@sis.hust.edu.vn`, Avatar Thú & Kết bạn 2 Chiều (2026-10-27)
- **Trạng thái**: Đang áp dụng (Active)
- **Quyết định**:
  1. **Email & Mật khẩu**: Chỉ chấp nhận đuôi `@sis.hust.edu.vn` (từ chối `@hust.edu.vn`). Chỉ yêu cầu mã OTP ở bước Đăng ký lần đầu và Quên mật khẩu; đăng nhập hàng ngày dùng Email + Mật khẩu (`PBKDF2-HMAC-SHA256`).
  2. **Lưu trữ Email có kiểm soát**: Lưu cả `email` (để đăng nhập và hiển thị cho bạn bè sau khi `accepted`) và `email_hash` (để rate-limit/OTP).
  3. **Cá nhân hóa**: Thay `anon_name` bằng `nickname` và bộ 11 emoji linh vật thú (`DEFAULT_AVATAR = "🦉"`).
  4. **Mạng xã hội thu nhỏ**: Thêm bảng `friendships` và `direct_messages` để hai người dùng sau khi kết bạn 2 chiều có thể nhắn tin lâu dài tại `/messages` và xem được email thật của nhau.

### ADR-016: Đơn giản hóa Ghép đôi sang 3 Bộ lọc Cứng 2 Chiều & Cascading Dropdown 68 Ngành (2026-10-27 & 2026-10-30)
- **Trạng thái**: Đang áp dụng (Active)
- **Quyết định**:
  1. Loại bỏ bộ câu hỏi tính cách Q1–Q6 và điểm tương đồng cosine; chuyển sang **3 tiêu chí lọc cứng 2 chiều (Mutual Hard Filters)**: Giới tính (`male`/`female`/`any`), Trường-Viện-Ngành (`same_major`/`same_faculty`/`different_faculty`/`any`), và Khóa học `K63`–`K71` (`same_cohort`/`senior`/`junior`/`any`).
  2. Sử dụng danh mục 68 ngành đào tạo chuẩn HUST 2026 từ `db/seed/hust-68-nganh-2026.csv` (`encoding="utf-8-sig"`). Giao diện Onboarding dùng Cascading Dropdown chọn **Trường/Viện/Khoa (`faculty_code` `VARCHAR(100)`) → Ngành học (`major_code`)**.

### Các ADR Nền tảng Ban đầu Vẫn Giữ Hiệu Lực
- **ADR-001**: Kiến trúc Monorepo 1-1-1 (`frontend/`, `backend/`, `db/`, `docs/`) dùng chung cho cả môi trường Docker Compose local và Cloud.
- **ADR-004**: Xác thực bằng JWT lưu trong `HttpOnly` cookie (tránh XSS đọc token).
- **ADR-010**: Tầng `StoreService` (`store.py`) đóng gói mọi giao tiếp Redis và hỗ trợ fallback in-memory khi phát triển local/chạy unit test.
- **ADR-011**: Bộ khung giao diện 5 màn hình chính (`Login`, `Onboarding`, `Matching`, `Chat`, `Messages`).
- **ADR-013**: Hệ thống điểm uy tín `trust_score` (mặc định `100`) giới hạn số lượt ghép đôi mỗi ngày theo múi giờ Việt Nam (`UTC+7`).

---

## Phần 2: Phụ lục các ADR Lịch sử Đã Được Thay Thế (`[Superseded]`)

> [!WARNING]
> Các ADR dưới đây thuộc thiết kế sơ khởi và **KHÔNG CÒN ÁP DỤNG** trong mã nguồn hiện tại:

| Mã ADR | Nội dung cũ ban đầu | Đã bị thay thế bởi |
| :--- | :--- | :--- |
| **ADR-002** | Ghép đôi bằng vector trọng số 6 câu hỏi tính cách (Q1–Q6) và ngưỡng điểm `0.70` / `0.55`. | **ADR-016** (3 bộ lọc cứng 2 chiều). |
| **ADR-003** | Tự động đẩy vào phòng chat với AI Bot Gemini sau 60s không tìm thấy người. | **ADR-019** (Trả `not_found` sau 60s; AI Bot dời sang Backlog Sprint 3). |
| **ADR-005** | Ma trận phạt điểm `trust_score` tự động theo số lượng `reports`. | Dời sang Backlog Sprint 2 (`docs/PLAN.md`). |
| **ADR-006** | Chuẩn hóa mã lỗi API theo envelope `{error: {code, message}}`. | Dùng chuẩn `HTTPException(detail=...)` mặc định của FastAPI. |
| **ADR-007** | Schema 7 bảng (có bảng `faculties`, `majors`, `reports`, `blocks` và không lưu cột `email`). | **ADR-016 & ADR-017** (5 bảng MVP + đọc ngành từ CSV). |
| **ADR-008, 009, 012, 015** | Chỉ giữ bộ đệm 10 tin nhắn gần nhất để phục vụ tính năng tố cáo (`report`). | **ADR-021** (Lưu lịch sử phòng ẩn danh 24h trên Redis để F5/reconnect + lưu DM vào MySQL). |
| **ADR-014** | Giữ khung route rỗng cho `report`, `block`, `admin` trong Sprint 1. | Đã dọn sạch, chỉ giữ các route thực sự hoạt động trong MVP. |

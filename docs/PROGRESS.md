# Tiến độ Thực hiện & Trạng thái Kiểm thử (Project Progress)

Cập nhật lần cuối: **04/11/2026**

## 1. Tổng quan Trạng thái Dự án

Toàn bộ phạm vi **MVP Core (Sprint 1 + Production Hardening + Realtime Chat/DM Refactor)** đã hoàn thành 100%, được kiểm chứng qua bộ Unit Test tự động của cả Backend (`pytest`) và Frontend (`vitest` + `vite build`).

| Phân hệ | Trạng thái | Các hạng mục đã hoàn thành |
| :--- | :---: | :--- |
| **1. Xác thực & Bảo mật (`auth`)** | ✅ Hoàn tất | • Chỉ nhận `@sis.hust.edu.vn`; đăng ký & quên mật khẩu qua OTP 6 số (HMAC tách domain `register`/`reset`, chống dò tài khoản anti-enumeration).<br>• Đăng nhập bằng mật khẩu (`PBKDF2-HMAC-SHA256`), cấp JWT `HttpOnly` cookie kèm Redis Session Allowlist (`jti`), thu hồi toàn bộ phiên khi đổi mật khẩu.<br>• Rate-limit đa tầng theo IP (`20/60s`), Email (`5/300s`) và Login (`10/900s`). |
| **2. Hồ sơ & Danh mục 68 Ngành (`profile`)** | ✅ Hoàn tất | • Đọc danh mục 68 ngành HUST 2026 từ `db/seed/hust-68-nganh-2026.csv` (`encoding="utf-8-sig"`, chống lỗi UTF-8 BOM) kèm fallback tĩnh `hustCatalog.js`.<br>• Giao diện Cascading Dropdown chọn **Trường/Viện/Khoa → Ngành đào tạo**, chọn 11 Avatar thú, Nickname, Giới tính và Khóa `K63`–`K71`.<br>• Mở rộng `profiles.faculty_code` lên `VARCHAR(100)` (migration `0004`). |
| **3. Ghép đôi 2 Chiều Nguyên tử (`matching`)** | ✅ Hoàn tất | • Kiểm tra thỏa mãn đồng thời 3 tiêu chí cứng của cả 2 phía (`is_mutual_match`).<br>• Giữ chỗ ứng viên nguyên tử bằng Redis Lua Script (`RESERVE_CANDIDATE_LUA`) kết hợp `SELECT ... FOR UPDATE` kiểm tra hạn mức `trust_score`/ngày.<br>• Timeout 60s trả trạng thái `not_found`; hỗ trợ `GET /match/active-room` tự động đưa người dùng về phòng đang mở. |
| **4. Chat Ẩn danh & Reconnect 24h (`chat`)** | ✅ Hoàn tất | • Kênh Pub/Sub riêng `hust:v1:channel:match:{room_id}`; giữ sống task Pub/Sub khi người dùng F5/rớt mạng tạm thời.<br>• Lưu lịch sử chat ẩn danh 24h trên Redis (`hust:v1:chat:history:{room_id}`), tải qua API gộp `GET /conversations/{room_id}/init` và phân trang cursor `before_timestamp`.<br>• Bảo vệ tuyệt đối quyền riêng tư: `opponent.email = None` trong suốt phiên ẩn danh; không chép tin nhắn ẩn danh sang `direct_messages`. |
| **5. Kết bạn 2 Chiều & Direct Messages (`direct_messages`)** | ✅ Hoàn tất | • Lưu người khởi tạo lời mời (`requested_by`, migration `0003`) chống tự chấp nhận; tự động đóng phòng ẩn danh và đếm ngược 2s chuyển sang `/messages` khi kết bạn thành công.<br>• Truy vấn danh sách bạn bè `GET /friends` kèm tin nhắn cuối bằng SQL Window Function `ROW_NUMBER()` (khử N+1 query).<br>• Gửi/nhận tin nhắn bạn bè 100% qua `/ws/direct/{friend_id}` (kênh `hust:v1:channel:dm:{low}_{high}`) và phân trang cursor `before_id`. |
| **6. Hạ tầng, WebSocket Slot & Fail-Fast 503** | ✅ Hoàn tất | • Giới hạn kết nối WebSocket (`3/user`, `10/IP`) và đảm bảo kiểm tra điều kiện DB trước khi gọi `acquire_ws_slot` ở cả `/ws/{room_id}` lẫn `/ws/direct/{friend_id}`.<br>• Đảm bảo Fail-Fast HTTP `503 RedisUnavailable` trên `production` cho toàn bộ thao tác trong `store.py`.<br>• Chuẩn hóa `pytest.ini` ở thư mục gốc, `buildWsUrl()` qua Vite proxy `/ws`, và sửa ánh xạ cổng MySQL trong `docker-compose.yml`. |

---

## 2. Lệnh Kiểm tra Nhanh (Verification Commands)

Chạy trực tiếp từ thư mục gốc `d:\laptrinh\fullstack\project_1`:

```powershell
# 1. Chạy toàn bộ bộ kiểm thử Backend (pytest)
.\backend\.venv\Scripts\python.exe -m pytest -v

# 2. Chạy bộ kiểm thử Frontend (Node test runner)
npm.cmd --prefix frontend test

# 3. Kiểm tra đóng gói Production Frontend (Vite build)
npm.cmd --prefix frontend run build
```

Để xem các tính năng dự kiến cho giai đoạn tiếp theo (Sprint 2 & Sprint 3), vui lòng xem `docs/PLAN.md`.

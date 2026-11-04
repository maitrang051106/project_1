# Frontend — React 19 + Vite 6 (`frontend/`)

## Cấu trúc thư mục
- `src/pages/Login.jsx` — 3 chế độ: Đăng nhập (`Sign In`), Đăng ký OTP (`Sign Up`), Quên mật khẩu (`Reset`), kiểm tra đuôi `@sis.hust.edu.vn`.
- `src/pages/Onboarding.jsx` — Thiết lập Nickname, chọn 11 Avatar thú, Giới tính, Cascading Dropdown (Trường/Viện → Ngành học), Khóa `K63`–`K71`.
- `src/pages/Matching.jsx` — Chọn 3 tiêu chí tìm bạn, tự kiểm tra `/match/active-room` khi vào trang, polling `/match/status` mỗi 2s trong 60s.
- `src/pages/Chat.jsx` — Phòng chat ẩn danh realtime (`/ws/{roomId}`), khởi tạo 1 bước qua `/conversations/{roomId}/init`, cuộn tải tin nhắn cũ (`before_timestamp`), gửi/nhận lời mời kết bạn và tự động đếm ngược 2s chuyển sang `/messages` khi kết bạn thành công.
- `src/pages/Messages.jsx` — Danh sách bạn bè phân trang (`GET /friends`) và khung chat bạn bè realtime qua `/ws/direct/{friendId}` kèm phân trang cursor (`before_id`).
- `src/components/ProtectedRoute.jsx` — Bảo vệ các route yêu cầu đăng nhập.
- `src/store/` — Zustand stores (`auth.js`, `chat.js`) và unit tests (`*.test.js`).
- `src/lib/` — Tiện ích dùng chung:
  - `api.js`: Hàm `apiFetch(path, options)` (luôn kèm `credentials: "include"`) và `buildWsUrl(path)`.
  - `constants.js`: Hằng số UI, danh sách Avatar, Khóa K63–K71, tùy chọn bộ lọc ghép đôi.
  - `hustCatalog.js`: Dữ liệu fallback tĩnh cho 68 ngành đào tạo HUST.

## Anti-Regression Guardrails (Quy tắc chống lặp lại lỗi — BẮT BUỘC)

1. **Kết nối WebSocket qua `buildWsUrl()` và Vite Proxy**:
   - Mọi kết nối WebSocket (`Chat.jsx`, `Messages.jsx`) **bắt buộc** dùng hàm `buildWsUrl(path)` từ `src/lib/api.js`.
   - Ở môi trường local dev, không gán cứng `VITE_WS_URL=ws://127.0.0.1:8000` trong `frontend/.env`; để trống biến này để `buildWsUrl()` đi qua `window.location.host` (`localhost:5173/ws/...`) nhờ proxy `/ws` trong `vite.config.js`, đảm bảo trình duyệt luôn đính kèm cookie `access_token` (`HttpOnly`).
2. **Khởi tạo Phòng Chat & Khử trùng lặp Tin nhắn (Deduplication)**:
   - Trong `Chat.jsx`, chỉ dùng một `useEffect` gọi `GET /conversations/{roomId}/init?limit=20` để lấy đồng thời `meta` và `history`, chỉ mở kết nối WebSocket sau khi `metaLoaded === true` và `!isEnded`.
   - Khi nhận tin nhắn từ WebSocket hoặc khi nối thêm lịch sử cũ (infinite scroll up), luôn lọc trùng bằng `msgKey(m)` (với chat ẩn danh) hoặc `m.id` (với Direct Messages).
3. **An toàn khi Parse JSON & Fallback Danh mục**:
   - Khi xử lý phản hồi lỗi từ API, luôn dùng `await res.json().catch(() => null)` hoặc bọc `try/catch` để tránh crash `SyntaxError: Unexpected token` nếu server trả lỗi 500 dạng text thuần.
   - Giữ nguyên fallback `HUST_CATALOG` từ `src/lib/hustCatalog.js` trong `Onboarding.jsx` để dropdown Trường/Ngành luôn hoạt động ngay cả khi API catalog chậm hoặc lỗi.
4. **Kiểm thử 2 Tài khoản trên máy Local**:
   - Vì cookie `access_token` có `Path=/` và chia sẻ trên cùng trình duyệt, khi test ghép đôi hoặc chat giữa 2 tài khoản trên cùng máy, bắt buộc mở **1 cửa sổ thường + 1 cửa sổ Ẩn danh (Incognito)** (hoặc 2 trình duyệt khác nhau) cùng truy cập `http://localhost:5173`.

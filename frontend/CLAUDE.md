# frontend/ – React + Vite

Đọc `../CLAUDE.md` trước. File này mô tả riêng phần giao diện.

## Nhiệm vụ
Đăng nhập 2 bước (email → OTP), Onboarding chọn mục tiêu/sở thích, màn hình tìm người, khung chat realtime.

## Cấu trúc
```
frontend/
  src/
    main.jsx, App.jsx
    pages/        Login.jsx, Onboarding.jsx, Matching.jsx, Chat.jsx
    components/   Bubble.jsx, MessageInput.jsx, ProtectedRoute.jsx, ...
    store/        auth.js, chat.js        (Zustand)
    lib/          api.js, socket.js       (fetch kèm cookie, WebSocket tự kết nối lại)
  index.html
  vercel.json     (rewrite mọi đường dẫn về /index.html)
  .env.example    (VITE_API_URL, VITE_WS_URL)
  vite.config.js  (proxy /api -> http://localhost:8000 khi dev)
```

## Quy tắc
- Gọi API qua `lib/api.js` với `credentials: "include"`; **không** lưu token ở `localStorage`.
- Địa chỉ backend lấy từ `import.meta.env.VITE_API_URL` / `VITE_WS_URL`; **không** hard-code `localhost` trong code. Biến `VITE_*` gắn lúc build, đổi xong phải build/deploy lại.
- Zustand chỉ giữ trạng thái dùng chung (người dùng, tin nhắn phòng hiện tại); trạng thái cục bộ dùng `useState`.
- Hiển thị tin nhắn bằng text (JSX tự escape); **cấm** `dangerouslySetInnerHTML`.
- `ProtectedRoute`: gọi `GET /me`, 401 thì chuyển về `/login`.
- WebSocket: tự kết nối lại với độ trễ tăng dần; dùng `wss://` khi trang chạy HTTPS; hiển thị trạng thái "đối phương đã rời".
- Giao diện responsive: kiểm tra ở 375px và 1280px; ưu tiên mobile.
- Nội dung giao diện bằng tiếng Việt; thông báo lỗi rõ ràng, thân thiện.

## Màn hình và luồng
`/login` (email → OTP, đếm ngược 60 giây trước khi gửi lại) → `/onboarding` (lần đầu) → `/matching` ("Đang tìm người phù hợp…", hết 60 giây hiện thông báo) → `/chat/:roomId`.

## Deploy (Vercel)
Root Directory `frontend`; Build `npm run build`; Output `dist`; đặt `VITE_API_URL`, `VITE_WS_URL`. Nếu khác tên miền với backend: xử lý CORS/cookie (xem `../docs/DEPLOY.md`).

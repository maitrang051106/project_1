# Frontend – React + Vite

Đọc [hướng dẫn gốc](../CLAUDE.md). Luồng giao diện: đăng nhập OTP →
onboarding → matching → chat. Dùng React Router và Zustand.

## Quy tắc
- Gọi API qua `lib/api.js` với `credentials: "include"`; không lưu token trong
  `localStorage`.
- Đọc backend URL từ `VITE_API_URL`/`VITE_WS_URL`; không hard-code localhost.
  Biến `VITE_*` gắn lúc build.
- Zustand chỉ giữ state dùng chung; state riêng dùng `useState`.
- Render tin nhắn dạng text; không dùng `dangerouslySetInnerHTML`.
- `ProtectedRoute` gọi `/me`; 401 thì chuyển về `/login`.
- WebSocket tự kết nối lại; dùng `wss://` trên HTTPS và hiển thị trạng thái
  peer. Nội dung UI tiếng Việt, responsive, ưu tiên mobile.
- Onboarding (Giới tính, Ngành, Khóa K63–K71) và Matching (3 bộ lọc cứng) tuân theo
  [QUESTIONNAIRE.md](../docs/QUESTIONNAIRE.md).

## Cấu hình
Dev proxy `/api` qua Vite. Deploy Vercel: Root `frontend`, build `npm run build`,
output `dist`; đặt `VITE_API_URL` và `VITE_WS_URL`. CORS/cookie xem
[DEPLOY.md](../docs/DEPLOY.md).

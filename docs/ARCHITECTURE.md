# Kiến trúc HUST Chatbox

> Cập nhật file này khi kiến trúc thay đổi. Quyết định và lý do nằm ở `DECISIONS.md`.

## 1. Tổng quan
```
Sinh viên (trình duyệt)
   |  HTTPS                         WebSocket (wss)
   v                                   |
Frontend (Vercel) --- gọi API --->  Backend FastAPI (Render) <---
                                       |        |         |
                                       v        v         v
                                  MySQL (Aiven) Redis   Dịch vụ email
```
Khi chạy local: Docker Compose chạy MySQL, Redis, Mailpit; backend và frontend chạy trực tiếp bằng `uvicorn` và `npm run dev`.

## 2. Luồng đăng nhập OTP
```
Client            Backend                Redis             Email
  | request-otp --->| kiểm tra tên miền     |                 |
  |                 | cooldown (SET NX 60s) |                 |
  |                 | SET otp:{h} (TTL 300s)|                 |
  |                 | gửi mail (nền) ------------------------>|
  | verify-otp ---->| GET + so sánh HMAC    |                 |
  |                 | DEL otp:{h}           |                 |
  |<- cookie JWT ---| tạo/tìm user + anon_name                |
```
Chi tiết bảo mật: `../CLAUDE.md` mục 7.

## 3. Luồng ghép cặp và chat
1. Người dùng hoàn tất Onboarding → hồ sơ được mã hóa thành vector multi-hot, lưu `profiles`.
2. `POST /match/join` đưa người dùng vào hàng đợi Redis `queue:matching` (kèm vector).
3. Worker nền (~4 giây): lấy pool → `cosine_matrix` → `greedy_match` (ngưỡng cấu hình) → tạo `conversation` → báo hai người (polling `GET /match/status` hoặc sự kiện).
4. Hai client mở `wss://…/ws/{conversation_id}`; backend xác thực JWT + kiểm tra thuộc phòng → subscribe kênh `room:{id}`; tin nhắn gửi bằng `PUBLISH`.
5. Quá 60 giây chưa ghép được: trạng thái "chưa tìm thấy" (Sprint 3 nối HUST Buddy).

## 4. Khóa Redis
| Khóa | Nội dung | TTL |
|---|---|---|
| `otp:{email_hash}` | HMAC của OTP | 300 giây |
| `otp_cd:{email_hash}` | cooldown gửi OTP | 60 giây |
| `otp_try:{email_hash}` | số lần thử sai | ngắn (≈5 phút) |
| `queue:matching` | hàng đợi ghép cặp (sorted set theo thời điểm vào) | — |
| `profile_vec:{user_id}` | vector hồ sơ trong hàng đợi | theo hàng đợi |
| `room:{conversation_id}` | kênh Pub/Sub của phòng | — |

## 5. Dữ liệu và quyền riêng tư
- Không lưu email thô (chỉ `email_hash`); không lưu nội dung tin nhắn.
- Dữ liệu định danh (Sprint 4) mã hóa AES, chỉ giải mã khi cả hai đồng ý Identity Reveal.

## 6. Môi trường
| Môi trường | Backend | Frontend | MySQL | Redis |
|---|---|---|---|---|
| Local | uvicorn | Vite dev | Docker | Docker |
| Production (thử) | Render | Vercel | Aiven | Render Key Value hoặc dịch vụ khác (cần kiểm tra giới hạn) |

## 7. Lộ trình mở rộng
Sprint 2 Trust Score/Report/Admin → Sprint 3 chatbot RAG (ChromaDB + LLM) → Sprint 4 Semantic Cache/Intent + Identity Reveal → Sprint 5 hoàn thiện (load test, sao lưu, bảo mật).

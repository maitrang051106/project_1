# Kiến trúc Hệ thống HUST Chatbox

## 1. Thành phần tổng quan
```text
Trình duyệt --HTTPS/WSS--> Vercel (React Vite) --> Render (FastAPI Async)
                                                    |-- Aiven / Managed MySQL (Users, Profiles, Friendships, DMs)
                                                    |-- Upstash / Redis (OTP, Cooldown, RateLimit, Matching Queue, Pub/Sub)
                                                    `-- SMTP Server (Gmail / Mailpit)
Local: Docker Compose (MySQL, Redis, Mailpit), Vite và FastAPI chạy riêng.
```

## 2. Luồng dữ liệu chính

### A. Xác thực và Bảo mật Email/OTP
- **Chuẩn hóa & kiểm tra**: Email phải thuộc domain chính xác `@sis.hust.edu.vn`.
- **Định danh trong Redis**: Email được băm bằng HMAC với `EMAIL_HASH_SECRET`. Tuyệt đối không lưu email thô trong Redis key.
- **OTP & Cooldown**: OTP 6 số sinh bằng `secrets`, mã hóa HMAC với domain separation (`hust:otp:{purpose}:{otp}`). Lưu trong Redis với TTL 300s, cooldown 60s, tối đa 5 lần thử sai và hủy sau 1 lần xác thực thành công.
- **Lưu trữ DB (ADR-018)**: Email thô được lưu trong bảng `users` nhằm hỗ trợ đăng nhập mật khẩu, khôi phục mật khẩu và tính năng chia sẻ danh tính khi kết bạn.
- **Chống Account Enumeration & Log Sanitization**: Phản hồi trung tính cho cả email tồn tại lẫn không tồn tại. Mọi exception và log được lọc sạch PII.

### B. Ghép đôi ngẫu nhiên (Matching)
- **Cơ chế**: Ghép đôi đồng bộ (synchronous) trực tiếp khi người dùng gọi `POST /match/join`. Không sử dụng worker định kỳ chạy nền.
- **3 Bộ lọc cứng hai chiều**: Giới tính, Viện/Ngành học, Khóa sinh viên (K63–K71). Chỉ ghép khi thỏa mãn đồng thời cả 2 chiều.
- **Quản lý phiên (Attempt Lifecycle)**: Mỗi lượt ghép được cấp một `attempt_id`. Hàng đợi lưu thông tin ứng viên có TTL 60 giây.
- **Atomic Reservation**: Dùng Redis Lua script (`RESERVE_CANDIDATE_LUA`) để khóa và ghép 2 ứng viên một cách nguyên tử, ngăn ngừa tình trạng ghép trùng khi nhiều user tham gia cùng mili-giây.
- **Timeout 60 giây**: Khi quá 60s không tìm thấy người phù hợp, hệ thống chuyển sang trạng thái `not_found`. Giao diện hiển thị nút "Thử lại ngay" (tạo attempt mới) hoặc "Đổi tiêu chí".

### C. Chat Realtime và Kết bạn (Redis Pub/Sub)
- **Room Chat Ẩn danh**: WebSocket kiểm tra JWT và quyền truy cập phòng trước `accept()`. Tin nhắn được broadcast qua Redis Pub/Sub channel `hust:v1:channel:room:{room_id}` giữa các instance backend.
- **Direct Messages**: Chat 1-1 giữa bạn bè qua WebSocket riêng, broadcast qua Redis Pub/Sub channel `hust:v1:channel:dm:{user_id}`.
- **Kết bạn & Tiết lộ danh tính**: Khi cả 2 đồng ý kết bạn, email và thông tin tài khoản được hiển thị cho đối phương theo ADR-018.

## 3. Quản lý trạng thái Redis
| Dữ liệu | Khóa Redis / Kênh | TTL / Giới hạn |
|---|---|---|
| OTP HMAC | `hust:v1:otp:{purpose}:{email_hash}` | 300 giây, tối đa 5 lần thử sai |
| Cooldown gửi mã | `hust:v1:cooldown:{purpose}:{email_hash}` | 60 giây |
| Rate Limit IP | `hust:v1:ratelimit:ip:{client_ip}` | Cấu hình (mặc định 10 req/phút) |
| Rate Limit Email | `hust:v1:ratelimit:email:{email_hash}` | Cấu hình (mặc định 5 req/phút) |
| Hàng đợi ghép đôi | `hust:v1:match:queue:set` & `hust:v1:match:queue:entry:{uid}` | 65 giây (TTL tự hủy) |
| Kết quả ghép đôi | `hust:v1:match:result:{uid}` | 300 giây |
| Kết quả Timeout | `hust:v1:match:not_found:{uid}` | 300 giây |
| Pub/Sub Room Chat | `hust:v1:channel:room:{room_id}` | Realtime, không lưu trữ |
| Pub/Sub Direct Message | `hust:v1:channel:dm:{user_id}` | Realtime, không lưu trữ |

## 4. Health Checks và Vận hành
- **Readiness (`GET /health`)**: Kiểm tra trực tiếp khả năng kết nối cơ sở dữ liệu (`SELECT 1`) và Redis (`PING`). Trả HTTP 200 khi sẵn sàng hoặc HTTP 503 nếu phụ thuộc bắt buộc gặp sự cố. Dữ liệu phản hồi được sanitized, không làm lộ URL kết nối, mật khẩu hay traceback.
- **Liveness (`GET /live`)**: Kiểm tra tiến trình web đang chạy bình thường (`{"status": "live"}`).

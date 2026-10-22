# HUST Chatbox – Hướng dẫn dự án (đọc file này đầu tiên)

> File "harness" gốc: mô tả dự án để con người và AI coding agent làm việc nhất quán.
> Trạng thái hiện tại luôn nằm ở `docs/PROGRESS.md`. Mỗi thư mục con có `CLAUDE.md` riêng.

## 1. Dự án là gì
Nền tảng chat ẩn danh dành riêng cho sinh viên Đại học Bách khoa Hà Nội (HUST): đăng nhập bằng email `@hust.edu.vn` / `@sis.hust.edu.vn` + mã OTP, được cấp tên ẩn danh (ví dụ `Anonymous_Fox`), được ghép với người có sở thích tương đồng (Cosine Similarity) và chat realtime 1–1.
Về sau: Trust Score dựa trên báo cáo, chatbot HUST Buddy (RAG) khi chưa có người ghép, Identity Reveal khi hai bên đồng ý.

Người làm: sinh viên năm 2, mới biết một chút backend. **Ưu tiên code đơn giản, dễ đọc, có chú thích ngắn bằng tiếng Việt.**

## 2. Phạm vi
**Sprint 1 (tuần 1) – MVP chạy trên Internet:** đăng nhập OTP, hồ sơ sở thích, ghép cặp Cosine, chat realtime, deploy Render + Vercel + Aiven.
**Sau đó:** Sprint 2 Trust Score & Report/Admin · Sprint 3 chatbot RAG · Sprint 4 Semantic Cache/Intent + Identity Reveal · Sprint 5 hoàn thiện.

**NGOÀI phạm vi (đừng tự thêm):**
- Đăng nhập Microsoft Entra ID (đã thay bằng email OTP – xem `docs/DECISIONS.md` ADR-002).
- Kiểm duyệt AI từng tin nhắn (đã bỏ – ADR-004). Trust Score dựa trên báo cáo do admin xác nhận.
- Lưu nội dung tin nhắn vào cơ sở dữ liệu (tin nhắn chỉ đi qua Redis Pub/Sub).

## 3. Công nghệ
| Lớp | Công nghệ |
|---|---|
| Frontend | React + Vite, Tailwind CSS, React Router, Zustand |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, redis-py (asyncio), Pydantic |
| Realtime | WebSocket gốc của FastAPI + Redis Pub/Sub |
| CSDL | MySQL (Aiven khi deploy, Docker khi chạy local) |
| Bộ nhớ đệm / hàng đợi | Redis (OTP, hàng đợi ghép cặp, Pub/Sub, cache) |
| Email | Mailpit khi dev; dịch vụ gửi email/SMTP khi chạy thật |
| Deploy | Backend: Render · Frontend: Vercel · MySQL: Aiven |

## 4. Cấu trúc thư mục
```
hust-chatbox/
  CLAUDE.md              <- file này
  README.md
  docker-compose.yml     <- mysql + redis + mailpit (chạy local)
  .env.example
  backend/               <- FastAPI (xem backend/CLAUDE.md)
  frontend/              <- React + Vite (xem frontend/CLAUDE.md)
  db/                    <- tài liệu schema, seed, sao lưu (xem db/CLAUDE.md)
  docs/                  <- ARCHITECTURE, PROGRESS, DECISIONS, TROUBLESHOOTING, DEPLOY
```

## 5. Lệnh thường dùng
```bash
docker compose up -d                         # MySQL, Redis, Mailpit
cd backend && uvicorn app.main:app --reload  # API tại http://localhost:8000 (/docs, /health)
cd backend && pytest                         # chạy test
cd backend && alembic upgrade head           # áp dụng migration
cd frontend && npm run dev                   # giao diện tại http://localhost:5173
```
Mailpit (xem email OTP khi dev): http://localhost:8025

## 6. Quy ước làm việc
- **Git:** `main` (ổn định) ← `dev` ← `feature/<ten>`. Mỗi tính năng một nhánh, gộp qua Pull Request. Commit theo dạng `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- **Python:** type hints, hàm ngắn, mỗi file một việc. Logic nghiệp vụ đặt trong `services/`, không viết trong route.
- **Đặt tên:** Python `snake_case`; React component `PascalCase`; biến môi trường `UPPER_SNAKE_CASE`.
- **Thay đổi nhỏ, kiểm chứng ngay:** làm một task, chạy test/lệnh để chứng minh nó chạy, rồi mới sang task tiếp.

## 7. Quy tắc bảo mật (không thương lượng)
1. Không bao giờ commit bí mật (`.env`, khóa API, mật khẩu, CA certificate). Chỉ commit `.env.example`.
2. OTP sinh bằng `secrets`; chỉ lưu **bản băm HMAC** trong Redis; TTL 5 phút; dùng một lần.
3. Kiểm tra tên miền email bằng so khớp chính xác (`domain in {"hust.edu.vn","sis.hust.edu.vn"}`), **không** dùng `endswith`.
4. Có cooldown 60 giây, tối đa 5 lần thử OTP sai, rate limit theo IP.
5. Token ở cookie `HttpOnly` + `Secure` + `SameSite`; không lưu token ở `localStorage`.
6. Không lưu email thô trong bảng người dùng: dùng `email_hash` (HMAC có khóa bí mật). Không ghi OTP/email đầy đủ vào log.
7. WebSocket: xác thực JWT và kiểm tra người dùng thuộc phòng trước khi `accept()`.
8. Không render HTML từ tin nhắn người dùng (chống XSS).
9. CORS: chỉ cho phép đúng địa chỉ frontend, không dùng `*` khi có cookie.
10. Mọi quyền phải kiểm tra ở backend; ẩn nút ở giao diện không phải là bảo mật.

## 8. Cách làm việc với AI agent
1. Đọc `CLAUDE.md` này, `docs/PROGRESS.md`, rồi `CLAUDE.md` của thư mục bạn sắp sửa.
2. Trình bày kế hoạch ngắn (các file sẽ tạo/sửa) trước khi viết code cho task lớn.
3. Làm đúng một task theo ID (ví dụ `T-08`) trong `docs/PROGRESS.md`; không làm lan sang task khác.
4. Chạy test/lệnh kiểm chứng và dán kết quả thật; **không khẳng định "đã chạy" nếu chưa chạy**.
5. Nếu thiếu thông tin hoặc có nhiều cách làm hợp lý, hỏi thay vì tự đoán.
6. Không thêm thư viện mới nếu chưa cần; nếu thêm, ghi lý do vào `docs/DECISIONS.md`.

## 9. Ghi lại quá trình (bắt buộc)
- Sau **mỗi task**: cập nhật checkbox và dòng nhật ký trong `docs/PROGRESS.md`.
- Khi chọn giữa các phương án: ghi vào `docs/DECISIONS.md` (bối cảnh, lựa chọn, lý do, đánh đổi).
- Khi gặp lỗi mất hơn 15 phút để sửa: ghi vào `docs/TROUBLESHOOTING.md` (triệu chứng, nguyên nhân, cách sửa).

## 10. Definition of Done (một task xong khi…)
- Code chạy được; có test cho logic chính; test xanh.
- Đã đi qua Pull Request có người review (hoặc tự review kỹ nếu làm một mình).
- Chạy được trên bản deploy (nếu task liên quan đến deploy).
- Đã cập nhật `docs/PROGRESS.md` và tài liệu liên quan; không để lộ bí mật.

# Tiến độ & nhật ký quá trình

> **Cập nhật sau mỗi task** (tick checkbox, ghi 1 dòng vào nhật ký). Ai (hoặc AI) làm việc với repo đều đọc file này trước để biết đang ở đâu.
> Nguồn kế hoạch chi tiết: file Excel `HUST_Chatbox_Agile_Sprint.xlsx` (sheet Backlog). ID task (T-xx) khớp với file đó.

## Trạng thái hiện tại
- **Sprint đang chạy:** Sprint 1 – MVP chạy trên Internet
- **Ngày bắt đầu:** (điền) | **Ngày hiện tại của Sprint:** (điền)
- **Đang làm:** T-01–04 hoàn tất; bước kế tiếp là T-05
- **Bị chặn bởi:** Không có; không thao tác GitHub/Projects theo yêu cầu
- **Bản deploy:** Frontend: (link) · Backend: (link) · Aiven: (đã tạo? Y/N)

## Tổng quan các Sprint
| Sprint | Mục tiêu | Trạng thái |
|---|---|---|
| 1 | Đăng nhập OTP, hồ sơ, ghép cặp Cosine, chat realtime, deploy Render+Vercel+Aiven | Đang làm |
| 2 | Trust Score dựa trên báo cáo, shadowban/khóa, Report + Admin, UX chat | Chưa bắt đầu |
| 3 | Chatbot HUST Buddy (RAG), nối vào luồng "phòng trống" | Chưa bắt đầu |
| 4 | Semantic Cache/Intent/Guided Flow + Identity Reveal | Chưa bắt đầu |
| 5 | Bảo mật, load test, sao lưu, quyền riêng tư, beta rộng | Chưa bắt đầu |

## Sprint 1 – Checklist theo ngày
Quy ước: `- [ ]` chưa làm · `- [x]` xong. Mỗi task xong ghi thêm ngày/giờ thực tế nếu muốn (để rút kinh nghiệm ước lượng).

### Ngày 1 – Khởi động
- [x] T-01 Tạo repo GitHub, nhánh main/dev, .gitignore, README, bảng GitHub Projects (1h) — không thao tác GitHub/Projects theo yêu cầu; hoàn tất nhánh local, `.gitignore`, README.
- [x] T-02 Docker Compose MySQL + Redis (+ Mailpit), .env.example (1.5h)
- [x] T-03 Khung FastAPI: routers/services/core, /health, đọc biến môi trường (2h)
- [x] T-04 Khung frontend: Vite + React + Tailwind + Router + Zustand (2h)
- [ ] T-05 Tạo tài khoản Aiven/Render/Vercel; thử kết nối Aiven (SSL) từ local (1.5h)
- [ ] T-06 ERD, model SQLAlchemy users/profiles/conversations, migration Alembic đầu (3h)

### Ngày 2 – Đăng nhập OTP (backend)
- [ ] T-07 Chuẩn hóa email + kiểm tra tên miền chính xác + test (1h)
- [ ] T-08 API request-otp: sinh OTP (secrets), lưu HMAC vào Redis TTL 5 phút (2h)
- [ ] T-09 Cooldown 60s, tối đa 5 lần thử sai, rate limit IP (2h)
- [ ] T-10 Gửi email OTP tự động (BackgroundTasks; Mailpit khi dev) (3h)
- [ ] T-11 API verify-otp: tạo user, email_hash, anon_name (2h)
- [ ] T-12 JWT cookie HttpOnly; /me, /logout; get_current_user (2h)
- [ ] T-13 pytest cho luồng OTP (5 ca) (1.5h)

### Ngày 3 – Giao diện đăng nhập, Onboarding, deploy sớm
- [ ] T-14 UI đăng nhập 2 bước + đếm ngược gửi lại (3h)
- [ ] T-15 ProtectedRoute + kho user (Zustand) + gọi /me (1.5h)
- [ ] T-16 Onboarding chọn mục tiêu/sở thích; API lưu profile + vector multi-hot (3h)
- [ ] T-17 Deploy backend lên Render (Root Directory = backend) (2h)
- [ ] T-18 Chạy migration lên Aiven (SSL); Render kết nối DB (1.5h)
- [ ] T-19 Deploy frontend lên Vercel (Root Directory = frontend, vercel.json) (1.5h)
- [ ] T-20 CORS + cookie cross-site (hoặc rewrite /api), thử đăng nhập trên bản deploy (2h)

### Ngày 4 – Chat realtime
- [ ] T-21 WebSocket /ws/{room}: xác thực JWT, kiểm tra thuộc phòng (3h)
- [ ] T-22 Redis Pub/Sub chuyển tiếp tin; giới hạn 1000 ký tự + rate limit (3h)
- [ ] T-23 Model/API conversations: tạo/đóng phòng (1.5h)
- [ ] T-24 UI khung chat: bong bóng, auto-scroll, Enter gửi, Zustand (3h)
- [ ] T-25 Client WebSocket tự kết nối lại; thông báo đối phương rời (2h)
- [ ] T-26 Kiểm thử 2 trình duyệt chat qua local (1h)

### Ngày 5 – Ghép cặp Cosine
- [ ] T-27 cosine_matrix + greedy_match (NumPy) + unit test (2.5h)
- [ ] T-28 Hàng đợi Redis: /match/join, /match/leave; mỗi tài khoản 1 vị trí (2h)
- [ ] T-29 Worker nền mỗi 4s: ghép, tạo phòng, báo hai người (3.5h)
- [ ] T-30 Timeout 60s: trạng thái "chưa tìm thấy" (1h)
- [ ] T-31 UI "Đang tìm người phù hợp…" + tự vào phòng chat (2.5h)
- [ ] T-32 Script sinh 100 user giả đo thời gian ghép (1.5h) *(Could)*

### Ngày 6 – Tích hợp & deploy chính thức
- [ ] T-33 Deploy production lần 2: biến môi trường, wss://, xác thực WebSocket (2.5h)
- [ ] T-34 Test end-to-end: điện thoại 4G + laptop (2h)
- [ ] T-35 Sửa lỗi cookie/CORS/WebSocket khi deploy (3h)
- [ ] T-36 Xử lý Render spin-down: thông báo "đang khởi động" + ping /health (1.5h) *(Should)*
- [ ] T-37 Bảo mật tối thiểu: không lộ secret, CORS chặt, rate limit (1.5h)
- [ ] T-38 Trang "Quyền riêng tư" + checkbox đồng ý (1h) *(Should)*

### Ngày 7 – Beta, demo, retro
- [ ] T-39 Beta nhỏ 5–10 bạn, thu phản hồi (2h)
- [ ] T-40 Sửa lỗi ưu tiên cao từ beta (3h)
- [ ] T-41 README: chạy local + deploy + sơ đồ kiến trúc (1.5h)
- [ ] T-42 Sprint Review + Retrospective + chốt backlog Sprint 2 (1.5h)

> Nếu quá tải, cắt theo thứ tự: T-32, T-38, T-36, T-25, T-13. Không cắt: đăng nhập OTP, chat, ghép cặp, deploy.

## Nhật ký hằng ngày
Mẫu mỗi ngày (thêm ở dưới, mới nhất ở trên):
```
### Ngày N – dd/mm/yyyy
- Mục tiêu hôm nay:
- Đã xong: T-xx, T-xx
- Dở dang / chuyển sang ngày mai:
- Vướng mắc (link sang TROUBLESHOOTING nếu có):
- Quyết định đã ghi (ADR-xxx):
- Học được:
- Giờ thực tế / giờ kế hoạch:
```

<!-- Nhật ký bắt đầu từ đây -->

### Ngày 1 – 22/10/2026
- Mục tiêu hôm nay: Dựng nền tảng local cho T-01 đến T-04.
- Đã xong: T-01 phần Git local, `.gitignore`, README; T-02 Compose MySQL/Redis/Mailpit; T-03 FastAPI config/health và test; T-04 Vite/React/Tailwind/Router/Zustand và test.
- Dở dang / chuyển sang ngày mai: Không thao tác GitHub/Projects theo yêu cầu; giữ nguyên remote có sẵn, không push. T-05 trở đi chưa làm.
- Vướng mắc: Cổng host 3306 không bind được trên máy này; xác nhận Compose bằng cổng tạm 3307. Docker services đã healthy.
- Quyết định đã ghi: ADR-008.
- Học được: Dùng `node:test` cho unit test frontend không cần DOM, tránh thêm test runner khi chưa cần.
- Giờ thực tế / giờ kế hoạch: Chưa đo chính xác.

## Sprint Review & Retrospective (điền cuối mỗi Sprint)
```
### Sprint N – dd/mm → dd/mm
- Demo được những gì:
- Chưa xong và lý do:
- Làm tốt:
- Cần cải thiện:
- 3 việc sẽ làm khác ở Sprint sau:
- Ước lượng giờ: kế hoạch ___ / thực tế ___ (điều chỉnh hệ số cho Sprint sau)
```

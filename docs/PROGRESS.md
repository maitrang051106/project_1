# Tiến độ & nhật ký quá trình

> Cập nhật checkbox sau mỗi task; ghi nhật ký ngắn ở cuối. Đây là nguồn trạng
> thái của repo. T-xx khớp backlog dự án.

## Trạng thái hiện tại
- **Sprint đang chạy:** Sprint 1 – MVP chạy trên Internet
- **Ngày bắt đầu:** Chưa ghi
- **Đang làm:** T-01–04 hoàn tất; bước kế tiếp là T-05
- **Bị chặn bởi:** Không có; không thao tác GitHub/Projects theo yêu cầu
- **Bản deploy:** Frontend: (link) · Backend: (link) · Aiven: (đã tạo? Y/N)

## Tổng quan các Sprint
| Sprint | Mục tiêu | Trạng thái |
|---|---|---|
| 1 | Đăng nhập OTP, hồ sơ, matching, chat realtime, deploy Render+Vercel+Aiven | Đang làm |
| 2 | Questionnaire v3, matching có hard filter, Report sau khi kết thúc chat, moderation/trust | Kế hoạch |
| 3 | Chatbot HUST Buddy (RAG), nối vào luồng "phòng trống" | Chưa bắt đầu |
| 4 | Semantic Cache/Intent/Guided Flow + Identity Reveal | Chưa bắt đầu |
| 5 | Bảo mật, load test, sao lưu, quyền riêng tư, beta rộng | Chưa bắt đầu |

## Sprint 1 – Checklist theo ngày
`[ ]` chưa làm · `[x]` hoàn tất.

### Ngày 1 – Khởi động
- [x] T-01 Tạo repo GitHub, nhánh main/dev, .gitignore, README, bảng GitHub Projects (1h) — không thao tác GitHub/Projects theo yêu cầu; hoàn tất nhánh local, `.gitignore`, README.
- [x] T-02 Docker Compose MySQL + Redis (+ Mailpit), .env.example (1.5h)
- [x] T-03 Khung FastAPI: routers/services/core, /health, đọc biến môi trường (2h)
- [x] T-04 Khung frontend: Vite + React + Tailwind + Router + Zustand (2h)
- [x] T-05 Tạo tài khoản Aiven/Render/Vercel; cấu hình Aiven SSL trong db.py/env.py (1.5h)
- [x] T-06 ERD, model SQLAlchemy users/profiles/conversations, migration Alembic đầu (3h)

### Ngày 2 – Đăng nhập OTP (backend)
- [x] T-07 Chuẩn hóa email + kiểm tra tên miền chính xác + test (1h)
- [x] T-08 API request-otp: sinh OTP (secrets), lưu HMAC vào Redis/Store TTL 5 phút (2h)
- [x] T-09 Cooldown 60s, tối đa 5 lần thử sai (2h)
- [x] T-10 Gửi email OTP tự động / log console (3h)
- [x] T-11 API verify-otp: tạo user, email_hash, anon_name (2h)
- [x] T-12 JWT cookie HttpOnly; /me, /logout; get_current_user (2h)
- [x] T-13 pytest cho luồng OTP (test_auth.py: 6 ca test) (1.5h)

### Ngày 3 – Giao diện đăng nhập, Onboarding, deploy sớm
- [x] T-14 UI đăng nhập 2 bước + đếm ngược gửi lại (Login.jsx) (3h)
- [x] T-15 ProtectedRoute + kho user (Zustand) + gọi /me (1.5h)
- [x] T-16 Onboarding theo `docs/QUESTIONNAIRE.md`: Giới tính, Ngành học (68 ngành HUST), Khóa (Onboarding.jsx)
- [x] T-17 Cấu hình deploy backend lên Render (2h)
- [x] T-18 Cấu hình migration lên Aiven (SSL) qua Render Start Command (1.5h)
- [x] T-19 Cấu hình deploy frontend lên Vercel (dist build OK) (1.5h)
- [x] T-20 CORS + cookie cross-site và Vercel routing (2h)

### Ngày 4 – Chat realtime
- [x] T-21 WebSocket /ws/{room}: xác thực JWT, kiểm tra thuộc phòng (3h)
- [x] T-22 Broadcast chuyển tiếp tin; giới hạn 1000 ký tự (3h)
- [x] T-23 Model/API conversations: tạo/kết thúc phòng; đặt `ended_at` (1.5h)
- [x] T-24 UI khung chat: bong bóng, auto-scroll, Enter gửi (Chat.jsx) (3h)
- [x] T-25 Client WebSocket hiển thị thông báo đối phương tham gia/rời (2h)
- [ ] T-26 Kiểm thử 2 trình duyệt chat qua local (1h)

### Ngày 5 – Ghép cặp Cosine
- [x] T-27 Matching 3 bộ lọc cứng hai chiều theo QUESTIONNAIRE.md (matching.py + unit tests)
- [x] T-28 Hàng đợi Redis/Store: /match/join, /match/leave, /match/status (2h)
- [ ] T-29 Worker nền mỗi 4s: ghép, tạo phòng, báo hai người (3.5h)
- [ ] T-30 Timeout 60s: trạng thái "chưa tìm thấy" (1h)
- [x] T-31 UI "Đang tìm người phù hợp…" + tự vào phòng chat (Matching.jsx) (2.5h)
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

## Kế hoạch tiếp theo

Hoàn thiện MVP (bắt đầu T-05), sau đó theo [PLAN.md](PLAN.md):

- [x] P-01 Chuẩn hóa catalog thành CSV seed; kiểm tra 68 mã duy nhất và 10 đơn vị.
- [ ] P-02 Chốt contract questionnaire; `docs/QUESTIONNAIRE.md` là nguồn sự thật.
- [ ] P-03 Migration schema v3: catalog, hồ sơ Q1-Q6 và các bảng report/trust/block/appeal.
- [ ] P-04 API profile và UI onboarding theo questionnaire.
- [ ] P-05/P-06 Matching v2: hard filter, weighted score, timeout và metrics.
- [ ] P-07/P-08 Một chat hoạt động/user; report trong 30 phút; Redis buffer 1 MiB, xóa tin cũ trước; DB evidence mã hóa TTL 30 phút.
- [ ] P-09/P-10 Thu thập dữ liệu report (placeholder 50), trust/ban, quota, block, appeals.
- [ ] P-11 Test tích hợp, migration/rollback, kiểm tra riêng tư và rollout.

Quy tắc nghiệp vụ tại `docs/QUESTIONNAIRE.md`; các câu hỏi còn mở tại
`docs/PLAN.md`.

## Nhật ký
Ghi ngày, task hoàn tất, việc còn lại và trở ngại; mới nhất đặt trên cùng.

<!-- Nhật ký bắt đầu từ đây -->

### Ngày 3 – 27/10/2026
- Đơn giản hóa toàn bộ hệ thống hồ sơ và ghép cặp theo yêu cầu mới (ADR-016):
  - Profile: Giới tính (nam/nữ), Ngành học (68 ngành HUST), Khóa (K63 đến K71).
  - Ghép cặp: 3 ràng buộc hai chiều (giới tính, ngành/trường, khóa).
  - Cập nhật tài liệu quy ước `docs/QUESTIONNAIRE.md`, `db/schema.md`, `docs/DECISIONS.md`.
  - Cập nhật model `Profile`, enum, migration `0001_initial_schema.py`, service `matching.py` và bộ unit test kiểm thử toàn diện.
- Cấu hình SSL Aiven cho `app/core/db.py` và `migrations/env.py`.

### Ngày 2 – 23/10/2026
- T-06: model SQLAlchemy, migration đầu và test metadata.
- Chuẩn hóa questionnaire, schema mục tiêu, roadmap và ADR-009–011.
- Còn lại: T-05 và các task MVP; chưa thử migration với MySQL/Aiven.

### Cập nhật quyết định – 23/10/2026
- Chốt questionnaire v3, ưu tiên Q1, quota lúc tạo conversation, một phòng
  hoạt động/user, không cooldown/shadowban, buffer giới hạn và placeholder `50`.
- Chuyển catalog sang CSV nguồn chuẩn; kiểm tra 68 mã/10 đơn vị. Database
  seeding thuộc P-03.

### Dọn catalog & chốt luồng report retry – 23/10/2026
- Đặt CSV chương trình làm nguồn chuẩn, cập nhật generator/tài liệu và bỏ bản
  Markdown trùng lặp; giữ ghi chú chất lượng dữ liệu.
- Chốt luồng xử lý lỗi snapshot report: nếu snapshot thất bại, API trả về lỗi,
  UI hiển thị thông báo "Gửi report không thành công"(ADR-015).

### Tối ưu tài liệu – 23/10/2026
- Rút gọn hướng dẫn, kiến trúc và roadmap; bỏ nội dung lặp, giữ contract, bảo
  mật, quyết định và checklist đang cần.

### Ngày 1 – 22/10/2026
- Hoàn thành nền local T-01–T-04: Compose, FastAPI và Vite/React.
- Chưa làm T-05 trở đi; không thao tác GitHub/Projects theo yêu cầu.
- Cổng 3306 bận; Docker được kiểm tra bằng cổng tạm 3307. ADR-008: dùng
  `node:test` cho unit test frontend.

# Quyết định kỹ thuật

Giữ ADR cũ để lưu lịch sử; quyết định mới hơn ghi rõ mục nào được thay thế.

## ADR-001: Chỉ dùng Python (FastAPI) cho backend
- Trạng thái: Chấp nhận
- Chọn FastAPI thay vì backend Node.js để giảm số công nghệ và dùng chung hệ
  sinh thái Python. Dùng WebSocket gốc và Redis Pub/Sub.

## ADR-002: Đăng nhập bằng email @hust.edu.vn + OTP, bỏ Microsoft Entra ID
- Trạng thái: Chấp nhận
- Dùng OTP 6 số qua email trường, không dùng Entra ID/mật khẩu. OTP chứng minh
  quyền truy cập hộp thư, không xác minh họ tên; email có thể vào thư rác.

## ADR-003: OTP lưu ở Redis dưới dạng băm HMAC
- Trạng thái: Chấp nhận
- Lưu HMAC trong Redis với TTL; so sánh bằng `hmac.compare_digest`. Bảo vệ
  `OTP_SECRET`; đổi khóa làm mất hiệu lực OTP đang chờ.

## ADR-004: Không kiểm duyệt AI từng tin nhắn
- Trạng thái: Chấp nhận; cách xử lý report/trust được cập nhật bởi ADR-009/012
- Không quét từng tin để giảm độ trễ, chi phí và chia sẻ dữ liệu. Rủi ro: hành
  vi xấu chỉ được xử lý sau report; hỗ trợ report, block và rate limit.

## ADR-005: Không lưu nội dung tin nhắn
- Trạng thái: Thay thế một phần bởi ADR-009
- Không lưu lịch sử chat để bảo vệ riêng tư. Bản evidence mã hóa, có mục đích
  và TTL giới hạn được cho phép theo ADR-009.

## ADR-006: Ghép cặp bằng Cosine Similarity trên vector multi-hot + ghép tham lam
- Trạng thái: Thay thế bởi ADR-010
- Phương án ban đầu: cosine trên vector multi-hot và greedy matching. Đã thay
  bằng hard filters + weighted score theo ADR-010/013.

## ADR-007: Hạ tầng thử nghiệm Render + Vercel + Aiven
- Trạng thái: Chấp nhận (cho bản thử)
- Dùng Render, Vercel, Aiven cho bản thử nghiệm. Giới hạn dịch vụ thay đổi;
  kiểm tra trước khi triển khai.

## ADR-008: Dùng Node.js test runner tích hợp cho frontend
- Ngày: 2026-10-22 | Trạng thái: Chấp nhận
- Dùng `node:test`/`node:assert` cho unit test store, tránh dependency test
  runner; test giao diện cần công cụ DOM/browser riêng nếu phát sinh.

## ADR-009: Chỉ phân loại nội dung khi có report, evidence tạm thời
- Ngày: 2026-10-23 | Trạng thái: Chấp nhận
- Participant được report người còn lại trong 30 phút sau chat. Redis giữ buffer
  trượt 30 phút; report hợp lệ snapshot evidence mã hóa vào DB, xóa sau 30 phút.
  Chưa chọn classifier. Redis TTL không dọn DB evidence; cần job xóa và xử lý
  lỗi snapshot. Không log nội dung chat.

## ADR-012: Chốt wildcard, quota chat và xử lý report giai đoạn đầu
- Ngày: 2026-10-23 | Trạng thái: Thiết kế chấp nhận; mã/quota tại ADR-013,
  catalog tại ADR-014
- Một phòng hoạt động/user, không cooldown; mỗi bên nhận một lượt khi phòng
  tạo thành công. Quota/ngày VN: score `>=90` không giới hạn, `70-89` tối đa
  5, `50-69` tối đa 3, `1-49` tối đa 1; `<=0` bị ban. Không shadowban.
- Redis buffer mỗi phòng tối đa 1 MiB, bỏ tin cũ; report hợp lệ lưu snapshot
  mã hóa 30 phút. Ban đầu chỉ thu thập; placeholder `50` không đổi trust.
- Rủi ro: buffer/TTL có thể khiến evidence thiếu; cần xử lý lỗi snapshot và
  dọn evidence khỏi DB.

## ADR-013: Mã đáp án và ưu tiên tính cách; tính quota lúc bắt đầu chat
- Ngày: 2026-10-23 | Trạng thái: Chấp nhận cho thiết kế
- Mã chuỗi: Q1/Q3 `0`–`3`, Q2 `0`–`2`, Q4-Q6 `0`–`2` + wildcard `3`;
  questionnaire version `3`.
- Personality thay cosine bằng ưu tiên hai chiều: code `0/1` xếp ứng viên
  `0→1→2→3`; code `2/3` xếp `3→2→1→0`. Tổng là weighted score.
- Ghi lượt quota cho mỗi bên khi tạo conversation, theo `started_at` và ngày
  `Asia/Ho_Chi_Minh`.

## ADR-014: Dùng catalog HUST tuyển sinh 2026 đã lưu trong repository
- Ngày: 2026-10-23 | Trạng thái: Chấp nhận cho thiết kế
- CSV [68 chương trình](../db/seed/hust-68-nganh-2026.csv) là nguồn chuẩn;
  script kiểm tra dữ liệu và tạo CSV đơn vị. Không crawl khi seed.
- Giữ mã chương trình làm `major_code`; `faculty_code` là slug nội bộ, không
  phải mã chính thức. Metadata không tham gia matching.
- Catalog tổng hợp; đối chiếu TROY-IT, ED2/ED3/ED5, MS2, MI-E22 và chỉ tiêu
  BF-E12 trước production.

## ADR-015: Xử lý lỗi snapshot evidence khi report
- Ngày: 2026-10-23 | Trạng thái: Chấp nhận cho thiết kế
- Nếu snapshot evidence thất bại (chưa lưu bền vững vào DB), backend không xác
  nhận report thành công mà trả về lỗi; UI hiển thị thông báo "Gửi report không
  thành công".


## ADR-016: Đơn giản hóa hồ sơ và chuyển toàn bộ sang 3 bộ lọc cứng hai chiều
- Ngày: 2026-10-27 | Trạng thái: Chấp nhận
- Xóa bỏ toàn bộ các câu hỏi tính cách, mục tiêu, vector cosine cũ.
- Khi đăng nhập: bắt buộc khai báo 3 thông tin: `gender` (nam/nữ), `major_code`/`faculty_code` (thuộc 68 ngành HUST), `cohort` (khóa K63 đến K71).
- Khi ghép cặp: chỉ áp dụng 3 ràng buộc hai chiều (Two-way Hard Filters):
  1. Giới tính: nam / nữ / bất kì
  2. Ngành/Trường: cùng ngành / cùng trường khác ngành / khác trường / bất kì
  3. Khóa: khóa trên / khóa dưới / cùng khóa / bất kì
- Cả hai người phải cùng thỏa mãn ràng buộc của nhau. Chi tiết tại `docs/QUESTIONNAIRE.md`.


## ADR-017: Authentication with Password, Strict SIS Email, Two-way Friend System & Persistent DMs
- Date: 2026-10-27 | Status: Accepted
- **Email domain restriction**: Only `@sis.hust.edu.vn` allowed (removed `@hust.edu.vn`).
- **Account Registration & Login**:
  - Sign Up: Email $\to$ OTP verification $\to$ Password creation (PBKDF2-HMAC-SHA256 with 100,000 iterations). Auto-login upon registration.
  - Sign In: Email + Password authentication.
  - Password Reset: Email $\to$ OTP $\to$ New password.
- **Identity & UI**: User-selectable custom nicknames and avatar emojis (🦉, 🐱, 🐸, 🐶, 🐵, 🐰, 🐻, 🐧, 🐹, 🦊, 🐼). Entire UI localized in English.
- **Anonymous Chat & Friend System**:
  - Chat displays opponent's avatar and nickname, with real email hidden.
  - Two-way "Add Friend" action: User A clicks "Add Friend", User B receives accept/decline prompt. On acceptance, both real emails are revealed in chat and recorded in `friendships` table.
- **Messages Tab**:
  - 2-column layout: Left column lists friends; right column displays persistent direct messages stored in `direct_messages` table with real-time WebSocket updates.

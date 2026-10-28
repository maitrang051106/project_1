# Kế hoạch questionnaire, matching và report

**Trạng thái:** Hoàn tất giai đoạn P-01 đến P-06. Nguồn nghiệp vụ: 3 bộ lọc cứng hai chiều; schema: [db/schema.md](../db/schema.md).

## Thứ tự triển khai

### Giai đoạn 0 – Hoàn tất nền MVP đang dang dở
Tiếp tục các việc Sprint 1 chưa xong theo [PROGRESS.md](./PROGRESS.md), bắt đầu với T-05 rồi hoàn tất OTP, profile, chat và triển khai cơ bản.

### Giai đoạn 1 – Catalog và questionnaire
**P-01. Chuẩn hóa catalog** — Hoàn tất. CSV chương trình là nguồn chuẩn; 68 mã ngành, 10 đơn vị.
**P-02. Đồng bộ contract hồ sơ & bộ lọc cứng** — Hoàn tất. Dùng chung contract hồ sơ v4 và 3 bộ lọc cứng hai chiều.

### Giai đoạn 2 – Schema và Onboarding
**P-03. Bảng danh mục ngành/trường và hồ sơ người dùng** — Hoàn tất. Bảng `profiles` (gender, faculty_code, major_code, cohort K63–K71).
**P-04. API profile và giao diện Onboarding** — Hoàn tất. Form onboarding 3 bước bắt buộc sau đăng nhập.

### Giai đoạn 3 – Matching hai chiều (Two-Way Hard Filters)
**P-05. Module Matching hai chiều** — Hoàn tất. Đã triển khai và kiểm thử trong `app.services.matching` (`is_mutual_match`) với 3 tiêu chí cứng: Giới tính, Ngành/Viện, Khóa học.

**P-06. Hàng đợi ghép cặp đồng bộ & Timeout 60s** — Hoàn tất.
- Ghép cặp đồng bộ (synchronous matching): quét ứng viên ngay khi gọi `POST /match/join`, sử dụng Redis Lua script để đặt chỗ (reserve) ứng viên nguyên tử, không cần worker chu kỳ chạy nền.
- Quản lý phiên (`attempt_id`): đảm bảo tính phân lập và không nhầm lẫn giữa các lượt tìm kiếm cũ/mới.
- Timeout 60s: sau 60 giây không tìm thấy người phù hợp, chuyển sang trạng thái `not_found`, giao diện hiển thị tùy chọn "Thử lại ngay" (tạo attempt mới) hoặc "Đổi tiêu chí tìm kiếm".
- Hủy tìm kiếm: `POST /match/leave` dọn dẹp hàng đợi và reset về `idle`.

### Giai đoạn 4 – Kết thúc chat và report
**P-07. Kết thúc conversation**
- Bổ sung thao tác kết thúc phòng ở backend và UI; chỉ participant được kết thúc, cập nhật `ended_at` idempotently và thông báo cho peer.
- Sau khi kết thúc, không nhận tin nhắn mới vào phòng đó.

**P-08. Report và lưu evidence ngắn hạn**
- Chỉ participant của conversation đã kết thúc được report participant còn lại trong 30 phút sau `ended_at`.
- Redis giữ buffer theo conversation gồm tin nhắn hai phía. Giới hạn `1 MiB`, xóa tin cũ nhất trước; làm mới TTL khi chat còn hoạt động, đặt TTL 30 phút khi kết thúc và dọn key của phòng stale.
- Snapshot phần buffer còn lại mã hóa vào `report_evidence`; xóa 30 phút sau khi tạo report.

### Giai đoạn 5 – Moderation, trust, block và appeal
**P-09. Moderation theo report**
- Chỉ thu thập dữ liệu từ report hợp lệ. Chưa triển khai hồi quy tuyến tính hay classifier tự động; placeholder trả `50`, không làm thay đổi trust score.
- Trust score khởi đầu `100`; chỉ ban khi score giảm về `0`; không có shadowban.

**P-10. Block, quota, appeal và quản trị**
- Block loại cả hai chiều trong bộ lọc ghép cặp.
- Mỗi user tối đa một conversation đang hoạt động; kết thúc conversation mới được ghép tiếp.
- Quota theo ngày Việt Nam (`Asia/Ho_Chi_Minh`), đếm theo `started_at`.

### Giai đoạn 6 – Kiểm thử và rollout
**P-11. Kiểm thử tích hợp và rollout an toàn**
- Unit tests cho mọi hard filter, rate limits, PII sanitization, OTP HMAC, attempt lifecycle và readiness/liveness probes.
- Kiểm tra phân quyền, TTL Redis, và dọn dữ liệu hết hạn.

## Phụ thuộc
```text
P-01 -> P-02 -> P-03 -> P-04 -> P-05 -> P-06
                         |                 |
                         +-> P-07 -> P-08 -> P-09 -> P-10 -> P-11
```

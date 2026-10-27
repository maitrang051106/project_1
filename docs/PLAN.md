# Kế hoạch questionnaire, matching và report

**Trạng thái:** Chưa triển khai code/migration. Hoàn tất MVP theo
[PROGRESS.md](PROGRESS.md) trước P-02. Nguồn nghiệp vụ:
[QUESTIONNAIRE.md](QUESTIONNAIRE.md); schema: [db/schema.md](../db/schema.md).

## Thứ tự triển khai

### Giai đoạn 0 – Hoàn tất nền MVP đang dang dở

Tiếp tục các việc Sprint 1 chưa xong theo [PROGRESS.md](./PROGRESS.md), bắt đầu
với T-05 rồi hoàn tất OTP, profile, chat và triển khai cơ bản. Không đánh dấu
các việc này hoàn thành bởi tài liệu kế hoạch.

### Giai đoạn 1 – Catalog và questionnaire

**P-01. Chuẩn hóa catalog** — Hoàn tất. CSV chương trình là nguồn chuẩn;
script kiểm tra 68 mã, 10 đơn vị và tạo CSV đơn vị. `faculty_code` là slug
nội bộ. Catalog tổng hợp; xem các mục cần đối chiếu trong
[README database](../db/README.md).

**P-02. Đồng bộ contract hồ sơ & bộ lọc cứng**

Backend/frontend dùng chung contract hồ sơ v4 và 3 bộ lọc cứng hai chiều theo [QUESTIONNAIRE.md](./QUESTIONNAIRE.md).

### Giai đoạn 2 – Schema và Onboarding

**P-03. Bảng danh mục ngành/trường và hồ sơ người dùng**

- Bảng `profiles` đã được chuẩn hóa gồm: `gender`, `faculty_code`, `major_code`, `cohort` (K63–K71).
- Tạo bảng danh mục `faculties`, `majors` từ CSV seed (`db/seed/hust-68-nganh-2026.csv` và `hust-schools-2026.csv`).

**P-04. API profile và giao diện Onboarding**

- Form onboarding 3 bước bắt buộc sau đăng nhập: Giới tính (`nam`/`nu`) -> Ngành học (68 ngành HUST) -> Khóa (K63 đến K71).
- Validate dữ liệu: `major_code` phải tồn tại trong catalog, `cohort` là số nguyên trong khoảng [63, 71].

### Giai đoạn 3 – Matching hai chiều (Two-Way Hard Filters)

**P-05. Module Matching hai chiều**

- Đã triển khai và kiểm thử trong `app.services.matching` (`is_mutual_match`).
- Kiểm tra toàn diện 3 tiêu chí hai chiều:
  1. Giới tính đối phương: `nam`, `nu`, `bat_ki`.
  2. Ngành/Trường đối phương: `cung_nganh`, `cung_truong_khac_nganh`, `khac_truong`, `bat_ki`.
  3. Khóa học đối phương: `khoa_tren`, `khoa_duoi`, `cung_khoa`, `bat_ki`.
- Bỏ hoàn toàn ma trận điểm số mềm, cosine similarity và vector embedding.

**P-06. Hàng đợi ghép cặp và Worker**

- Endpoint `/match/join`, `/match/leave` lưu preference của user vào Redis.
- Worker quét hàng đợi mỗi 4s: tìm cặp đôi thỏa mãn `is_mutual_match()` hai chiều, tạo phòng chat atomic, gửi thông báo qua WebSocket.
- Timeout 60s: thông báo chưa tìm thấy người phù hợp nếu hết thời gian chờ.

### Giai đoạn 4 – Kết thúc chat và report

**P-07. Kết thúc conversation**

- Bổ sung thao tác kết thúc phòng ở backend và UI; chỉ participant được kết
  thúc, cập nhật `ended_at` idempotently và thông báo cho peer.
- Sau khi kết thúc, không nhận tin nhắn mới vào phòng đó.

**P-08. Report và lưu evidence ngắn hạn**

- Chỉ participant của conversation đã kết thúc được report participant còn lại
  trong 30 phút sau `ended_at`.
- Redis giữ buffer theo conversation gồm tin nhắn hai phía. Giới hạn `1 MiB`,
  xóa tin cũ nhất trước; làm mới TTL khi chat còn hoạt động, đặt TTL 30 phút
  khi kết thúc và dọn key của phòng stale.
- Snapshot phần buffer còn lại mã hóa vào `report_evidence`; xóa 30 phút sau
  khi tạo report. Nếu snapshot thất bại, API trả lỗi, UI hiển thị thông báo
  "Gửi report không thành công";
  không báo thành công khi chưa lưu bền vững.

### Giai đoạn 5 – Moderation, trust, block và appeal

**P-09. Moderation theo report**

- Chỉ thu thập dữ liệu từ report hợp lệ. Chưa triển khai hồi quy tuyến tính hay
  classifier tự động; placeholder trả `50`, không làm thay đổi trust score.
- Khi có mô hình sau này, xử lý qua `ConversationClassifier`; không lưu prompt
  hoặc transcript lâu dài.
- Trust score khởi đầu `100`; chỉ ban khi score giảm về `0`; không có
  shadowban.

**P-10. Block, quota, appeal và quản trị**

- Block loại cả hai chiều trong bộ lọc ghép cặp.
- Mỗi user tối đa một conversation đang hoạt động; kết thúc conversation mới
  được ghép tiếp. Tính lượt quota cho cả hai user khi conversation bắt đầu và
  được tạo thành công; xác định ngày theo `started_at` giờ Việt Nam.
- Bảo đảm giới hạn một phòng hoạt động bằng thao tác atomic/lock phía server để
  hai yêu cầu ghép đồng thời không tạo hai conversation cho cùng một user.
- Quota theo ngày Việt Nam (`Asia/Ho_Chi_Minh`), đếm theo `started_at`:
  score `>=90` không giới hạn,
  `70-89` tối đa 5, `50-69` tối đa 3, `1-49` tối đa 1; score `<=0` bị ban.
- Tạo luồng appeal và thao tác review; quyền được kiểm tra tại backend.
- Banned user không được đăng nhập/ghép cặp theo trạng thái.

### Giai đoạn 6 – Kiểm thử và rollout

**P-11. Kiểm thử tích hợp và rollout an toàn**

- Unit tests cho mọi hard filter, placeholder moderation `50` không đổi trust,
  thời gian report, hết hạn evidence, quota và một active conversation/user.
- Integration tests qua MySQL/Redis thực tế local hoặc Testcontainers; thử
  rollback migration và đảm bảo dữ liệu hồ sơ cũ không bị mất.
- Kiểm tra phân quyền report/end/block/appeal, TTL Redis, mã hóa evidence và
  dọn dữ liệu hết hạn.
- Canary rollout sau khi backup; theo dõi queue-empty metrics và lỗi background
  classifier.

## Phụ thuộc

```text
P-01 -> P-02 -> P-03 -> P-04 -> P-05 -> P-06
                         |                 |
                         +-> P-07 -> P-08 -> P-09 -> P-10 -> P-11
```

P-05/P-06 không được bật trước khi profile v2 và catalog đã sẵn sàng. P-09 chỉ
thu thập report data sau khi report/evidence flow hoạt động; mọi hành động tự
động thay đổi trust phải chờ quyết định và mô hình được duyệt sau này.

## Cần chốt trước implementation tương ứng

- Đối chiếu các mục được ghi chú trong catalog trước khi mở rộng sử dụng.
- Quyền reviewer và quy trình appeal trước khi triển khai luồng appeal.

Thực hiện theo dependency; kế hoạch không thay thế migration, kiểm thử hoặc
phê duyệt triển khai.

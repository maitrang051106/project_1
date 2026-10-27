# Backend – FastAPI

Đọc hướng dẫn gốc [../CLAUDE.md](../CLAUDE.md). Tài liệu nghiệp vụ chuẩn:
[questionnaire/matching](../docs/QUESTIONNAIRE.md), [roadmap](../docs/PLAN.md).

## Quy tắc triển khai
- Route xác thực/điều phối; nghiệp vụ đặt trong `services/`.
- Dùng async nhất quán; không chạy tác vụ blocking trong route async.
- Gửi email nền; lỗi và log không được tiết lộ email/OTP.
- Lỗi API ngắn gọn, không tiết lộ việc email có tài khoản hay không.
- Chạy app từ `backend/`: `python -m uvicorn app.main:app --reload`.

## Bảo mật OTP
Chuẩn hóa email, so khớp domain chính xác; OTP 6 số sinh bằng `secrets`, chỉ
lưu HMAC trong Redis với TTL 300 giây, dùng một lần. Cooldown 60 giây; tối đa
5 lần sai rồi hủy OTP. So sánh bằng `hmac.compare_digest`. JWT cookie có
`HttpOnly`, `Secure`, `SameSite`; không ghi bí mật vào log.

## Chat và ghép cặp
- WebSocket phải xác thực JWT và membership trước `accept()`. Giới hạn tin
  nhắn 1000 ký tự/tốc độ; dùng Redis Pub/Sub, hủy task khi disconnect.
- Không lưu transcript dài hạn. Buffer mỗi conversation tối đa 1 MiB, bỏ tin
  cũ nhất; hết hạn sau 30 phút kể từ khi chat kết thúc.
- Chỉ participant kết thúc phòng; sau `ended_at` không nhận tin mới.
- Hồ sơ người dùng gồm gender, major_code, faculty_code, cohort (K63–K71). Matching dùng
  3 bộ lọc cứng hai chiều theo QUESTIONNAIRE.md; không dùng vector/cosine/score mềm;
  một chat hoạt động/user, không cooldown.
- Quota tính lúc conversation được tạo thành công theo `started_at` và ngày
  `Asia/Ho_Chi_Minh`. Mức quota và trust xem QUESTIONNAIRE.md.
- Report trong 30 phút sau chat; chỉ snapshot evidence mã hóa khi report hợp
  lệ. Xóa evidence sau 30 phút bằng job riêng.
- Moderation ban đầu chỉ thu thập dữ liệu; placeholder `50` không đổi trust.

## Cấu hình, test và deploy
Biến môi trường trong `.env.example`. Chạy test bằng `python -m pytest`.
Deploy Render: Root `backend`; build `pip install -r requirements.txt`;
start `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`;
health check `/health`. Xem [DEPLOY.md](../docs/DEPLOY.md).

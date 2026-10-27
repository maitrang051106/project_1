# Kiến trúc

## Thành phần
```text
Trình duyệt --HTTPS/WSS--> Vercel (React) --> Render (FastAPI)
                                               |-- Aiven MySQL
                                               |-- Redis
                                               `-- SMTP
Local: Docker Compose (MySQL, Redis, Mailpit), Vite và FastAPI chạy riêng.
```

## Luồng chính
- **OTP:** kiểm tra domain → cooldown → tạo OTP → lưu HMAC trong Redis 300s →
  gửi email → xác minh một lần → phát JWT cookie. Bảo mật chi tiết tại
  [CLAUDE.md](../CLAUDE.md).
- **Matching:** hồ sơ gồm giới tính, ngành học, khóa. Hàng đợi ở Redis; worker
  áp 3 bộ lọc cứng hai chiều (is_mutual_match). Tạo phòng atomic, tối đa một
  phòng hoạt động/user; quota tính từ `started_at`.
- **Chat:** WebSocket xác thực JWT và membership trước khi accept; Redis
  Pub/Sub chuyển tin giữa hai phía. Kết thúc phòng ghi `ended_at`.
- **Report:** Redis giữ buffer tối đa 1 MiB, bỏ tin cũ trước; TTL 30 phút sau
  khi kết thúc. Report hợp lệ trong 30 phút có thể snapshot evidence mã hóa vào
  DB, xóa 30 phút sau khi tạo.

## Redis
| Dữ liệu | TTL/giới hạn |
|---|---|
| OTP HMAC | 300 giây |
| Cooldown OTP | 60 giây |
| Matching queue/profile cache | Thời gian chờ trong queue |
| Pub/Sub room | Theo vòng đời phòng |
| Buffer hội thoại | 1 MiB; TTL trượt khi hoạt động, 30 phút sau khi kết thúc |

## Quyền riêng tư và vận hành
- Không lưu email thô hoặc lịch sử chat dài hạn.
- Moderation ban đầu chỉ thu thập report; placeholder `50` không đổi trust.
- Chỉ ban khi trust về `0`; không có shadowban.
- Quyết định sản phẩm xem [DECISIONS.md](DECISIONS.md); roadmap xem
  [PLAN.md](PLAN.md); triển khai xem [DEPLOY.md](DEPLOY.md).

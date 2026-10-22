# Nhật ký quyết định (ADR)

> Mỗi quyết định kỹ thuật quan trọng ghi một mục. Không xóa mục cũ; nếu đổi ý, thêm mục mới và đánh dấu mục cũ là "Thay thế bởi ADR-xxx".

Mẫu:
```
## ADR-00X: <Tiêu đề>
- Ngày: yyyy-mm-dd | Trạng thái: Đề xuất / Chấp nhận / Thay thế bởi ADR-xxx
- Bối cảnh: …
- Lựa chọn: …
- Lý do: …
- Đánh đổi / rủi ro: …
```

## ADR-001: Chỉ dùng Python (FastAPI) cho backend
- Trạng thái: Chấp nhận
- Bối cảnh: Đề cương ban đầu dùng cả Python và Node.js.
- Lựa chọn: Chỉ FastAPI.
- Lý do: Giảm khối lượng học cho người mới; FastAPI hỗ trợ WebSocket/async và cùng hệ sinh thái AI/ML (NumPy, embedding, RAG).
- Đánh đổi: Không tận dụng Socket.IO của Node.js; dùng WebSocket gốc + Redis Pub/Sub.

## ADR-002: Đăng nhập bằng email @hust.edu.vn + OTP, bỏ Microsoft Entra ID
- Trạng thái: Chấp nhận
- Bối cảnh: Đăng ký ứng dụng trong tenant Entra ID của trường cần quyền admin nhà trường.
- Lựa chọn: Gửi OTP 6 số tới email trường; không dùng mật khẩu.
- Lý do: Không phụ thuộc nhà trường; đơn giản; chứng minh sở hữu hộp thư HUST.
- Đánh đổi: OTP chỉ chứng minh quyền sở hữu hộp thư, **không** xác thực họ tên. Identity Reveal (Sprint 4) chỉ hiển thị email đã xác thực (và MSSV nếu trích được từ định dạng email, cần kiểm tra thực tế). Email có thể vào thư rác; cần dịch vụ gửi email đáng tin cậy.

## ADR-003: OTP lưu ở Redis dưới dạng băm HMAC
- Trạng thái: Chấp nhận
- Lý do: TTL tự hết hạn; nếu Redis bị lộ vẫn không đọc được OTP đang hiệu lực. So sánh bằng `hmac.compare_digest`.
- Đánh đổi: Cần giữ bí mật `OTP_SECRET`; đổi khóa sẽ làm mất hiệu lực OTP đang chờ.

## ADR-004: Bỏ kiểm duyệt AI từng tin nhắn
- Trạng thái: Chấp nhận
- Bối cảnh: Đề cương ban đầu dùng mô hình phân loại chấm xác suất vi phạm cho mọi tin nhắn.
- Lựa chọn: Không quét từng tin. Trust Score dựa trên báo cáo (Report) do admin xác nhận; có shadowban (<50) và khóa (=0).
- Lý do: Giảm độ phức tạp, độ trễ, chi phí và chia sẻ dữ liệu với bên thứ ba.
- Đánh đổi: Lừa đảo/quấy rối chỉ bị xử lý sau khi có báo cáo. Giảm thiểu: nút Report dễ thấy, chặn người dùng, banner cảnh báo an toàn, rate limit. Có thể bổ sung kiểm duyệt tự động sau.

## ADR-005: Không lưu nội dung tin nhắn
- Trạng thái: Chấp nhận
- Lý do: Quyền riêng tư; giảm rủi ro rò rỉ dữ liệu. Tin nhắn chỉ đi qua Redis Pub/Sub.
- Đánh đổi: Không có lịch sử chat; báo cáo vi phạm dựa vào mô tả của người báo cáo (có thể xem lại sau nếu cần lưu có thời hạn).

## ADR-006: Ghép cặp bằng Cosine Similarity trên vector multi-hot + ghép tham lam
- Trạng thái: Chấp nhận
- Lý do: Đơn giản, đủ nhanh cho vài nghìn người dùng bằng NumPy; không cần vector DB.
- Đánh đổi: Ghép tham lam không tối ưu toàn cục; ngưỡng cao thì chờ lâu, ngưỡng thấp thì kém phù hợp (cần đo và chỉnh).

## ADR-007: Hạ tầng thử nghiệm Render + Vercel + Aiven
- Trạng thái: Chấp nhận (cho bản thử)
- Lý do: Có gói miễn phí/giá thấp, dễ dùng.
- Đánh đổi: Render free tự tắt khi nhàn rỗi (khởi động lại mất khoảng 1 phút) và ổ đĩa tạm thời; Aiven free có giới hạn tài nguyên; Redis cần dịch vụ riêng. Kiểm tra giới hạn hiện tại trước khi dựa vào.

## ADR-008: Dùng Node.js test runner tích hợp cho frontend
- Ngày: 2026-10-22 | Trạng thái: Chấp nhận
- Bối cảnh: T-04 cần test cho Zustand store; các test hiện tại không cần DOM hay mock trình duyệt.
- Lựa chọn: Dùng `node:test` và `node:assert/strict` có sẵn, chạy qua `npm test`.
- Lý do: Đủ cho test đơn vị hiện tại, tránh thêm test runner bên thứ ba; npm audit sau khi bỏ Vitest báo không có lỗ hổng.
- Đánh đổi / rủi ro: Test giao diện React cần công cụ DOM/browser riêng nếu được bổ sung ở task sau.

<!-- Thêm ADR-009, ADR-010… bên dưới -->

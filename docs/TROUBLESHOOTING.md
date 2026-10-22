# Nhật ký sự cố & cách sửa

> Ghi mỗi lần gặp lỗi mất hơn ~15 phút để sửa. Đây là tài liệu học tập quý giá và giúp tránh lặp lại.

Mẫu:
```
### [yyyy-mm-dd] Tiêu đề ngắn
- Task: T-xx
- Triệu chứng: (thông báo lỗi, hành vi sai)
- Nguyên nhân gốc:
- Cách sửa:
- Bài học / cách phòng tránh:
```

## Các lỗi thường gặp cần để ý (dự đoán, chưa phải đã xảy ra)
| Tình huống | Hướng kiểm tra |
|---|---|
| Đăng nhập được ở local nhưng mất phiên trên bản deploy | Cookie `SameSite`/`Secure`, CORS có `allow_credentials`, frontend khác tên miền backend |
| WebSocket không kết nối trên Render | Dùng `wss://`, kiểm tra token xác thực, dịch vụ có đang "ngủ" không |
| Không kết nối được Aiven | SSL/CA certificate, host/port, thử bằng `mysql` client |
| `redis.get()` trả bytes | Tạo client với `decode_responses=True` |
| Biến `VITE_*` không đổi sau khi sửa | Biến gắn lúc build; Redeploy |
| Tải lại trang trên Vercel bị 404 | Thiếu `vercel.json` rewrite về `/index.html` |
| OTP email vào thư rác / không tới | Kiểm tra dịch vụ gửi email, SPF/DKIM, thử hộp thư @hust.edu.vn thật |
| Start command Render báo không tìm thấy module | Dùng `app.main:app` theo cấu trúc thư mục `backend/app/` |

## Nhật ký
<!-- Thêm mục mới ở đây, mới nhất ở trên cùng -->

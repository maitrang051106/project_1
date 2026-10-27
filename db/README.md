# Database: migration và catalog

## Migration
Trong `backend/`, cấu hình `DATABASE_URL` rồi chạy:

```powershell
python -m alembic upgrade head
```

`DATABASE_URL` dùng driver `mysql+aiomysql`; cấu hình SSL theo yêu cầu Aiven.
Không commit credential hoặc CA. Kiểm tra revision:

```powershell
python -m alembic current
```

Đọc migration và sao lưu trước khi áp dụng lên dữ liệu thật; không sửa schema
trực tiếp trên Aiven. Thiết kế: [schema.md](schema.md).

## Catalog seed
`seed/hust-68-nganh-2026.csv` là nguồn chuẩn gồm 68 chương trình; chỉnh sửa
catalog trực tiếp trong file này. Tạo lại
[CSV đơn vị](seed/hust-schools-2026.csv) và kiểm tra số lượng/mã bằng lệnh:

```powershell
python db/seed/generate_hust_catalog.py
```

Không crawl website khi import. Catalog được tổng hợp; cần đối chiếu
TROY-IT, ED2/ED3/ED5, MS2, MI-E22 và chỉ tiêu BF-E12 trước khi dùng production.

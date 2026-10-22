# Prompt thiết lập dự án HUST Chatbox

## Cách dùng
1. Tạo repo rỗng và copy bộ file harness (`CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`, `db/CLAUDE.md`, `docs/*`) vào đúng vị trí.
2. Mở AI coding agent (ví dụ Claude Code) tại thư mục gốc repo.
3. Dán **toàn bộ nội dung trong khung PROMPT bên dưới**.
4. Theo dõi từng bước, đọc kết quả lệnh agent chạy, và chỉ duyệt khi hiểu agent đang làm gì.

Prompt này chỉ dựng **khung dự án (Sprint 1 – Ngày 1, tương ứng T-01…T-06)**. Các tính năng OTP, chat, ghép cặp sẽ làm ở các task sau bằng "Prompt mẫu cho task tiếp theo" ở cuối file.

---

## PROMPT

````
Bạn là kỹ sư phần mềm senior, đang giúp một sinh viên năm 2 (mới biết một chút backend) dựng khung dự án "HUST Chatbox". Hãy ưu tiên code đơn giản, dễ đọc, chú thích ngắn bằng tiếng Việt, và giải thích ngắn gọn lý do khi có lựa chọn quan trọng.

## 1. Đọc trước khi làm
Đọc các file sau (đã có sẵn trong repo) và coi chúng là nguồn sự thật:
- CLAUDE.md (gốc), backend/CLAUDE.md, frontend/CLAUDE.md, db/CLAUDE.md
- docs/ARCHITECTURE.md, docs/DECISIONS.md, docs/PROGRESS.md
Nếu có mâu thuẫn giữa prompt này và các file đó, hãy dừng lại và hỏi tôi.

## 2. Nhiệm vụ: dựng khung dự án (CHƯA cài đặt tính năng)
Thực hiện lần lượt, hoàn thành và kiểm chứng từng bước trước khi sang bước tiếp theo.

### Bước 1 – Git và tệp gốc (T-01)
- Nếu chưa phải repo git thì `git init`; tạo nhánh `dev` từ `main`; làm việc trên nhánh `feature/scaffold` rồi báo tôi trước khi gộp.
- Tạo `.gitignore` (Python, Node, `.env`, `__pycache__`, `node_modules`, `dist`, file dump `*.sql.gz`, thư mục IDE).
- Tạo `.env.example` ở gốc và trong `backend/`, `frontend/` với các biến đã liệt kê trong các CLAUDE.md (giá trị mẫu, KHÔNG bí mật thật).
- Cập nhật `README.md`: mô tả ngắn, cách chạy local (cho cả Windows và macOS/Linux nếu khác nhau), liên kết sang docs/.

### Bước 2 – Docker Compose (T-02)
- `docker-compose.yml` gồm: `mysql` (8.x, volume, cổng 3306, biến môi trường từ `.env`), `redis` (7.x, cổng 6379), `mailpit` (SMTP 1025, giao diện 8025).
- Có `restart: unless-stopped` và healthcheck cho mysql/redis.
- Chạy `docker compose up -d` và xác nhận 3 dịch vụ khỏe mạnh.

### Bước 3 – Backend FastAPI (T-03, T-06)
Trong `backend/` theo đúng cấu trúc ở `backend/CLAUDE.md`:
- `requirements.txt`: cài thật bằng pip và ghim phiên bản đã cài được thành công (fastapi, uvicorn, sqlalchemy[asyncio], một driver MySQL async, alembic, redis, pydantic-settings, pytest, httpx, pytest-asyncio, numpy). Không thêm thư viện thừa.
- `app/core/config.py` (pydantic-settings), `db.py` (async engine + `get_db`), `redis.py` (`decode_responses=True`), `security.py` (khung rỗng có chú thích).
- `app/main.py` với endpoint `GET /health` trả `{"status": "ok"}`; include router từ `app/api/health.py`.
- Models SQLAlchemy 2.0 cho `User`, `Profile`, `Conversation` đúng theo `db/CLAUDE.md` (không thêm bảng khác).
- Cấu hình Alembic chạy được với engine async; sinh migration đầu tiên bằng autogenerate, **đọc lại file migration** rồi mới chạy `alembic upgrade head` trên MySQL local; kiểm tra bảng đã tạo.
- `tests/test_health.py` kiểm tra `/health`; chạy `pytest` và báo kết quả.
- `Dockerfile` đơn giản (python slim, chạy `uvicorn app.main:app --host 0.0.0.0 --port $PORT` với mặc định cổng 8000).
- Các file còn lại trong cấu trúc (`api/auth.py`, `services/otp.py`, …): chỉ tạo file rỗng có docstring một dòng mô tả mục đích. KHÔNG cài đặt OTP, WebSocket, ghép cặp.

### Bước 4 – Frontend (T-04)
Trong `frontend/` theo `frontend/CLAUDE.md`:
- Tạo dự án Vite + React; cài Tailwind CSS (làm theo hướng dẫn chính thức hiện hành của Tailwind), React Router, Zustand.
- Trang placeholder: `Login`, `Onboarding`, `Matching`, `Chat` (chỉ tiêu đề + mô tả), `ProtectedRoute` khung, router cơ bản.
- `src/lib/api.js` (fetch với `credentials: "include"`, địa chỉ lấy từ `import.meta.env.VITE_API_URL`), `src/store/auth.js`, `src/store/chat.js` (khung).
- `vite.config.js` có proxy `/api` → `http://localhost:8000`.
- `vercel.json` rewrite mọi đường dẫn về `/index.html`.
- Chạy `npm run build` và `npm run dev`; xác nhận build thành công.

### Bước 5 – Thư mục db/ (T-06)
- Tạo `db/README.md` (kết nối local + Aiven SSL + sao lưu/khôi phục cơ bản) và `db/schema.md` khớp migration vừa sinh.
- Thêm khung `db/seed/seed_users.py` (chỉ docstring + TODO, chưa cài đặt).

### Bước 6 – Kiểm chứng toàn bộ
Chạy và báo kết quả THẬT của từng lệnh:
1. `docker compose ps`
2. `cd backend && alembic upgrade head && pytest`
3. `cd backend && uvicorn app.main:app` rồi gọi `GET /health`
4. `cd frontend && npm run build`
Nếu lệnh nào lỗi: đọc lỗi, sửa gốc rễ, chạy lại; KHÔNG khẳng định thành công khi chưa chạy.

## 3. Ràng buộc
- Không cài đặt tính năng ngoài phạm vi khung (OTP, chat, ghép cặp, chatbot).
- Không đưa bí mật hoặc khóa thật vào bất kỳ file nào; không commit `.env`.
- Không dùng Microsoft Entra ID; không thêm kiểm duyệt AI từng tin nhắn; không lưu nội dung tin nhắn (xem ADR-002, ADR-004, ADR-005).
- Không xóa hay ghi đè các file md harness; chỉ cập nhật `README.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md`, `docs/TROUBLESHOOTING.md` khi cần.
- Không thêm thư viện ngoài danh sách khi chưa giải thích lý do và chờ tôi đồng ý.
- Nếu thiếu thông tin hoặc có nhiều cách hợp lý, hỏi tôi một câu rõ ràng thay vì tự đoán.
- Mỗi bước hoàn thành: một commit nhỏ, thông điệp theo dạng `chore:`, `feat:`, `docs:`.

## 4. Ghi lại quá trình (bắt buộc)
- Sau mỗi bước: tick checkbox T-01…T-06 trong `docs/PROGRESS.md` và thêm một mục "Ngày 1" vào nhật ký (đã xong gì, vướng mắc, học được, giờ thực tế nếu biết).
- Mỗi quyết định kỹ thuật mới (ví dụ chọn driver MySQL async, cách cấu hình Alembic): thêm ADR mới vào `docs/DECISIONS.md`.
- Mỗi lỗi mất nhiều thời gian: ghi vào `docs/TROUBLESHOOTING.md` theo mẫu có sẵn.

## 5. Báo cáo cuối
Kết thúc bằng bản tóm tắt gồm:
1. Danh sách file/thư mục đã tạo.
2. Kết quả thật của các lệnh kiểm chứng (dán đầu ra rút gọn).
3. Những điểm chưa chắc hoặc cần tôi quyết định.
4. Gợi ý task tiếp theo (T-07…) và những điều tôi cần học trước (Bài nào trong giáo trình).
````

---

## Prompt mẫu cho task tiếp theo (dùng lại cho mọi task)

```
Hãy làm task <T-xx>: "<tên task>" trong docs/PROGRESS.md.

Trước khi viết code:
1. Đọc CLAUDE.md gốc, CLAUDE.md của thư mục liên quan và docs/PROGRESS.md.
2. Trình bày kế hoạch ngắn: file sẽ tạo/sửa, cách kiểm chứng. Chờ tôi đồng ý nếu thay đổi lớn.

Khi làm:
- Chỉ làm đúng task này; không lan sang task khác.
- Tuân thủ quy tắc bảo mật trong CLAUDE.md mục 7.
- Viết test cho logic chính và chạy; dán kết quả thật.

Sau khi xong:
- Tick checkbox T-xx trong docs/PROGRESS.md và thêm dòng nhật ký.
- Ghi ADR nếu có quyết định mới; ghi TROUBLESHOOTING nếu gặp lỗi khó.
- Tạo commit nhỏ theo quy ước và tóm tắt: đã làm gì, kiểm chứng thế nào, còn rủi ro gì.
```

## Gợi ý prompt cho các task chính
| Task | Mở đầu prompt gợi ý |
|---|---|
| T-07…T-13 (OTP) | "Cài đặt luồng đăng nhập OTP theo backend/CLAUDE.md mục 'Luồng OTP'. Bắt đầu bằng test trước cho kiểm tra tên miền (gồm fakehust.edu.vn)." |
| T-21…T-22 (WebSocket) | "Cài đặt WebSocket /ws/{room} theo backend/CLAUDE.md, xác thực JWT, kiểm tra thuộc phòng, Redis Pub/Sub, không lưu nội dung tin nhắn." |
| T-27…T-29 (Ghép cặp) | "Cài đặt cosine_matrix, greedy_match và worker theo backend/CLAUDE.md mục 'Ghép cặp'. Viết unit test trước." |
| T-17…T-20 (Deploy) | "Giúp tôi deploy theo docs/DEPLOY.md. Hướng dẫn từng bước, tôi sẽ tự thao tác trên Render/Vercel/Aiven, đừng yêu cầu tôi dán khóa bí mật vào chat." |

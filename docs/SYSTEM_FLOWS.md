# TÀI LIỆU PHÂN TÍCH TOÀN BỘ LUỒNG HOẠT ĐỘNG VÀ BIỂU ĐỒ HỆ THỐNG HUST CHATBOX

> **Dự án:** HUST Chatbox - Nền tảng kết nối & chat ẩn danh 1-1 cho sinh viên Đại học Bách Khoa Hà Nội  
> **Ngôn ngữ & Công nghệ:** FastAPI, Python 3.12+, React 18, Vite, TailwindCSS, SQLAlchemy (Async), MySQL, Redis / In-Memory Fallback, WebSocket  
> **Ngày phân tích:** 27/10/2026  
> **Tài liệu nguồn kiểm chứng:** Toàn bộ mã nguồn `backend/` và `frontend/` trong kho dự án.

---

## MỤC LỤC
1. [Tổng quan Kiến trúc Hệ thống (System Architecture)](#1-tổng-quan-kiến-trúc-hệ-thống)
2. [Sơ đồ Thực thể Cơ sở Dữ liệu (Database ERD)](#2-sơ-đồ-thực-thể-cơ-sở-dữ-liệu-erd)
3. [Luồng 1: Xác thực & Quản lý Tài khoản (Authentication Flow)](#3-luồng-1-xác-thực--quản-lý-tài-khoản)
   - 3.1. Đăng ký tài khoản với Email OTP
   - 3.2. Đăng nhập Email & Mật khẩu
   - 3.3. Quên mật khẩu & Đặt lại mật khẩu (Reset Password)
   - 3.4. Khôi phục phiên làm việc (Session Restore & /me)
   - 3.5. Đăng xuất (Sign Out)
4. [Luồng 2: Khai báo & Quản lý Hồ sơ (Profile & Onboarding Flow)](#4-luồng-2-khai-báo--quản-lý-hồ-sơ)
   - 4.1. Tải danh mục 68 ngành học & 10 Viện/Trường HUST
   - 4.2. Khai báo hồ sơ sinh viên (Giới tính, Ngành, Khóa K63-K71, Nickname, Avatar)
5. [Luồng 3: Ghép cặp Ẩn danh theo 3 Bộ lọc Cứng Hai Chiều (Matching Flow)](#5-luồng-3-ghép-cặp-ẩn-danh-theo-3-bộ-lọc-cứng-hai-chiều)
   - 5.1. Cơ chế 3 bộ lọc cứng hai chiều (is_mutual_match)
   - 5.2. Luồng tức thì (Instant Match) vs. Luồng chờ hàng đợi (Queue & Polling)
6. [Luồng 4: Phòng Chat Realtime Ẩn danh & Tiết lộ Danh tính (Realtime Anonymous Chat)](#6-luồng-4-phòng-chat-realtime-ẩn-danh--tiết-lộ-danh-tính)
   - 6.1. Bắt tay WebSocket, xác thực JWT & kiểm tra tư cách thành viên
   - 6.2. Trao đổi tin nhắn văn bản ẩn danh
   - 6.3. Luồng kết bạn & Tiết lộ danh tính (Friend Request & Identity Reveal)
   - 6.4. Kết thúc phòng chat & Ngắt kết nối
7. [Luồng 5: Nhắn tin Trực tiếp giữa Bạn bè (Direct Messaging Flow)](#7-luồng-5-nhắn-tin-trực-tiếp-giữa-bạn-bè)
   - 7.1. Danh sách bạn bè & hội thoại gần nhất
   - 7.2. Kênh WebSocket nhắn tin trực tiếp riêng (Direct Message WS)
8. [Bảng Tra cứu API Endpoints & WebSocket Routes](#8-bảng-tra-cứu-api-endpoints--websocket-routes)
9. [Cơ chế Bảo mật, Khả năng Chịu lỗi & Fallback Tự động](#9-cơ-chế-bảo-mật-khả-năng-chịu-lỗi--fallback-tự-động)

---

## 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

Hệ thống được thiết kế theo mô hình **Client-Server kiến trúc hiện đại**, phân tách rõ ràng giữa Single Page Application (SPA Frontend) và API Server không trạng thái (Stateless Backend), kết hợp cơ chế Stateful Realtime qua WebSocket và Bộ lưu trữ kép (Dual Store: Redis hoặc In-memory Fallback).

```mermaid
flowchart TB
    subgraph ClientLayer["Lớp Trình duyệt (Client Application)"]
        UI["React 18 SPA (Vite + TailwindCSS)"]
        Store["Zustand Auth Store"]
        WSC["Native WebSocket Client"]
        UI <--> Store
        UI <--> WSC
    end

    subgraph GatewayLayer["Lớp Mạng & Điều phối (Gateway / Protocol)"]
        HTTP_EP["REST API (HTTPS - JSON)"]
        WS_EP["WebSocket (WSS - Realtime Pub/Sub)"]
    end

    subgraph BackendLayer["Lớp Xử lý Trung tâm (FastAPI Backend)"]
        AuthRouter["auth.py (Xác thực, OTP, JWT)"]
        ProfileRouter["profile.py (Hồ sơ, 68 Ngành HUST)"]
        MatchRouter["matching.py (Ghép đôi 3 bộ lọc)"]
        ChatRouter["chat.py (Phòng chat ẩn danh, Kết bạn)"]
        DMRouter["direct_messages.py (Chat bạn bè 1-1)"]
        MatchService["matching.py (Thuật toán is_mutual_match)"]
        CatalogService["catalog.py (Catalog HUST)"]
        StoreService["store.py (Quản lý State, Broadcast)"]
    end

    subgraph DataLayer["Lớp Lưu trữ Dữ liệu (Persistence & Cache)"]
        MySQL[("MySQL Database\n(Users, Profiles, Conversations,\nFriendships, DirectMessages)")]
        RedisCache[("Redis Server / In-Memory Fallback\n(OTP HMAC, Cooldown, Matching Queue,\nRealtime Room Queues)")]
        Mailpit[("SMTP Service / Mailpit\n(Gửi mã OTP sinh viên)")]
    end

    UI -->|HTTPS Requests + HttpOnly Cookie| HTTP_EP
    WSC -->|WebSocket Connection + JWT Cookie| WS_EP

    HTTP_EP --> AuthRouter & ProfileRouter & MatchRouter & ChatRouter & DMRouter
    WS_EP --> ChatRouter & DMRouter

    AuthRouter --> StoreService & Mailpit & MySQL
    ProfileRouter --> CatalogService & MySQL
    MatchRouter --> MatchService & StoreService & MySQL
    ChatRouter --> StoreService & MySQL
    DMRouter --> StoreService & MySQL
```

---

## 2. SƠ ĐỒ THỰC THỂ CƠ SỞ DỮ LIỆU (DATABASE ERD)

Cơ sở dữ liệu quan hệ được xây dựng chặt chẽ với các ràng buộc khóa ngoại, chỉ mục hiệu năng cao và các kiểu dữ liệu Enum.

```mermaid
erDiagram
    USERS ||--o| PROFILES : "has (1-1)"
    USERS ||--o{ CONVERSATIONS : "participant_a / participant_b"
    USERS ||--o{ FRIENDSHIPS : "friend_a / friend_b"
    USERS ||--o{ DIRECT_MESSAGES : "sender / receiver"

    USERS {
        int id PK "Khóa chính tự tăng"
        string email UK "Email thật (@sis.hust.edu.vn)"
        char(64) email_hash UK "Băm SHA-256 chống lộ danh tính"
        string password_hash "Mật khẩu băm PBKDF2/Argon2"
        string nickname "Biệt danh hiển thị ẩn danh"
        string avatar "Biểu tượng Emoji avatar"
        int trust_score "Điểm tin cậy (Mặc định: 100)"
        enum status "ACTIVE | BANNED"
        enum role "USER | ADMIN"
        datetime created_at "Thời điểm tạo tài khoản"
        datetime last_login_at "Thời điểm đăng nhập gần nhất"
    }

    PROFILES {
        int user_id PK, FK "Khóa chính & Khóa ngoại Users"
        string gender "Giới tính: male | female"
        string faculty_code "Mã Viện/Trường (SOICT, SME, ...)"
        string major_code "Mã ngành chuẩn HUST (IT1, EE2, ...)"
        int cohort "Khóa sinh viên (63 đến 71)"
        datetime updated_at "Thời điểm cập nhật"
    }

    CONVERSATIONS {
        int id PK "Mã phòng chat ẩn danh (Room ID)"
        int user_a FK "Người tham gia A (user_a <> user_b)"
        int user_b FK "Người tham gia B"
        enum type "HUMAN | BOT"
        float score "Điểm tương đồng (nếu có)"
        datetime started_at "Thời điểm tạo phòng"
        datetime ended_at "Thời điểm kết thúc cuộc trò chuyện"
    }

    FRIENDSHIPS {
        int id PK "Khóa chính"
        int user_a FK "User ID nhỏ hơn"
        int user_b FK "User ID lớn hơn (Unique user_a, user_b)"
        string status "accepted | pending | declined"
        datetime created_at "Thời điểm gửi/chấp nhận"
        datetime updated_at "Thời điểm cập nhật trạng thái"
    }

    DIRECT_MESSAGES {
        int id PK "Mã tin nhắn"
        int sender_id FK "Người gửi"
        int receiver_id FK "Người nhận"
        text content "Nội dung tin nhắn (tối đa 1000 ký tự)"
        boolean is_read "Trạng thái đã đọc"
        datetime created_at "Thời điểm gửi tin"
    }
```

---

## 3. LUỒNG 1: XÁC THỰC & QUẢN LÝ TÀI KHOẢN

### 3.1. Luồng Đăng ký Tài khoản (Registration with OTP)
1. **Kiểm tra đầu vào:** Email phải đúng định dạng sinh viên Đại học Bách Khoa Hà Nội (`@sis.hust.edu.vn`).
2. **Kiểm tra trùng lặp & Cooldown:** Backend kiểm tra email hoặc băm email `email_hash` trong DB. Đồng thời kiểm tra Cooldown (60 giây) qua `store_service.is_in_cooldown`.
3. **Sinh & Lưu trữ OTP:** Sinh mã OTP 6 số ngẫu nhiên qua module `secrets`, băm HMAC-SHA256 lưu vào Redis/Store với TTL 300 giây (5 phút), giới hạn tối đa 5 lần thử sai.
4. **Gửi Mail:** Gửi qua giao thức SMTP đến hòm thư sinh viên (trong môi trường dev sử dụng Mailpit hoặc in log).
5. **Xác thực mã & Khởi tạo tài khoản:** Người dùng nhập OTP + Mật khẩu mới (tối thiểu 6 ký tự) + Nickname + Avatar tùy chọn. Backend kiểm tra OTP, băm mật khẩu, tạo bản ghi `User`, cấp phát JWT token được đóng gói trong HttpOnly Cookie (`access_token`).

```mermaid
sequenceDiagram
    autonumber
    actor User as Sinh viên Bách Khoa
    participant UI as Giao diện Login/Register
    participant AuthAPI as API (/api/auth)
    participant Store as StoreService (Redis/Memory)
    participant Mail as Dịch vụ Mail (SMTP/Mailpit)
    participant DB as Cơ sở dữ liệu MySQL

    User->>UI: Nhập email sinh viên (@sis.hust.edu.vn)
    UI->>AuthAPI: POST /auth/request-register-otp { email }
    AuthAPI->>AuthAPI: Chuẩn hóa & kiểm tra đuôi @sis.hust.edu.vn
    AuthAPI->>DB: Kiểm tra tài khoản đã tồn tại chưa
    DB-->>AuthAPI: Chưa tồn tại
    AuthAPI->>Store: Kiểm tra cooldown 60s
    Store-->>AuthAPI: OK (Không bị giới hạn)
    AuthAPI->>AuthAPI: Sinh mã OTP 6 chữ số ngẫu nhiên
    AuthAPI->>Store: Lưu OTP HMAC (TTL 300s, max_attempts=5) & Cooldown 60s
    AuthAPI->>Mail: Gửi email chứa mã OTP đến sinh viên
    AuthAPI-->>UI: 200 OK (Mã xác thực đã gửi, cooldown 60s)
    UI->>User: Hiển thị form nhập OTP & Mật khẩu

    User->>UI: Nhập OTP + Mật khẩu + Nickname + Avatar
    UI->>AuthAPI: POST /auth/register { email, otp, password, nickname, avatar }
    AuthAPI->>Store: Kiểm tra tính hợp lệ của mã OTP
    alt OTP sai hoặc quá 5 lần
        Store-->>AuthAPI: Không hợp lệ
        AuthAPI-->>UI: 400 Bad Request (Mã xác thực không hợp lệ/hết hạn)
    else OTP chính xác
        Store-->>AuthAPI: Xác thực thành công (Xóa OTP)
        AuthAPI->>AuthAPI: Băm mật khẩu (Hash password)
        AuthAPI->>DB: Thêm bản ghi mới vào bảng `users`
        DB-->>AuthAPI: Lưu thành công (user_id)
        AuthAPI->>AuthAPI: Tạo JWT Access Token
        AuthAPI-->>UI: 200 OK (Set-Cookie: access_token HttpOnly) + has_profile=False
        UI->>User: Đăng nhập thành công, chuyển hướng sang /onboarding
    end
```

---

### 3.2. Luồng Đăng nhập (Password Login)
Người dùng nhập email sinh viên và mật khẩu. Hệ thống kiểm tra mật khẩu đã băm, kiểm tra trạng thái tài khoản không bị khóa (`status != BANNED`), cập nhật `last_login_at` và trả về JWT Cookie. Nếu người dùng chưa hoàn thành hồ sơ (`has_profile == false`), hệ thống điều hướng vào `/onboarding`. Nếu đã hoàn thành hồ sơ, hệ thống đưa vào `/matching`.

```mermaid
sequenceDiagram
    autonumber
    actor User as Sinh viên
    participant UI as Giao diện Login
    participant AuthAPI as API /auth/login
    participant DB as Cơ sở dữ liệu MySQL

    User->>UI: Nhập Email & Mật khẩu
    UI->>AuthAPI: POST /auth/login { email, password }
    AuthAPI->>DB: Truy vấn User theo email_hash kèm thông tin Profile
    DB-->>AuthAPI: Thông tin User
    alt Không tìm thấy tài khoản hoặc mật khẩu sai
        AuthAPI-->>UI: 401 Unauthorized (Sai email hoặc mật khẩu)
    else Tài khoản bị khóa (BANNED)
        AuthAPI-->>UI: 403 Forbidden (Tài khoản đã bị đình chỉ)
    else Đăng nhập thành công
        AuthAPI->>DB: Cập nhật last_login_at = now()
        AuthAPI->>AuthAPI: Sinh JWT Access Token
        AuthAPI-->>UI: 200 OK (Set-Cookie: access_token, user_info, has_profile)
        alt has_profile == true
            UI->>User: Điều hướng vào trang Ghép cặp (/matching)
        else has_profile == false
            UI->>User: Điều hướng vào trang Tạo hồ sơ (/onboarding)
        end
    end
```

---

### 3.3. Luồng Quên Mật khẩu (Password Reset Flow)
Bao gồm 2 bước:
1. `POST /api/auth/request-reset-otp`: Kiểm tra email tồn tại trong hệ thống -> Lưu mã OTP và gửi về email.
2. `POST /api/auth/reset-password`: Xác minh mã OTP hợp lệ -> Cập nhật mật khẩu mới vào cơ sở dữ liệu -> Tự động đăng nhập luôn (cấp JWT cookie).

```mermaid
flowchart TD
    Start([Bắt đầu Quên Mật Khẩu]) --> InputEmail["Nhập Email sinh viên"]
    InputEmail --> CallReq["POST /auth/request-reset-otp"]
    CallReq --> CheckUser{"Tài khoản có tồn tại?"}
    CheckUser -- "Không" --> EnumSafe["Chống enumeration: Trả 200 'Nếu địa chỉ hợp lệ, mã sẽ được gửi'"]
    CheckUser -- "Có" --> CheckCD{"Đang trong Cooldown 60s?"}
    CheckCD -- "Có" --> ErrCD["Báo lỗi: 429 Vui lòng chờ 60 giây"]
    CheckCD -- "Không" --> GenOTP["Tạo OTP mới, lưu Redis TTL 300s & gửi email"]
    GenOTP --> ShowForm["Hiển thị form nhập OTP và Mật khẩu mới"]
    ShowForm --> SubmitReset["POST /auth/reset-password { email, otp, new_password }"]
    SubmitReset --> VerifyOTP{"OTP hợp lệ & Chưa quá 5 lần?"}
    VerifyOTP -- "Sai / Hết hạn" --> ErrOTP["Báo lỗi: 400 Mã không hợp lệ"]
    VerifyOTP -- "Hợp lệ" --> UpdatePwd["Cập nhật password_hash mới trong DB"]
    UpdatePwd --> GenJWT["Cấp JWT Access Token mới trong Cookie"]
    GenJWT --> Redirect["Đăng nhập thành công -> Điều hướng /matching"]
    Redirect --> End([Hoàn tất])
```

---

### 3.4. Luồng Khôi phục Phiên làm việc & Đăng xuất
- Khi người dùng truy cập bất kỳ trang nào (F5 trình duyệt), `App.jsx` gọi `GET /api/auth/me`.
- Backend kiểm tra cookie `access_token`. Nếu hợp lệ, trả về user info và profile; nếu không, tự động làm sạch store Zustand.
- Khi người dùng bấm **Sign Out**, gửi `POST /api/auth/logout`. Backend xóa cookie và Client xóa bộ nhớ, chuyển về `/login`.

---

## 4. LUỒNG 2: KHAI BÁO & QUẢN LÝ HỒ SƠ (ONBOARDING)

Mỗi sinh viên bắt buộc phải hoàn thành hồ sơ trước khi có thể tham gia tìm bạn chat.

```mermaid
sequenceDiagram
    autonumber
    actor User as Sinh viên
    participant UI as Giao diện Onboarding
    participant ProfAPI as API /api/profile
    participant CatService as Catalog Service
    participant DB as Cơ sở dữ liệu MySQL

    User->>UI: Truy cập trang /onboarding
    UI->>ProfAPI: GET /profile/catalog
    ProfAPI->>CatService: Lấy danh mục 68 ngành học chuẩn HUST
    CatService-->>ProfAPI: Danh sách 68 ngành Tiếng Anh (Mã ngành, Tên ngành, Mã Đơn vị, Tên Trường/Khoa)
    ProfAPI-->>UI: 200 OK (JSON catalog)
    UI->>ProfAPI: GET /profile/me
    ProfAPI->>DB: Lấy hồ sơ hiện tại (nếu đã tạo)
    DB-->>ProfAPI: Trả về Profile hoặc 404
    ProfAPI-->>UI: Hiển thị dữ liệu hồ sơ lên Form

    User->>UI: Chọn Giới tính, Chọn Trường/Viện/Khoa -> Ngành học (Cascading Select), Chọn Khóa (K63-K71), Đổi Nickname/Avatar
    UI->>ProfAPI: POST /profile { gender, major_code, cohort, nickname, avatar }
    ProfAPI->>ProfAPI: Kiểm tra gender (male/female)
    ProfAPI->>CatService: Kiểm tra major_code có thuộc 68 ngành HUST không
    alt Mã ngành không hợp lệ
        ProfAPI-->>UI: 400 Bad Request (Mã ngành không tồn tại trong danh mục)
    else Hợp lệ
        ProfAPI->>ProfAPI: Tự động tra cứu faculty_code từ major_code
        ProfAPI->>ProfAPI: Kiểm tra ràng buộc khóa (63 <= cohort <= 71)
        ProfAPI->>DB: Lưu/Cập nhật bảng `profiles` & bảng `users`
        DB-->>ProfAPI: Thành công
        ProfAPI-->>UI: 200 OK (Cập nhật hồ sơ thành công)
        UI->>User: Thông báo thành công, chuyển hướng vào trang Ghép đôi (/matching)
    end
```

---

## 5. LUỒNG 3: GHÉP CẶP ẨN DANH THEO 3 BỘ LỌC CỨNG HAI CHIỀU

Đây là hạt nhân nghiệp vụ của ứng dụng, đảm bảo tính thỏa mãn song phương (Bipartite Mutual Satisfaction).

### 5.1. Quy tắc 3 Bộ lọc Cứng Hai Chiều (`is_mutual_match`)

Một cặp ghép giữa Sinh viên A và Sinh viên B chỉ được coi là thành công khi và chỉ khi:
$$\text{is\_mutual\_match}(A, B) = \text{Accepts}(A \to B) \land \text{Accepts}(B \to A)$$

| Tiêu chí | Lựa chọn lọc của User A | Điều kiện để chấp nhận User B |
|---|---|---|
| **Giới tính** (`target_gender`) | `any` (Bất kì)<br>`male` (Nam)<br>`female` (Nữ) | Không kiểm tra<br>`B.gender == 'male'`<br>`B.gender == 'female'` |
| **Ngành / Viện** (`target_major_faculty`) | `any` (Bất kì)<br>`same_major` (Cùng ngành)<br>`same_faculty` (Cùng trường/viện khác ngành)<br>`different_faculty` (Khác trường/viện) | Không kiểm tra<br>`A.major_code == B.major_code`<br>`A.faculty_code == B.faculty_code` VÀ `A.major_code != B.major_code`<br>`A.faculty_code != B.faculty_code` |
| **Khóa học** (`target_cohort`) | `any` (Bất kì)<br>`same_cohort` (Cùng khóa)<br>`senior` (Khóa trên)<br>`junior` (Khóa dưới) | Không kiểm tra<br>`A.cohort == B.cohort`<br>`B.cohort < A.cohort` (Ví dụ A là K68 thì B là K67, K66...)<br>`B.cohort > A.cohort` (Ví dụ A là K68 thì B là K69, K70...) |

### 5.2. Biểu đồ Luồng Tìm kiếm & Ghép cặp

```mermaid
flowchart TD
    Start([User ấn 'Bắt đầu ghép']) --> CheckProf{"Đã hoàn thiện Profile chưa?"}
    CheckProf -- "Chưa" --> RetErr["400: Yêu cầu hoàn thành Onboarding"]
    CheckProf -- "Rồi" --> GenAtt["Tạo attempt_id mới & dọn kết quả cũ"]
    GenAtt --> ScanQueue["Quét các ứng viên trong hàng đợi (StoreService)"]
    ScanQueue --> FilterStale["Loại bỏ ứng viên timeout >= 60 giây"]
    FilterStale --> LoopCand{"Duyệt từng ứng viên trong hàng đợi"}

    LoopCand -- "Thử ứng viên B" --> EvalMutual{"is_mutual_match(A, B) == True?\n(Thỏa mãn cả 3 bộ lọc 2 chiều)"}
    EvalMutual -- "Không khớp" --> LoopCand

    EvalMutual -- "Khớp cả 2 chiều!" --> Reserve["Redis Lua Script: RESERVE_CANDIDATE_LUA\n(Khóa nguyên tử tránh ghép trùng)"]
    Reserve -- "Thất bại (B vừa bị ghép bởi lượt khác)" --> LoopCand
    Reserve -- "Thành công" --> CreateRoom["Tạo Conversation mới trong MySQL (user_a, user_b, type=HUMAN)"]
    CreateRoom --> SaveResult["Lưu match_result cho cả A và B trong Store (TTL 300s)"]
    SaveResult --> RetMatched["API trả về: status='matched', room_id, attempt_id"]
    RetMatched --> EnterChat["Frontend tự động điều hướng vào /chat/{room_id}"]

    LoopCand -- "Hết danh sách mà không có ai khớp" --> AddToQ["Đưa User A vào hàng đợi (Queue TTL 65s)"]
    AddToQ --> RetWaiting["API trả về: status='waiting', attempt_id"]
    RetWaiting --> StartPolling["Frontend bật đếm giờ & Polling GET /match/status mỗi 2s"]

    StartPolling --> PollCheck{"Poll kiểm tra kết quả theo attempt_id"}
    PollCheck -- "status == 'matched'" --> ReceiveMatch["Nhận room_id -> Điều hướng /chat/{room_id}"]
    PollCheck -- "User ấn 'Hủy tìm kiếm'" --> LeaveAPI["POST /match/leave -> Hủy lượt tìm, reset về 'idle'"]
    PollCheck -- "status == 'not_found' (sau 60s)" --> TimeoutMatch["UI dừng polling -> Hiện màn hình Timeout\n(Lựa chọn 'Thử lại ngay' hoặc 'Đổi tiêu chí')"]
```

---

## 6. LUỒNG 4: PHÒNG CHAT REALTIME ẨN DANH & TIẾT LỘ DANH TÍNH

### 6.1. Chi tiết Bắt tay WebSocket & Vòng đời Phòng Chat
1. **Bắt tay & Xác thực:** Client mở kết nối `wss://<host>/ws/{room_id}` kèm cookie JWT.
2. **Kiểm tra thành viên:** Backend kiểm tra `room_id` có tồn tại, `user_id` có phải `user_a` hoặc `user_b` không, và phòng chưa bị kết thúc (`ended_at IS NULL`).
3. **Đăng ký lắng nghe:** Client được gán một hàng đợi nhận tin riêng trong `StoreService._rooms[room_id]`.
4. **Broadcast tham gia:** Server gửi tin nhắn `room_info` tới client mới và broadcast `user joined` tới toàn phòng.

```mermaid
sequenceDiagram
    autonumber
    actor UserA as Sinh viên A
    actor UserB as Sinh viên B
    participant WS as WebSocket Gateway (/ws/{room_id})
    participant Store as StoreService (Pub/Sub)
    participant DB as Cơ sở dữ liệu MySQL

    Note over UserA,UserB: Cả 2 đã nhận được room_id từ luồng Matching
    UserA->>WS: Kết nối WebSocket /ws/{room_id} (Kèm Token)
    WS->>WS: Giải mã JWT, lấy user_id
    WS->>DB: Kiểm tra phòng chat & quyền tham gia của UserA
    DB-->>WS: Hợp lệ (Room mở, UserA thuộc phòng)
    WS->>WS: websocket.accept()
    WS-->>UserA: Gửi gói tin khởi tạo `room_info` (Đối phương ẩn danh)
    WS->>Store: Đăng ký hàng đợi nhận tin cho UserA
    WS->>Store: Broadcast "User A joined the chat"
    Store-->>UserB: Nhận thông báo A đã vào phòng

    Note over UserA,UserB: Giai đoạn Chat Ẩn danh (Realtime Messaging)
    UserA->>WS: Gửi tin nhắn text (Ví dụ: "Chào bạn, mình K68 SOICT")
    WS->>WS: Kiểm tra độ dài (<= 1000 ký tự)
    WS->>Store: Broadcast tin nhắn tới tất cả hàng đợi trong phòng
    Store-->>UserA: Nhận tin nhắn của chính mình (Render bong bóng xanh)
    Store-->>UserB: Nhận tin nhắn của UserA (Render bong bóng xám)

    Note over UserA,UserB: Giai đoạn Tiết lộ Danh tính & Kết bạn (Identity Reveal)
    UserA->>WS: Gửi sự kiện JSON: { type: "friend_request" }
    WS->>Store: Broadcast sự kiện "friend_request_received"
    Store-->>UserB: Hiển thị Popup: "User A muốn kết bạn & tiết lộ danh tính"

    alt User B từ chối
        UserB->>WS: Gửi { type: "friend_response", accepted: false }
        WS->>Store: Broadcast "friend_declined"
        Store-->>UserA: Thông báo: Lời mời kết bạn đã bị từ chối
    else User B đồng ý
        UserB->>WS: Gửi { type: "friend_response", accepted: true }
        WS->>DB: Ghi bản ghi vào bảng `friendships` (status="accepted")
        WS->>DB: Lấy email chính thức (@sis.hust.edu.vn) của cả 2 User
        DB-->>WS: Trả về email thật
        WS->>Store: Broadcast sự kiện "friend_accepted" kèm Email thật của cả 2
        Store-->>UserA: Hiển thị: Đã là bạn bè! Email đối phương: b.nguyen@sis.hust.edu.vn
        Store-->>UserB: Hiển thị: Đã là bạn bè! Email đối phương: a.tran@sis.hust.edu.vn
        Note over UserA,UserB: Hai người giờ đây có thể chat vĩnh viễn trong mục Messages
    end

    Note over UserA,UserB: Kết thúc cuộc trò chuyện
    UserA->>WS: Bấm nút "Kết thúc chat" -> POST /conversations/{room_id}/end
    WS->>DB: Cập nhật ended_at = now()
    WS->>Store: Broadcast sự kiện { type: "ended" }
    Store-->>UserA: Vô hiệu hóa khung chat
    Store-->>UserB: Vô hiệu hóa khung chat
    UserA->>WS: Đóng WebSocket
    WS->>Store: Hủy hàng đợi lắng nghe & Broadcast "User A left the chat"
```

---

## 7. LUỒNG 5: NHẮN TIN TRỰC TIẾP GIỮA BẠN BÈ (DIRECT MESSAGES)

Sau khi hai sinh viên đã đồng ý kết bạn ở phòng chat ẩn danh, mối quan hệ bạn bè được lưu vĩnh viễn trong bảng `friendships`. Họ có thể trò chuyện bất cứ lúc nào qua giao diện **Messages**.

```mermaid
sequenceDiagram
    autonumber
    actor UserA as Sinh viên A
    actor UserB as Sinh viên B (Bạn bè)
    participant UI as Giao diện Messages (/messages)
    participant DM_API as API Direct Messages
    participant DM_WS as WebSocket (/ws/direct/{friend_id})
    participant DB as Cơ sở dữ liệu MySQL

    UserA->>UI: Truy cập tab Messages
    UI->>DM_API: GET /friends
    DM_API->>DB: Lấy danh sách bạn bè (status='accepted') kèm tin nhắn gần nhất
    DB-->>DM_API: Danh sách bạn bè
    DM_API-->>UI: Hiển thị danh sách bên cột trái

    UserA->>UI: Chọn trò chuyện với Bạn B
    UI->>DM_API: GET /messages/{friend_id}
    DM_API->>DB: Kiểm tra quan hệ bạn bè & lấy lịch sử tin nhắn
    DB-->>DM_API: Danh sách các tin nhắn đã gửi trước đó
    DM_API-->>UI: Hiển thị lịch sử tin nhắn lên màn hình

    UI->>DM_WS: Kết nối WebSocket /ws/direct/{friend_id}
    DM_WS->>DB: Xác thực JWT & Kiểm tra điều kiện bạn bè
    DM_WS-->>UI: Chấp nhận kết nối (Gia nhập phòng dm_A_B)

    UserA->>DM_WS: Gửi tin nhắn qua WebSocket (Nội dung: "Mai hẹn nhau ở thư viện Tạ Quang Bửu nhé")
    DM_WS->>DB: INSERT tin nhắn mới vào bảng `direct_messages`
    DB-->>DM_WS: Lưu thành công
    DM_WS->>DM_WS: Broadcast tin nhắn đến kênh `dm_A_B`
    DM_WS-->>UserA: Cập nhật tin nhắn trên màn hình User A
    DM_WS-->>UserB: Tin nhắn hiển thị tức thì trên màn hình User B (Realtime)
    DM_WS-->>UI: Cập nhật `last_message` ở danh sách bạn bè cột bên trái
```

---

## 8. BẢNG TRA CỨU API ENDPOINTS & WEBSOCKET ROUTES

Toàn bộ các tuyến giao tiếp của hệ thống đều được bảo vệ và chuẩn hóa:

| Phương thức | Đường dẫn Route | Mục đích nghiệp vụ | Quyền truy cập |
|---|---|---|---|
| **GET** | `/health` | Kiểm tra tình trạng máy chủ (Healthcheck) | Công khai |
| **POST** | `/api/auth/request-register-otp` | Yêu cầu mã OTP đăng ký (Kiểm tra `@sis.hust.edu.vn`) | Công khai |
| **POST** | `/api/auth/register` | Xác thực OTP & Tạo tài khoản mới | Công khai |
| **POST** | `/api/auth/login` | Đăng nhập bằng Email & Mật khẩu | Công khai |
| **POST** | `/api/auth/request-reset-otp` | Yêu cầu mã OTP đặt lại mật khẩu | Công khai |
| **POST** | `/api/auth/reset-password` | Xác thực OTP & Đổi mật khẩu mới | Công khai |
| **GET** | `/api/auth/me` | Lấy thông tin tài khoản hiện tại & trạng thái hồ sơ | Đã đăng nhập (JWT) |
| **POST** | `/api/auth/logout` | Đăng xuất & Xóa cookie `access_token` | Đã đăng nhập (JWT) |
| **GET** | `/api/profile/catalog` | Lấy danh mục 68 ngành học & 10 Viện/Trường HUST | Công khai |
| **GET** | `/api/profile/me` | Lấy chi tiết hồ sơ cá nhân của người dùng | Đã đăng nhập (JWT) |
| **POST** | `/api/profile` | Tạo mới hoặc cập nhật hồ sơ sinh viên | Đã đăng nhập (JWT) |
| **POST** | `/api/match/join` | Tham gia hàng đợi ghép đôi với 3 bộ lọc cứng | Đã có hồ sơ |
| **GET** | `/api/match/status` | Polling kiểm tra trạng thái ghép cặp | Đã có hồ sơ |
| **POST** | `/api/match/leave` | Hủy tìm kiếm và rời khỏi hàng đợi | Đã đăng nhập (JWT) |
| **WS** | `/ws/{room_id}` | WebSocket chat ẩn danh 1-1 & Tiết lộ danh tính | Thành viên phòng |
| **POST** | `/api/conversations/{room_id}/end` | Kết thúc phòng trò chuyện ẩn danh | Thành viên phòng |
| **GET** | `/api/friends` | Lấy danh sách bạn bè đã kết bạn | Đã đăng nhập (JWT) |
| **GET** | `/api/messages/{friend_id}` | Lấy lịch sử tin nhắn trực tiếp với bạn bè | Là bạn bè |
| **POST** | `/api/messages/{friend_id}` | Gửi tin nhắn trực tiếp qua HTTP REST | Là bạn bè |
| **WS** | `/ws/direct/{friend_id}` | WebSocket chat trực tiếp realtime giữa bạn bè | Là bạn bè |

---

## 9. CƠ CHẾ BẢO MẬT, KHẢ NĂNG CHỊU LỖI & FALLBACK TỰ ĐỘNG

```mermaid
flowchart LR
    subgraph SecurityMechanisms["Cơ chế Bảo mật Chặt chẽ"]
        S1["Chỉ nhận email @sis.hust.edu.vn"]
        S2["Băm email SHA-256 (email_hash)\nChống lộ danh tính người dùng"]
        S3["OTP HMAC TTL 300s, Cooldown 60s\nKhóa sau 5 lần nhập sai"]
        S4["JWT Cookie HttpOnly, Secure, SameSite\nChống XSS và Token Theft"]
        S5["Giới hạn độ dài tin nhắn (1000 ký tự)\nChống tràn bộ nhớ & spam"]
    end

    subgraph ResilienceMechanisms["Cơ chế Chịu lỗi Kép (Dual-Store Resilience)"]
        R1["Kết nối Redis khả dụng?"]
        R2["Sử dụng Redis Distributed Cache\n(Pub/Sub, Key-Value TTL, Set)"]
        R3["Tự động chuyển sang In-Memory Store\n(Asyncio Queue, Memory KV TTL)"]
        R1 -- "Có (Redis Live)" --> R2
        R1 -- "Mất kết nối / Dev Offline" --> R3
    end
```

### Các nguyên tắc bảo mật cốt lõi:
1. **Quyền riêng tư tuyệt đối khi Chat Ẩn danh:**
   - Trong quá trình ghép cặp và chat tại phòng `/ws/{room_id}`, danh tính thật (Email, Họ tên thật) hoàn toàn được giấu kín. Hai bên chỉ nhìn thấy Nickname ảo, Avatar emoji, Giới tính, Khóa học và Ngành học.
   - Chỉ khi **cả hai bên cùng đồng ý** trong sự kiện "Reveal Identity / Friend Request", email sinh viên chính thức mới được tiết lộ.
2. **Bảo vệ chống Brute-Force & Lạm dụng:**
   - Rate limit gửi OTP: Cooldown 60 giây giữa mỗi lần bấm.
   - Thử sai tối đa 5 lần: Sau 5 lần nhập sai OTP, key OTP bị hủy ngay lập tức trên hệ thống lưu trữ.
3. **Kiểm tra phân quyền chặt chẽ ở Backend (Authorization Gates):**
   - Mọi WebSocket connection đều được giải mã JWT và truy vấn DB xác thực membership trước khi hàm `accept()` được gọi. Người lạ không thể nghe trộm hoặc gửi tin vào bất kỳ phòng nào.
4. **Không phụ thuộc cứng vào Redis:**
   - Hệ thống được trang bị lớp trừu tượng `StoreService` có khả năng tự động fallback về In-Memory an toàn nếu Redis gặp sự cố, đảm bảo dịch vụ không bị gián đoạn.

---
*Tài liệu được tổng hợp và phân tích trực tiếp từ mã nguồn thực tế của dự án HUST Chatbox.*

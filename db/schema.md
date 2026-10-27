# Database Schema Design

> **Core MVP Tables**: `users`, `profiles`, `conversations`, `friendships`, and `direct_messages`.
> Profile specifications and 3-criteria mutual matching filters are documented in [docs/QUESTIONNAIRE.md](../docs/QUESTIONNAIRE.md).

## Target Relational Model

```mermaid
erDiagram
    USERS ||--o| PROFILES : "has"
    USERS ||--o{ CONVERSATIONS : "participant_a"
    USERS ||--o{ CONVERSATIONS : "participant_b"
    USERS ||--o{ FRIENDSHIPS : "friend_a"
    USERS ||--o{ FRIENDSHIPS : "friend_b"
    USERS ||--o{ DIRECT_MESSAGES : "sender"
    USERS ||--o{ DIRECT_MESSAGES : "receiver"
    FACULTIES ||--o{ MAJORS : "groups"
    FACULTIES ||--o{ PROFILES : "school"
    MAJORS o|--o{ PROFILES : "selected_major"

    USERS {
        int id PK
        varchar email UK "SIS student email"
        char email_hash UK
        varchar password_hash "PBKDF2-HMAC-SHA256"
        varchar anon_name "Nickname"
        varchar avatar "Emoji avatar"
        int trust_score
        enum status "active or banned"
        enum role
        datetime created_at
        datetime last_login_at
    }
    PROFILES {
        int user_id PK "also FK to USERS"
        string gender "nam or nu"
        string faculty_code FK
        string major_code FK
        int cohort "cohort K63-K71 (63..71)"
        datetime updated_at
    }
    CONVERSATIONS {
        int id PK
        int user_a FK
        int user_b FK
        enum type
        float score
        datetime started_at
        datetime ended_at
    }
    FRIENDSHIPS {
        int id PK
        int user_a FK
        int user_b FK
        string status "accepted or pending"
        datetime created_at
        datetime updated_at
    }
    DIRECT_MESSAGES {
        int id PK
        int sender_id FK
        int receiver_id FK
        text content
        boolean is_read
        datetime created_at
    }
```

## Active Tables

### `users`

| Column | Type | Constraints / Meaning |
|---|---|---|
| `id` | `INT` | Primary Key, Auto-increment |
| `email` | `VARCHAR(191)` | Unique, student email (`@sis.hust.edu.vn`) |
| `email_hash` | `CHAR(64)` | Required, unique HMAC-SHA256 of normalized email |
| `password_hash` | `VARCHAR(255)` | Salted PBKDF2-HMAC-SHA256 hash |
| `anon_name` | `VARCHAR(50)` | User-chosen nickname |
| `avatar` | `VARCHAR(20)` | User-chosen avatar emoji (default 🦉) |
| `trust_score` | `INT` | Default `100` |
| `status` | `ENUM` | `active`, `banned`; default `active` |
| `role` | `ENUM` | `user`, `admin`; default `user` |
| `created_at` | `DATETIME` | Account creation timestamp |
| `last_login_at` | `DATETIME NULL` | Most recent login |

### `profiles`

| Column | Type | Meaning |
|---|---|---|
| `user_id` | `INT PK/FK` | Primary Key, References `users.id` (CASCADE) |
| `gender` | `VARCHAR(10)` | Gender: `nam` (Male) or `nu` (Female) |
| `faculty_code` | `VARCHAR(20)` | HUST School/Faculty code |
| `major_code` | `VARCHAR(20)` | HUST Major code from 68 catalog |
| `cohort` | `INT` | Academic cohort between K63 and K71 (63..71) |
| `updated_at` | `DATETIME` | Last profile update timestamp |

### `friendships`

| Column | Type | Constraints / Meaning |
|---|---|---|
| `id` | `INT` | Primary Key, Auto-increment |
| `user_a`, `user_b` | `INT FK` | Users in friendship; unique pair constraint |
| `status` | `VARCHAR(20)` | `accepted`, `pending`, `declined` |
| `created_at` | `DATETIME` | Created timestamp |
| `updated_at` | `DATETIME` | Last updated timestamp |

### `direct_messages`

| Column | Type | Constraints / Meaning |
|---|---|---|
| `id` | `INT` | Primary Key, Auto-increment |
| `sender_id` | `INT FK` | User who sent the message |
| `receiver_id` | `INT FK` | User who received the message |
| `content` | `TEXT` | Message text content |
| `is_read` | `BOOLEAN` | Read status |
| `created_at` | `DATETIME` | Message send timestamp |

### `conversations`

| Column | Type | Constraints / Meaning |
|---|---|---|
| `id` | `INT` | Primary Key, Auto-increment |
| `user_a`, `user_b` | `INT FK` | Room participants; distinct users |
| `type` | `ENUM` | `human`, `bot`; default `human` |
| `score` | `FLOAT NULL` | Match score |
| `started_at` | `DATETIME` | Room start timestamp |
| `ended_at` | `DATETIME NULL` | Room termination timestamp |

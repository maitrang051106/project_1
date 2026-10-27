# Profile, Matching Filters & Friendship Contract

> Single Source of Truth (SSOT) for profile data, mutual matching filters, authentication, and the friend system.

- **Version:** `5` (Strict SIS Email, Password Auth, Custom Nickname/Avatar, Mutual Hard Filters, Two-Way Add Friend & Persistent DMs)
- **Academic Catalog:** [68 HUST Majors CSV](../db/seed/hust-68-nganh-2026.csv) across 10 Schools/Faculties [CSV Units](../db/seed/hust-schools-2026.csv).

---

## 1. Authentication & Identity

### Allowed Email Domain
- Strictly `@sis.hust.edu.vn` (all other domains including `@hust.edu.vn` are rejected).

### Flow
1. **Sign Up**: Email $\to$ 6-digit OTP verification $\to$ Password (min 6 characters) $\to$ Auto-login.
2. **Sign In**: Email + Password.
3. **Password Reset**: Email $\to$ OTP verification $\to$ New password.

### Identity & Presentation
- **Nickname (`anon_name`)**: User-defined custom alias (e.g. "Midnight Coder").
- **Avatar (`avatar`)**: User-selected emoji avatar (e.g. 🦉, 🐱, 🐸, 🐶, 🐵, 🐰, 🐻, 🐧, 🐹, 🦊, 🐼).
- **Navbar**: Displays chosen Avatar + Nickname + Sign Out button.

---

## 2. Onboarding Profile

Users must complete profile setup before joining the matching queue:

| Field | Key | Type | Valid Values / Constraints |
|---|---|---|---|
| **Gender** | `gender` | `VARCHAR(10)` | `"nam"` (Male), `"nu"` (Female) |
| **Major & Faculty** | `major_code`<br>`faculty_code` | `VARCHAR(20)`<br>`VARCHAR(20)` | `major_code`: Selected from the 68 official HUST majors.<br>`faculty_code`: Associated School/Institute. |
| **Cohort (Batch)** | `cohort` | `INT` | Integer from 63 to 71 representing student batch (K63 to K71). |

---

## 3. Mutual Matching Preferences (Two-Way Hard Filters)

When joining the queue, users specify 3 preferences:

### 1. Target Gender (`target_gender`)
* `"nam"`: Male only (`candidate.gender == "nam"`).
* `"nu"`: Female only (`candidate.gender == "nu"`).
* `"bat_ki"`: Any gender.

### 2. Target Major / School (`target_major_faculty`)
* `"cung_nganh"`: Same major (`candidate.major_code == my.major_code`).
* `"cung_truong_khac_nganh"`: Same school, different major.
* `"khac_truong"`: Different school.
* `"bat_ki"`: Any major or school.

### 3. Target Cohort (`target_cohort`)
* `"khoa_tren"`: Senior student (`candidate.cohort < my.cohort`).
* `"khoa_duoi"`: Junior student (`candidate.cohort > my.cohort`).
* `"cung_khoa"`: Same batch (`candidate.cohort == my.cohort`).
* `"bat_ki"`: Any batch.

### Mutual Condition
$$\text{IsMatch}(A, B) \iff \text{Satisfies}(A \to B) \land \text{Satisfies}(B \to A) \land (A \neq B)$$

---

## 4. Anonymous Chat & Two-Way "Add Friend"

- In Anonymous Chat: Real email is hidden. Opponent's Avatar and Nickname are displayed.
- **Add Friend Button**:
  1. User A clicks `Add Friend` $\to$ sends `friend_request` event over WebSocket.
  2. User B sees a prompt: `"User A wants to add friend and reveal real emails. [Accept] [Decline]"`.
  3. When User B clicks `Accept`:
     - System creates/updates `Friendship` with `status = "accepted"`.
     - System broadcasts `friend_accepted` event revealing both users' verified `@sis.hust.edu.vn` emails.
     - The conversation is added to both users' **Messages** tab for persistent direct messaging.

---

## 5. Persistent Direct Messaging ("Messages" Tab)

- Standard 2-column layout:
  - **Left column**: List of accepted friends (Avatar, Nickname, Verified Email, preview of last message, timestamp).
  - **Right column**: Direct conversation pane with message history (`direct_messages` table) and real-time updates via WebSocket (`/ws/direct/{friend_id}`).

# Quy ước Hồ sơ và Bộ lọc Ghép cặp (Profile & Hard Filters Contract)

> Nguồn sự thật (Single Source of Truth) cho thông tin hồ sơ và quy tắc matching. Mọi model AI, backend và frontend bắt buộc tuân thủ đúng contract này.

- **Phiên bản:** `4` (Tối giản: 3 trường hồ sơ + 3 bộ lọc cứng hai chiều)
- **Catalog đào tạo:** [CSV 68 ngành](../db/seed/hust-68-nganh-2026.csv) thuộc 10 Trường/Viện/Khoa HUST [CSV đơn vị](../db/seed/hust-schools-2026.csv).

---

## 1. Hồ sơ bắt buộc khi đăng nhập (Onboarding Profile)

Sau khi xác thực email OTP (`@hust.edu.vn` hoặc `@sis.hust.edu.vn`), người dùng bắt buộc phải khai báo 3 thông tin để kích hoạt tài khoản:

| Trường | Field | Kiểu dữ liệu | Giá trị hợp lệ / Ràng buộc |
|---|---|---|---|
| **Giới tính** | `gender` | `VARCHAR(10)` | `"nam"`, `"nu"` |
| **Ngành học & Đơn vị** | `major_code`<br>`faculty_code` | `VARCHAR(20)`<br>`VARCHAR(20)` | `major_code`: Chọn từ 68 mã ngành HUST.<br>`faculty_code`: Mã Trường/Viện quản lý ngành tương ứng (tự động suy ra từ ngành). |
| **Khóa sinh viên** | `cohort` | `INT` | Số nguyên từ 63 đến 71 biểu thị khóa sinh viên (K63 đến K71). |

*Lưu ý cho AI:* Không còn câu hỏi tính cách, mục tiêu chat hay vector embedding 5 chiều.

---

## 2. Ba (03) Tiêu chí Ghép cặp (Matching Preferences)

Khi người dùng tham gia hàng đợi tìm bạn chat, họ chọn 3 tiêu chí mong muốn về đối phương:

### 1. Giới tính đối phương (`target_gender`)
* `"nam"`: Chỉ ghép với đối phương là Nam (`candidate.gender == "nam"`).
* `"nu"`: Chỉ ghép với đối phương là Nữ (`candidate.gender == "nu"`).
* `"bat_ki"`: Chấp nhận mọi giới tính.

### 2. Ngành / Trường đối phương (`target_major_faculty`)
* `"cung_nganh"`: Cùng mã ngành (`candidate.major_code == my.major_code`).
* `"cung_truong_khac_nganh"`: Cùng trường/viện nhưng khác ngành (`candidate.faculty_code == my.faculty_code` và `candidate.major_code != my.major_code`).
* `"khac_truong"`: Khác trường/viện (`candidate.faculty_code != my.faculty_code`).
* `"bat_ki"`: Bất kỳ ngành/trường nào.

### 3. Khóa học đối phương (`target_cohort`)
* `"khoa_tren"`: Đối phương nhập học trước mình (`candidate.cohort < my.cohort`).
* `"khoa_duoi"`: Đối phương nhập học sau mình (`candidate.cohort > my.cohort`).
* `"cung_khoa"`: Đối phương cùng khóa với mình (`candidate.cohort == my.cohort`).
* `"bat_ki"`: Bất kỳ khóa nào.

---

## 3. Nguyên tắc Ghép cặp Hai Chiều (Mutual Hard Filters)

Hai người dùng A và B chỉ được ghép vào cùng một cuộc trò chuyện khi và chỉ khi **cả hai cùng thỏa mãn tiêu chí của nhau**:

$$\text{IsMatch}(A, B) \iff \text{Satisfies}(A \to B) \land \text{Satisfies}(B \to A) \land (A \neq B) \land \text{NotBlocked}(A, B)$$

### Ma trận kiểm tra logic hai chiều:
1. **Giới tính:**
   * A chấp nhận giới tính của B VÀ B chấp nhận giới tính của A.
2. **Ngành/Trường:**
   * Mối quan hệ ngành/trường giữa A và B phải thỏa mãn lựa chọn của A VÀ lựa chọn của B.
3. **Khóa học:**
   * Quan hệ khóa giữa A và B phải thỏa mãn lựa chọn của A VÀ lựa chọn của B.
   * *Ví dụ:* Nếu A chọn `khoa_tren` mà B cũng chọn `khoa_tren` $\to$ **Không bao giờ match** (xung đột logic).
   * *Ví dụ hợp lệ:* A chọn `khoa_tren` (muốn gặp khóa trên), B là khóa trên và B chọn `khoa_duoi` (hoặc `bat_ki`) $\to$ **Match**.

---

## 4. Quản lý Hàng đợi & Phòng chat
* Mỗi tài khoản chỉ có tối đa **1 phòng chat hoạt động** tại một thời điểm.
* Chỉ người tham gia mới có quyền kết thúc phòng chat (`ended_at`). Sau khi kết thúc, phòng chat bị đóng và có thể bắt đầu ghép phòng mới.
* Quota lượt chat tính theo ngày Việt Nam (`Asia/Ho_Chi_Minh`) dựa vào `started_at`:
  * `trust_score >= 90`: Không giới hạn lượt chat.
  * `70 - 89`: Tối đa 5 lượt/ngày.
  * `50 - 69`: Tối đa 3 lượt/ngày.
  * `1 - 49`: Tối đa 1 lượt/ngày.
  * `trust_score <= 0`: Bị khóa tài khoản (`banned`).

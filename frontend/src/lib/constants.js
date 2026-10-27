// frontend/src/lib/constants.js

// Allowed email domain for HUST students
export const STUDENT_EMAIL_DOMAIN = "@sis.hust.edu.vn";

// Animal head and owl avatar options
export const AVATAR_OPTIONS = [
  "🦉", "🐱", "🐸", "🐶", "🐵", "🐰", "🐻", "🐧", "🐹", "🦊", "🐼"
];

export const DEFAULT_AVATAR = "🦉";

// Valid student cohorts (K63 - K71)
export const COHORTS = [63, 64, 65, 66, 67, 68, 69, 70, 71];
export const DEFAULT_COHORT = 71;

// Gender choices
export const GENDER_OPTIONS = [
  { value: "nam", label: "Male", icon: "👦" },
  { value: "nu", label: "Female", icon: "👧" },
];

// Matching preference filters
export const TARGET_GENDER_OPTIONS = [
  { id: "bat_ki", label: "Any Gender", icon: "👦/👧" },
  { id: "nam", label: "Male", icon: "👦" },
  { id: "nu", label: "Female", icon: "👧" },
];

export const TARGET_MAJOR_FACULTY_OPTIONS = [
  { id: "bat_ki", label: "Any School / Major" },
  { id: "cung_nganh", label: "Same Major" },
  { id: "cung_truong_khac_nganh", label: "Same School (Different Major)" },
  { id: "khac_truong", label: "Different School" },
];

export const TARGET_COHORT_OPTIONS = [
  { id: "bat_ki", label: "Any Batch" },
  { id: "cung_khoa", label: "Same Batch" },
  { id: "khoa_tren", label: "Senior Student (Higher Batch)" },
  { id: "khoa_duoi", label: "Junior Student (Lower Batch)" },
];

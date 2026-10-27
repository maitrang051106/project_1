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
  { value: "male", label: "Male", icon: "👦" },
  { value: "female", label: "Female", icon: "👧" },
];

// Matching preference filters
export const TARGET_GENDER_OPTIONS = [
  { id: "any", label: "Any Gender", icon: "👦/👧" },
  { id: "male", label: "Male", icon: "👦" },
  { id: "female", label: "Female", icon: "👧" },
];

export const TARGET_MAJOR_FACULTY_OPTIONS = [
  { id: "any", label: "Any School / Major" },
  { id: "same_major", label: "Same Major" },
  { id: "same_faculty", label: "Same School (Different Major)" },
  { id: "different_faculty", label: "Different School" },
];

export const TARGET_COHORT_OPTIONS = [
  { id: "any", label: "Any Batch" },
  { id: "same_cohort", label: "Same Batch" },
  { id: "senior", label: "Senior Student (Higher Batch)" },
  { id: "junior", label: "Junior Student (Lower Batch)" },
];

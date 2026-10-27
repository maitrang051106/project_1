from dataclasses import dataclass

from app.models.enums import Gender, TargetCohort, TargetGender, TargetMajorFaculty


@dataclass(frozen=True)
class UserProfileData:
    user_id: int
    gender: str  # Gender.NAM.value | Gender.NU.value
    faculty_code: str  # Ví dụ "SOICT", "SME", ...
    major_code: str  # Ví dụ "IT1", "IT2", "ME1", ...
    cohort: int  # Ví dụ 68 (cho K68), 67 (cho K67)


@dataclass(frozen=True)
class MatchPreferenceData:
    target_gender: str = TargetGender.BAT_KI.value
    target_major_faculty: str = TargetMajorFaculty.BAT_KI.value
    target_cohort: str = TargetCohort.BAT_KI.value


def check_gender_match(pref_gender: str, candidate_gender: str) -> bool:
    """Kiểm tra ràng buộc giới tính 1 chiều."""
    if pref_gender == TargetGender.BAT_KI.value:
        return True
    return pref_gender == candidate_gender


def check_major_faculty_match(
    pref_major_faculty: str,
    my_faculty: str,
    my_major: str,
    candidate_faculty: str,
    candidate_major: str,
) -> bool:
    """Kiểm tra ràng buộc ngành/trường 1 chiều:
    - cung_nganh: cùng mã ngành
    - cung_truong_khac_nganh: cùng trường nhưng khác mã ngành
    - khac_truong: khác mã trường
    - bat_ki: chấp nhận tất cả
    """
    if pref_major_faculty == TargetMajorFaculty.BAT_KI.value:
        return True
    if pref_major_faculty == TargetMajorFaculty.CUNG_NGANH.value:
        return my_major == candidate_major
    if pref_major_faculty == TargetMajorFaculty.CUNG_TRUONG_KHAC_NGANH.value:
        return (my_faculty == candidate_faculty) and (my_major != candidate_major)
    if pref_major_faculty == TargetMajorFaculty.KHAC_TRUONG.value:
        return my_faculty != candidate_faculty
    return False


def check_cohort_match(
    pref_cohort: str,
    my_cohort: int,
    candidate_cohort: int,
) -> bool:
    """Kiểm tra ràng buộc khóa 1 chiều:
    - khoa_tren: đối phương nhập học trước mình (số khóa nhỏ hơn, vd mình K68 đối phương K67)
    - khoa_duoi: đối phương nhập học sau mình (số khóa lớn hơn, vd mình K68 đối phương K69)
    - cung_khoa: cùng số khóa (vd cùng K68)
    - bat_ki: chấp nhận mọi khóa
    """
    if pref_cohort == TargetCohort.BAT_KI.value:
        return True
    if pref_cohort == TargetCohort.KHOA_TREN.value:
        return candidate_cohort < my_cohort
    if pref_cohort == TargetCohort.KHOA_DUOI.value:
        return candidate_cohort > my_cohort
    if pref_cohort == TargetCohort.CUNG_KHOA.value:
        return candidate_cohort == my_cohort
    return False


def is_mutual_match(
    profile_a: UserProfileData,
    pref_a: MatchPreferenceData,
    profile_b: UserProfileData,
    pref_b: MatchPreferenceData,
) -> bool:
    """Kiểm tra điều kiện ghép cặp hai chiều (Two-way hard filters):
    Cả A thỏa mãn tiêu chí của B VÀ B thỏa mãn tiêu chí của A.
    """
    if profile_a.user_id == profile_b.user_id:
        return False

    # 1. Chiều A đánh giá B
    a_accepts_b = (
        check_gender_match(pref_a.target_gender, profile_b.gender)
        and check_major_faculty_match(
            pref_a.target_major_faculty,
            profile_a.faculty_code,
            profile_a.major_code,
            profile_b.faculty_code,
            profile_b.major_code,
        )
        and check_cohort_match(
            pref_a.target_cohort,
            profile_a.cohort,
            profile_b.cohort,
        )
    )

    if not a_accepts_b:
        return False

    # 2. Chiều B đánh giá A
    b_accepts_a = (
        check_gender_match(pref_b.target_gender, profile_a.gender)
        and check_major_faculty_match(
            pref_b.target_major_faculty,
            profile_b.faculty_code,
            profile_b.major_code,
            profile_a.faculty_code,
            profile_a.major_code,
        )
        and check_cohort_match(
            pref_b.target_cohort,
            profile_b.cohort,
            profile_a.cohort,
        )
    )

    return b_accepts_a


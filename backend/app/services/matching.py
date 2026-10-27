from dataclasses import dataclass

from app.models.enums import Gender, TargetCohort, TargetGender, TargetMajorFaculty


@dataclass(frozen=True)
class UserProfileData:
    user_id: int
    gender: str  # Gender.MALE.value | Gender.FEMALE.value
    faculty_code: str  # e.g. "SOICT", "SME", ...
    major_code: str  # e.g. "IT1", "IT2", "ME1", ...
    cohort: int  # e.g. 68 (for K68), 67 (for K67)


@dataclass(frozen=True)
class MatchPreferenceData:
    target_gender: str = TargetGender.ANY.value
    target_major_faculty: str = TargetMajorFaculty.ANY.value
    target_cohort: str = TargetCohort.ANY.value


def check_gender_match(pref_gender: str, candidate_gender: str) -> bool:
    """Check one-way gender preference."""
    pref = pref_gender.lower()
    cand = candidate_gender.lower()
    # Normalize legacy values
    if pref in (TargetGender.ANY.value, "bat_ki"):
        return True
    if pref == "nam":
        pref = TargetGender.MALE.value
    elif pref == "nu":
        pref = TargetGender.FEMALE.value

    if cand == "nam":
        cand = Gender.MALE.value
    elif cand == "nu":
        cand = Gender.FEMALE.value

    return pref == cand


def check_major_faculty_match(
    pref_major_faculty: str,
    my_faculty: str,
    my_major: str,
    candidate_faculty: str,
    candidate_major: str,
) -> bool:
    """Check one-way major / faculty preference."""
    pref = pref_major_faculty.lower()
    if pref in (TargetMajorFaculty.ANY.value, "bat_ki"):
        return True
    if pref in (TargetMajorFaculty.SAME_MAJOR.value, "cung_nganh"):
        return my_major == candidate_major
    if pref in (TargetMajorFaculty.SAME_FACULTY.value, "cung_truong_khac_nganh"):
        return (my_faculty == candidate_faculty) and (my_major != candidate_major)
    if pref in (TargetMajorFaculty.DIFFERENT_FACULTY.value, "khac_truong"):
        return my_faculty != candidate_faculty
    return False


def check_cohort_match(
    pref_cohort: str,
    my_cohort: int,
    candidate_cohort: int,
) -> bool:
    """Check one-way cohort preference."""
    pref = pref_cohort.lower()
    if pref in (TargetCohort.ANY.value, "bat_ki"):
        return True
    if pref in (TargetCohort.SAME_COHORT.value, "cung_khoa"):
        return my_cohort == candidate_cohort
    if pref in (TargetCohort.SENIOR.value, "khoa_tren"):
        return candidate_cohort < my_cohort
    if pref in (TargetCohort.JUNIOR.value, "khoa_duoi"):
        return candidate_cohort > my_cohort
    return False


def is_mutual_match(
    user_a: UserProfileData,
    pref_a: MatchPreferenceData,
    user_b: UserProfileData,
    pref_b: MatchPreferenceData,
) -> bool:
    """Verify mutual two-way matching satisfaction between User A and User B."""
    # Self-match prevention
    if user_a.user_id == user_b.user_id:
        return False

    # Check A -> B
    a_satisfies_b_gender = check_gender_match(pref_a.target_gender, user_b.gender)
    a_satisfies_b_major = check_major_faculty_match(
        pref_a.target_major_faculty,
        user_a.faculty_code,
        user_a.major_code,
        user_b.faculty_code,
        user_b.major_code,
    )
    a_satisfies_b_cohort = check_cohort_match(
        pref_a.target_cohort,
        user_a.cohort,
        user_b.cohort,
    )
    a_accepts_b = a_satisfies_b_gender and a_satisfies_b_major and a_satisfies_b_cohort

    if not a_accepts_b:
        return False

    # Check B -> A
    b_satisfies_a_gender = check_gender_match(pref_b.target_gender, user_a.gender)
    b_satisfies_a_major = check_major_faculty_match(
        pref_b.target_major_faculty,
        user_b.faculty_code,
        user_b.major_code,
        user_a.faculty_code,
        user_a.major_code,
    )
    b_satisfies_a_cohort = check_cohort_match(
        pref_b.target_cohort,
        user_b.cohort,
        user_a.cohort,
    )
    b_accepts_a = b_satisfies_a_gender and b_satisfies_a_major and b_satisfies_a_cohort

    return b_accepts_a

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from app.models.enums import Gender, TargetCohort, TargetGender, TargetMajorFaculty

VIETNAM_TIMEZONE = timezone(timedelta(hours=7), name="ICT")


def daily_match_limit(trust_score: int) -> int | None:
    """Return the accepted daily conversation quota for a trust score."""
    if trust_score >= 90:
        return None
    if trust_score >= 70:
        return 5
    if trust_score >= 50:
        return 3
    if trust_score > 0:
        return 1
    return 0


def vietnam_day_utc_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return naive UTC bounds for the current Vietnam calendar day."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    local_now = current.astimezone(VIETNAM_TIMEZONE)
    local_start = datetime.combine(local_now.date(), time.min, tzinfo=VIETNAM_TIMEZONE)
    local_end = local_start + timedelta(days=1)
    utc_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = local_end.astimezone(timezone.utc).replace(tzinfo=None)
    return utc_start, utc_end


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
    pref = pref_gender.strip().lower()
    cand = candidate_gender.strip().lower()

    if pref == TargetGender.ANY.value:
        return True
    return pref == cand


def check_major_faculty_match(
    pref_major_faculty: str,
    my_faculty: str,
    my_major: str,
    candidate_faculty: str,
    candidate_major: str,
) -> bool:
    """Check one-way major / faculty preference."""
    pref = pref_major_faculty.strip().lower()

    if pref == TargetMajorFaculty.ANY.value:
        return True
    if pref == TargetMajorFaculty.SAME_MAJOR.value:
        return my_major == candidate_major
    if pref == TargetMajorFaculty.SAME_FACULTY.value:
        return (my_faculty == candidate_faculty) and (my_major != candidate_major)
    if pref == TargetMajorFaculty.DIFFERENT_FACULTY.value:
        return my_faculty != candidate_faculty
    return False


def check_cohort_match(
    pref_cohort: str,
    my_cohort: int,
    candidate_cohort: int,
) -> bool:
    """Check one-way cohort preference."""
    pref = pref_cohort.strip().lower()

    if pref == TargetCohort.ANY.value:
        return True
    if pref == TargetCohort.SAME_COHORT.value:
        return my_cohort == candidate_cohort
    if pref == TargetCohort.SENIOR.value:
        return candidate_cohort < my_cohort
    if pref == TargetCohort.JUNIOR.value:
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

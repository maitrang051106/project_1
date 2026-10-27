from app.models.enums import Gender, TargetCohort, TargetGender, TargetMajorFaculty
from app.services.matching import (
    MatchPreferenceData,
    UserProfileData,
    check_cohort_match,
    check_gender_match,
    check_major_faculty_match,
    is_mutual_match,
)


def test_gender_match() -> None:
    assert check_gender_match(TargetGender.ANY.value, Gender.MALE.value) is True
    assert check_gender_match(TargetGender.ANY.value, Gender.FEMALE.value) is True
    assert check_gender_match(TargetGender.MALE.value, Gender.MALE.value) is True
    assert check_gender_match(TargetGender.MALE.value, Gender.FEMALE.value) is False
    assert check_gender_match(TargetGender.FEMALE.value, Gender.FEMALE.value) is True
    assert check_gender_match(TargetGender.FEMALE.value, Gender.MALE.value) is False


def test_major_faculty_match() -> None:
    # Same major
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.SAME_MAJOR.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT1",
        )
        is True
    )
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.SAME_MAJOR.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT2",
        )
        is False
    )

    # Same faculty, different major
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.SAME_FACULTY.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT2",
        )
        is True
    )
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.SAME_FACULTY.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT1",
        )
        is False
    )
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.SAME_FACULTY.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SME",
            candidate_major="ME1",
        )
        is False
    )

    # Different faculty
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.DIFFERENT_FACULTY.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SME",
            candidate_major="ME1",
        )
        is True
    )
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.DIFFERENT_FACULTY.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT2",
        )
        is False
    )

    # Any
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.ANY.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SME",
            candidate_major="ME1",
        )
        is True
    )


def test_cohort_match() -> None:
    # A is K68 (cohort=68)
    # Senior: candidate_cohort < 68 (K67, K66...)
    assert check_cohort_match(TargetCohort.SENIOR.value, my_cohort=68, candidate_cohort=67) is True
    assert check_cohort_match(TargetCohort.SENIOR.value, my_cohort=68, candidate_cohort=68) is False
    assert check_cohort_match(TargetCohort.SENIOR.value, my_cohort=68, candidate_cohort=69) is False

    # Junior: candidate_cohort > 68 (K69, K70...)
    assert check_cohort_match(TargetCohort.JUNIOR.value, my_cohort=68, candidate_cohort=69) is True
    assert check_cohort_match(TargetCohort.JUNIOR.value, my_cohort=68, candidate_cohort=68) is False
    assert check_cohort_match(TargetCohort.JUNIOR.value, my_cohort=68, candidate_cohort=67) is False

    # Same cohort: candidate_cohort == 68
    assert check_cohort_match(TargetCohort.SAME_COHORT.value, my_cohort=68, candidate_cohort=68) is True
    assert check_cohort_match(TargetCohort.SAME_COHORT.value, my_cohort=68, candidate_cohort=67) is False

    # Any
    assert check_cohort_match(TargetCohort.ANY.value, my_cohort=68, candidate_cohort=67) is True
    assert check_cohort_match(TargetCohort.ANY.value, my_cohort=68, candidate_cohort=69) is True


def test_mutual_match_success() -> None:
    # A: Male, SOICT/IT1, K68. Looking for Female, same faculty different major, junior.
    user_a = UserProfileData(user_id=1, gender="male", faculty_code="SOICT", major_code="IT1", cohort=68)
    pref_a = MatchPreferenceData(
        target_gender="female",
        target_major_faculty="same_faculty",
        target_cohort="junior",
    )

    # B: Female, SOICT/IT2, K69. Looking for Male, same faculty different major, senior.
    user_b = UserProfileData(user_id=2, gender="female", faculty_code="SOICT", major_code="IT2", cohort=69)
    pref_b = MatchPreferenceData(
        target_gender="male",
        target_major_faculty="same_faculty",
        target_cohort="senior",
    )

    assert is_mutual_match(user_a, pref_a, user_b, pref_b) is True


def test_mutual_match_fails_one_sided_preference() -> None:
    # A: Male, K68. Looking for senior.
    user_a = UserProfileData(user_id=1, gender="male", faculty_code="SOICT", major_code="IT1", cohort=68)
    pref_a = MatchPreferenceData(target_cohort="senior")

    # B: Female, K67 (senior to A). But B ALSO looks for senior.
    user_b = UserProfileData(user_id=2, gender="female", faculty_code="SOICT", major_code="IT1", cohort=67)
    pref_b = MatchPreferenceData(target_cohort="senior")

    assert is_mutual_match(user_a, pref_a, user_b, pref_b) is False


def test_mutual_match_self_fails() -> None:
    user_a = UserProfileData(user_id=1, gender="male", faculty_code="SOICT", major_code="IT1", cohort=68)
    pref_a = MatchPreferenceData()
    assert is_mutual_match(user_a, pref_a, user_a, pref_a) is False

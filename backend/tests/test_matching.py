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
    assert check_gender_match(TargetGender.BAT_KI.value, Gender.NAM.value) is True
    assert check_gender_match(TargetGender.BAT_KI.value, Gender.NU.value) is True
    assert check_gender_match(TargetGender.NAM.value, Gender.NAM.value) is True
    assert check_gender_match(TargetGender.NAM.value, Gender.NU.value) is False
    assert check_gender_match(TargetGender.NU.value, Gender.NU.value) is True
    assert check_gender_match(TargetGender.NU.value, Gender.NAM.value) is False


def test_major_faculty_match() -> None:
    # Cùng ngành
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.CUNG_NGANH.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT1",
        )
        is True
    )
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.CUNG_NGANH.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT2",
        )
        is False
    )

    # Cùng trường, khác ngành
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.CUNG_TRUONG_KHAC_NGANH.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT2",
        )
        is True
    )
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.CUNG_TRUONG_KHAC_NGANH.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT1",
        )
        is False
    )
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.CUNG_TRUONG_KHAC_NGANH.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SME",
            candidate_major="ME1",
        )
        is False
    )

    # Khác trường
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.KHAC_TRUONG.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SME",
            candidate_major="ME1",
        )
        is True
    )
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.KHAC_TRUONG.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SOICT",
            candidate_major="IT2",
        )
        is False
    )

    # Bất kì
    assert (
        check_major_faculty_match(
            TargetMajorFaculty.BAT_KI.value,
            my_faculty="SOICT",
            my_major="IT1",
            candidate_faculty="SME",
            candidate_major="ME1",
        )
        is True
    )


def test_cohort_match() -> None:
    # A là K68 (cohort=68)
    # Khóa trên: candidate_cohort < 68 (K67, K66...)
    assert check_cohort_match(TargetCohort.KHOA_TREN.value, my_cohort=68, candidate_cohort=67) is True
    assert check_cohort_match(TargetCohort.KHOA_TREN.value, my_cohort=68, candidate_cohort=68) is False
    assert check_cohort_match(TargetCohort.KHOA_TREN.value, my_cohort=68, candidate_cohort=69) is False

    # Khóa dưới: candidate_cohort > 68 (K69, K70...)
    assert check_cohort_match(TargetCohort.KHOA_DUOI.value, my_cohort=68, candidate_cohort=69) is True
    assert check_cohort_match(TargetCohort.KHOA_DUOI.value, my_cohort=68, candidate_cohort=68) is False
    assert check_cohort_match(TargetCohort.KHOA_DUOI.value, my_cohort=68, candidate_cohort=67) is False

    # Cùng khóa: candidate_cohort == 68
    assert check_cohort_match(TargetCohort.CUNG_KHOA.value, my_cohort=68, candidate_cohort=68) is True
    assert check_cohort_match(TargetCohort.CUNG_KHOA.value, my_cohort=68, candidate_cohort=67) is False

    # Bất kì
    assert check_cohort_match(TargetCohort.BAT_KI.value, my_cohort=68, candidate_cohort=67) is True
    assert check_cohort_match(TargetCohort.BAT_KI.value, my_cohort=68, candidate_cohort=69) is True


def test_mutual_match_success() -> None:
    # A: Nam, SOICT/IT1, K68. Tìm Nữ, cùng trường khác ngành, khóa dưới.
    user_a = UserProfileData(user_id=1, gender="nam", faculty_code="SOICT", major_code="IT1", cohort=68)
    pref_a = MatchPreferenceData(
        target_gender="nu",
        target_major_faculty="cung_truong_khac_nganh",
        target_cohort="khoa_duoi",
    )

    # B: Nữ, SOICT/IT2, K69. Tìm Nam, cùng trường khác ngành, khóa trên.
    user_b = UserProfileData(user_id=2, gender="nu", faculty_code="SOICT", major_code="IT2", cohort=69)
    pref_b = MatchPreferenceData(
        target_gender="nam",
        target_major_faculty="cung_truong_khac_nganh",
        target_cohort="khoa_tren",
    )

    assert is_mutual_match(user_a, pref_a, user_b, pref_b) is True


def test_mutual_match_fails_one_sided_preference() -> None:
    # A: Nam, K68. Tìm khóa trên.
    user_a = UserProfileData(user_id=1, gender="nam", faculty_code="SOICT", major_code="IT1", cohort=68)
    pref_a = MatchPreferenceData(target_cohort="khoa_tren")

    # B: Nữ, K67 (là khóa trên của A). Nhưng B CŨNG tìm khóa trên (muốn gặp K66 trở lên).
    user_b = UserProfileData(user_id=2, gender="nu", faculty_code="SOICT", major_code="IT1", cohort=67)
    pref_b = MatchPreferenceData(target_cohort="khoa_tren")

    # A thỏa mãn B (A muốn gặp B là K67), nhưng B không thỏa mãn vì A là K68 (khóa dưới của B).
    assert is_mutual_match(user_a, pref_a, user_b, pref_b) is False


def test_mutual_match_self_fails() -> None:
    user_a = UserProfileData(user_id=1, gender="nam", faculty_code="SOICT", major_code="IT1", cohort=68)
    pref_a = MatchPreferenceData()
    assert is_mutual_match(user_a, pref_a, user_a, pref_a) is False


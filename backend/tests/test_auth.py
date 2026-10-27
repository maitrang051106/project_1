from app.core.security import (
    create_access_token,
    create_email_hash,
    decode_access_token,
    generate_default_nickname,
    generate_otp,
    hash_password,
    is_valid_hust_email,
    normalize_email,
    verify_password,
)


def test_normalize_email() -> None:
    assert normalize_email("  SV2026@SIS.HUST.EDU.VN  ") == "sv2026@sis.hust.edu.vn"


def test_is_valid_hust_email_strictly_sis() -> None:
    # Only @sis.hust.edu.vn is allowed
    assert is_valid_hust_email("student@sis.hust.edu.vn") is True
    # @hust.edu.vn and other domains must be rejected
    assert is_valid_hust_email("teacher@hust.edu.vn") is False
    assert is_valid_hust_email("user@gmail.com") is False
    assert is_valid_hust_email("invalid-email") is False


def test_password_hashing_and_verification() -> None:
    raw = "HustChatSecret123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert "$" in hashed
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_create_email_hash() -> None:
    h1 = create_email_hash("user1@sis.hust.edu.vn")
    h2 = create_email_hash("user1@sis.hust.edu.vn")
    h3 = create_email_hash("user2@sis.hust.edu.vn")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_generate_otp() -> None:
    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_default_nickname() -> None:
    name = generate_default_nickname()
    assert "#" in name
    assert len(name.split()) >= 2


def test_jwt_token_flow() -> None:
    token = create_access_token({"sub": "42"})
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert "exp" in decoded

from app.core.security import (
    create_access_token,
    create_email_hash,
    decode_access_token,
    generate_anon_name,
    generate_otp,
    is_valid_hust_email,
    normalize_email,
)


def test_normalize_email() -> None:
    assert normalize_email("  SinhVien.IT@HUST.EDU.VN  ") == "sinhvien.it@hust.edu.vn"
    assert normalize_email("Test@sis.hust.edu.vn") == "test@sis.hust.edu.vn"


def test_is_valid_hust_email() -> None:
    assert is_valid_hust_email("sv123@hust.edu.vn") is True
    assert is_valid_hust_email("sv123@sis.hust.edu.vn") is True
    assert is_valid_hust_email("sv123@gmail.com") is False
    assert is_valid_hust_email("sv123@hust.edu.vn.attacker.com") is False
    assert is_valid_hust_email("invalid-email") is False


def test_create_email_hash() -> None:
    h1 = create_email_hash("sv@hust.edu.vn")
    h2 = create_email_hash("  SV@HUST.EDU.VN  ")
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex string


def test_generate_otp() -> None:
    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_anon_name() -> None:
    name = generate_anon_name()
    assert "#" in name
    assert len(name) > 5


def test_jwt_token_flow() -> None:
    from app.core.config import settings
    settings.jwt_secret = "hust-chatbox-secret-jwt-key-2026-very-secure-32b"
    token = create_access_token({"sub": "42"})
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"

    bad_payload = decode_access_token("invalid.token.string")
    assert bad_payload is None

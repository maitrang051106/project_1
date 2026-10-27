from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import random
import secrets

import jwt

from app.core.config import settings

ALLOWED_DOMAINS = ("hust.edu.vn", "sis.hust.edu.vn")

ANON_ADJECTIVES = [
    "Dũng Cảm", "Nhiệt Huyết", "Thầm Lặng", "Thức Khuya", "Yêu Đời",
    "Chăm Chỉ", "Bí Ẩn", "Lãng Tử", "Tinh Nghịch", "Thông Thái",
    "Bá Đạo", "Bình Yên", "Mơ Mộng", "Tốc Độ", "Kiên Cường"
]

ANON_NOUNS = [
    "Cú Đêm", "Bách Khoa", "Chim Én", "Hải Âu", "Gấu Nâu",
    "Kỹ Sư", "Lập Trình Viên", "Chiến Binh", "Học Giả", "Đồng Tu",
    "Nhà Thơ", "Thám Tử", "Thần Đồng", "Sư Huynh", "Sư Muội"
]


def normalize_email(email: str) -> str:
    """Chuẩn hóa email: viết thường, loại bỏ khoảng trắng."""
    return email.strip().lower()


def is_valid_hust_email(email: str) -> bool:
    """Kiểm tra domain email có thuộc trường HUST hay không (@hust.edu.vn hoặc @sis.hust.edu.vn)."""
    norm = normalize_email(email)
    if "@" not in norm:
        return False
    domain = norm.split("@")[-1]
    return domain in ALLOWED_DOMAINS


def create_email_hash(email: str) -> str:
    """Tạo HMAC-SHA256 băm email để bảo vệ danh tính, không lưu email thô."""
    norm = normalize_email(email)
    return hmac.new(
        settings.otp_secret.encode("utf-8"),
        norm.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_otp() -> str:
    """Sinh mã OTP 6 chữ số ngẫu nhiên an toàn bằng secrets."""
    return "".join(secrets.choice("0123456789") for _ in range(6))


def hash_otp(otp: str) -> str:
    """Băm OTP bằng SHA256 trước khi lưu để bảo mật."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def generate_anon_name() -> str:
    """Tạo tên ẩn danh thân thiện cho sinh viên, ví dụ 'Cú Đêm Bá Đạo #3821'."""
    noun = random.choice(ANON_NOUNS)
    adj = random.choice(ANON_ADJECTIVES)
    num = random.randint(1000, 9999)
    return f"{noun} {adj} #{num}"


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Tạo JWT Token xác thực người dùng."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(seconds=settings.jwt_expire_seconds)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Giải mã và xác minh JWT Token."""
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None


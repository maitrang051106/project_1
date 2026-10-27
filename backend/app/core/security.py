from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import random
import secrets

import jwt

from app.core.config import settings
from app.core.constants import ALLOWED_EMAIL_DOMAINS

ALLOWED_DOMAINS = ALLOWED_EMAIL_DOMAINS

ANON_ADJECTIVES = [
    "Brave", "Curious", "Silent", "Midnight", "Cheerful",
    "Diligent", "Mystic", "Clever", "Swift", "Resilient"
]

ANON_NOUNS = [
    "Owl", "Phoenix", "Sparrow", "Falcon", "Panda",
    "Engineer", "Coder", "Scholar", "Explorer", "Seeker"
]


def normalize_email(email: str) -> str:
    """Normalize email: lowercase and strip whitespace."""
    return email.strip().lower()


def is_valid_hust_email(email: str) -> bool:
    """Check if email belongs to HUST SIS domain (@sis.hust.edu.vn only)."""
    norm = normalize_email(email)
    if "@" not in norm:
        return False
    domain = norm.split("@")[-1]
    return domain in ALLOWED_DOMAINS


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with random 16-byte salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against PBKDF2 hash."""
    try:
        salt, expected_hash = hashed_password.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(dk.hex(), expected_hash)
    except Exception:
        return False


def create_email_hash(email: str) -> str:
    """Generate HMAC-SHA256 hash of email to protect identity without storing raw email."""
    norm = normalize_email(email)
    return hmac.new(
        settings.otp_secret.encode("utf-8"),
        norm.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_otp() -> str:
    """Generate secure random 6-digit OTP using secrets."""
    return "".join(secrets.choice("0123456789") for _ in range(6))


def hash_otp(otp: str) -> str:
    """Hash OTP using SHA-256 before storing for security."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def generate_default_nickname() -> str:
    """Generate default student nickname (e.g. 'Midnight Owl #3821')."""
    noun = random.choice(ANON_NOUNS)
    adj = random.choice(ANON_ADJECTIVES)
    num = random.randint(1000, 9999)
    return f"{adj} {noun} #{num}"


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token for user authentication."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(seconds=settings.jwt_expire_seconds)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode and verify JWT access token."""
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None


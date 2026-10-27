# backend/app/core/constants.py

ALLOWED_EMAIL_DOMAINS = ("sis.hust.edu.vn",)

MIN_COHORT = 63
MAX_COHORT = 71

OTP_TTL_SECONDS = 300
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5

MAX_CHAT_MESSAGE_LENGTH = 1000
MAX_DIRECT_MESSAGE_LENGTH = 2000

DEFAULT_AVATAR = "🦉"
AVATAR_OPTIONS = (
    "🦉", "🐱", "🐸", "🐶", "🐵", "🐰", "🐻", "🐧", "🐹", "🦊", "🐼"
)


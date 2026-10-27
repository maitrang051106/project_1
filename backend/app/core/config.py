import re
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HUST Chatbox API"
    environment: str = "development"
    database_url: str = (
        "mysql+aiomysql://hust_chatbox:replace-me@127.0.0.1:3306/hust_chatbox"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    otp_secret: str = "hust-chatbox-otp-secret-key-2026-very-secure-32b"
    jwt_secret: str = "hust-chatbox-jwt-secret-key-2026-very-secure-32b"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 86400  # 1 day
    email_host: str = "smtp.gmail.com"
    email_port: int = 587
    email_username: str | None = None
    email_password: str | None = None
    email_from: str = "hustchatbox@gmail.com"
    email_use_tls: bool = True
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        # Auto-convert mysql:// to async driver mysql+aiomysql://
        if v.startswith("mysql://"):
            v = "mysql+aiomysql://" + v[len("mysql://"):]
        # Remove unsupported query params like ?ssl-mode=REQUIRED
        v = re.sub(r"[?&]ssl-mode=[^&]*", "", v)
        v = re.sub(r"[?&]$", "", v)
        return v

    @field_validator("frontend_origin", mode="after")
    @classmethod
    def normalize_frontend_origin(cls, v: str) -> str:
        # Strip trailing path (e.g. /login) so browser CORS Origin header matches
        parsed = urlparse(v)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return v.rstrip("/")


settings = Settings()


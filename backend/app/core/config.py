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
    jwt_expire_seconds: int = 86400  # 1 ngày
    email_host: str = "127.0.0.1"
    email_port: int = 1025
    email_from: str = "noreply@hust.edu.vn"
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    model_config = SettingsConfigDict(
        env_file=".env",
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


import re
import secrets
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HUST Chatbox API"
    environment: str = "development"
    database_url: str = (
        "mysql+aiomysql://hust_chatbox:replace-me@127.0.0.1:3306/hust_chatbox"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    otp_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    email_hash_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
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
    rate_limit_ip_requests: int = 20
    rate_limit_ip_window_seconds: int = 60
    rate_limit_email_requests: int = 5
    rate_limit_email_window_seconds: int = 300
    login_rate_limit_email_attempts: int = 10
    login_rate_limit_email_window_seconds: int = 900
    trusted_proxies: str = "127.0.0.1,::1"
    match_timeout_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return list(
            dict.fromkeys(
                [
                    self.frontend_origin,
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:3000",
                    "https://project-1-hust-chatbox.vercel.app",
                    "https://project-1-qtlhgs1xa-maitrang051106s-projects.vercel.app",
                ]
            )
        )

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.environment.lower() != "production":
            return self

        required_fields = (
            "database_url",
            "redis_url",
            "otp_secret",
            "email_hash_secret",
            "jwt_secret",
            "email_host",
            "email_port",
            "email_username",
            "email_password",
            "email_from",
            "email_use_tls",
            "frontend_origin",
            "cookie_secure",
            "cookie_samesite",
        )
        missing_fields = [
            field_name
            for field_name in required_fields
            if field_name not in self.model_fields_set
        ]
        if missing_fields:
            names = ", ".join(field.upper() for field in missing_fields)
            raise ValueError(f"Production configuration is missing: {names}")

        for field_name in ("otp_secret", "email_hash_secret", "jwt_secret"):
            value = getattr(self, field_name)
            if len(value.encode("utf-8")) < 32 or value.lower().startswith(
                ("replace-with", "change-me", "your-")
            ):
                raise ValueError(
                    f"{field_name.upper()} must be a non-placeholder secret of at least 32 bytes"
                )

        if not self.cookie_secure or self.cookie_samesite.lower() != "none":
            raise ValueError(
                "Production cookies require COOKIE_SECURE=true and COOKIE_SAMESITE=none"
            )

        return self

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


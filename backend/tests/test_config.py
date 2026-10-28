import ssl

import pytest
from app.core.config import Settings
from app.core.db import get_db_connect_args
from app.api.deps import is_allowed_websocket_origin


def test_settings_read_values_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "HUST Chatbox Test")

    settings = Settings(_env_file=None)

    assert settings.app_name == "HUST Chatbox Test"


def test_development_secret_defaults_are_ephemeral() -> None:
    first = Settings(_env_file=None)
    second = Settings(_env_file=None)

    assert first.jwt_secret != second.jwt_secret
    assert len(first.jwt_secret) >= 32


def test_production_requires_explicit_database_redis_and_secrets() -> None:
    with pytest.raises(ValueError, match="Production configuration is missing"):
        Settings(_env_file=None, environment="production")


def test_production_rejects_placeholder_secrets() -> None:
    with pytest.raises(ValueError, match="non-placeholder secret"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="mysql+aiomysql://user:pass@db.example/app",
            redis_url="redis://redis.example/0",
            otp_secret="replace-with-a-random-32b-secret-key",
            email_hash_secret="e" * 32,
            jwt_secret="j" * 32,
            email_host="smtp.gmail.com",
            email_port=587,
            email_username="sender@gmail.com",
            email_password="application-password",
            email_from="sender@gmail.com",
            email_use_tls=True,
            frontend_origin="https://chat.example",
            cookie_secure=True,
            cookie_samesite="none",
        )


def test_production_accepts_required_environment_variables(monkeypatch) -> None:
    values = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "mysql+aiomysql://user:pass@db.example/app",
        "REDIS_URL": "redis://redis.example/0",
        "OTP_SECRET": "o" * 40,
        "EMAIL_HASH_SECRET": "e" * 40,
        "JWT_SECRET": "j" * 40,
        "EMAIL_HOST": "smtp.gmail.com",
        "EMAIL_PORT": "587",
        "EMAIL_USERNAME": "sender@gmail.com",
        "EMAIL_PASSWORD": "application-password",
        "EMAIL_FROM": "sender@gmail.com",
        "EMAIL_USE_TLS": "true",
        "FRONTEND_ORIGIN": "https://chat.example",
        "COOKIE_SECURE": "true",
        "COOKIE_SAMESITE": "none",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    assert settings.environment == "production"
    assert settings.otp_secret == "o" * 40


def test_production_rejects_insecure_cookie_defaults(monkeypatch) -> None:
    values = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "mysql+aiomysql://user:pass@db.example/app",
        "REDIS_URL": "redis://redis.example/0",
        "OTP_SECRET": "o" * 40,
        "EMAIL_HASH_SECRET": "e" * 40,
        "JWT_SECRET": "j" * 40,
        "EMAIL_HOST": "smtp.gmail.com",
        "EMAIL_PORT": "587",
        "EMAIL_USERNAME": "sender@gmail.com",
        "EMAIL_PASSWORD": "application-password",
        "EMAIL_FROM": "sender@gmail.com",
        "EMAIL_USE_TLS": "true",
        "FRONTEND_ORIGIN": "https://chat.example",
        "COOKIE_SECURE": "false",
        "COOKIE_SAMESITE": "lax",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match="Production cookies require"):
        Settings(_env_file=None)


def test_settings_database_url_normalization(monkeypatch) -> None:
    raw_url = "mysql://avnadmin:secret@mysql-host.aivencloud.com:11585/defaultdb?ssl-mode=REQUIRED"
    monkeypatch.setenv("DATABASE_URL", raw_url)

    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("mysql+aiomysql://")
    assert "ssl-mode" not in settings.database_url
    assert settings.database_url == "mysql+aiomysql://avnadmin:secret@mysql-host.aivencloud.com:11585/defaultdb"


def test_settings_frontend_origin_normalization(monkeypatch) -> None:
    raw_origin = "https://project-1-7lgj.vercel.app/login"
    monkeypatch.setenv("FRONTEND_ORIGIN", raw_origin)

    settings = Settings(_env_file=None)
    assert settings.frontend_origin == "https://project-1-7lgj.vercel.app"


def test_websocket_origin_must_be_allowlisted() -> None:
    assert is_allowed_websocket_origin("http://localhost:5173") is True
    assert is_allowed_websocket_origin("https://attacker.example") is False
    assert is_allowed_websocket_origin(None) is False


def test_get_db_connect_args_for_aiven_cloud() -> None:
    args = get_db_connect_args("mysql+aiomysql://user:pass@mysql-host.aivencloud.com:11585/hust_chatbox")
    assert "ssl" in args
    ctx = args["ssl"]
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_NONE


def test_get_db_connect_args_for_sqlite() -> None:
    args = get_db_connect_args("sqlite+aiosqlite:///:memory:")
    assert args == {}


def test_settings_email_configuration(monkeypatch) -> None:
    monkeypatch.setenv("EMAIL_HOST", "smtp.gmail.com")
    monkeypatch.setenv("EMAIL_PORT", "587")
    monkeypatch.setenv("EMAIL_USERNAME", "testuser@gmail.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "abcd efgh ijkl mnop")
    monkeypatch.setenv("EMAIL_FROM", "testuser@gmail.com")
    monkeypatch.setenv("EMAIL_USE_TLS", "true")

    settings = Settings(_env_file=None)
    assert settings.email_host == "smtp.gmail.com"
    assert settings.email_port == 587
    assert settings.email_username == "testuser@gmail.com"
    assert settings.email_password == "abcd efgh ijkl mnop"
    assert settings.email_from == "testuser@gmail.com"
    assert settings.email_use_tls is True


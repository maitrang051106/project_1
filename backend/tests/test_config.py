import ssl
from app.core.config import Settings
from app.core.db import get_db_connect_args


def test_settings_read_values_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "HUST Chatbox Test")

    settings = Settings(_env_file=None)

    assert settings.app_name == "HUST Chatbox Test"


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

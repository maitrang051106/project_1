from app.core.config import Settings


def test_settings_read_values_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "HUST Chatbox Test")

    settings = Settings(_env_file=None)

    assert settings.app_name == "HUST Chatbox Test"

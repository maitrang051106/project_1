from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HUST Chatbox API"
    environment: str = "development"
    database_url: str = (
        "mysql+aiomysql://hust_chatbox:replace-me@127.0.0.1:3306/hust_chatbox"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    otp_secret: str = ""
    jwt_secret: str = ""
    email_host: str = "127.0.0.1"
    email_port: int = 1025
    email_from: str = "noreply@hust.edu.vn"
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    match_threshold: float = 0.5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

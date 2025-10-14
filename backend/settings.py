# backend/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Яндекс XML Search
    YANDEX_XML_USER: str | None = None
    YANDEX_XML_KEY: str | None = None
    YANDEX_XML_ENDPOINT: str = "https://yandex.com/search/xml"

    # Базовая оригинальность (когда ключи есть)
    ORIGINALITY_BASE: float = 83.3

    # где лежит .env и что делать с "лишними" ключами
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",   # не падать, если в .env встретится незнакомый ключ
    )

settings = Settings()

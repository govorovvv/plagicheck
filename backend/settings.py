from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Yandex XML Search (официальный API)
    YANDEX_XML_USER: str | None = None   # логин для XML-поиска
    YANDEX_XML_KEY: str | None = None    # ключ XML-поиска
    YANDEX_XML_ENDPOINT: str = "https://yandex.com/search/xml"

    # Базовый % для демо (используется, когда ключи есть)
    ORIGINALITY_BASE: float = 83.3

    class Config:
        env_file = ".env"


settings = Settings()

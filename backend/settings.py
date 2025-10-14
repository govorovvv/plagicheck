from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- Yandex Cloud Search API ---
    YC_SEARCH_API_KEY: str | None = None
    YC_FOLDER_ID: str | None = None
    YC_SEARCH_ENDPOINT: str = "https://searchapi.api.cloud.yandex.net/v2/web/searchAsync"
    YC_OPERATION_ENDPOINT: str = "https://operation.api.cloud.yandex.net/operations"

    # базовая оригинальность (когда ключи есть)
    ORIGINALITY_BASE: float = 83.3

    # где брать .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()

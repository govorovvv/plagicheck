
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    YANDEX_XML_USER: str = ""
    YANDEX_XML_KEY: str = ""
    YANDEX_XML_ENDPOINT: str = "https://yandex.com/search/xml"

settings = Settings(_env_file=".env", _env_file_encoding="utf-8")


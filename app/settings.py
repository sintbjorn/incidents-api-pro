from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@db:5432/incidents"
    API_KEY: str | None = None
    NOTIFICATION_SERVICE_URL: str | None = None
    NOTIFICATION_SERVICE_API_KEY: str | None = None
    NOTIFICATION_CHANNEL: str = "telegram"
    NOTIFICATION_TIMEOUT_SECONDS: float = 5.0

settings = Settings()

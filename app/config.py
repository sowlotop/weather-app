from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENWEATHER_API_KEY: str
    RATE_LIMIT_PER_MINUTE: int = 30
    EXTERNAL_API_BASE: str = "https://api.openweathermap.org/data/2.5/weather"
    REQUEST_TIMEOUT_SECONDS: int = 6
    PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

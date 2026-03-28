from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "postgresql://homebase:homebase@localhost:5432/homebase"
    google_calendar_id: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()

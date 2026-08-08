from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SteuerHelfer API"
    environment: str = "development"
    tax_year: int = 2025
    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

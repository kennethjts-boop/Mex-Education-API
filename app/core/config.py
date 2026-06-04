import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    SUPABASE_URL: str = Field(default="https://placeholder-project.supabase.co")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="placeholder-key")
    OPENAI_API_KEY: str = Field(default="")
    APP_ENV: str = Field(default="development")
    PORT: int = Field(default=8000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Set

class Settings(BaseSettings):
    SUPABASE_URL: str = Field(default="https://placeholder-project.supabase.co")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="placeholder-key")
    OPENAI_API_KEY: str = Field(default="")
    APP_ENV: str = Field(default="development")
    PORT: int = Field(default=8000)
    
    # Configuración de subida de archivos
    ALLOWED_EXTENSIONS: Set[str] = {"pdf", "docx", "txt", "csv", "xlsx", "png", "jpg", "jpeg"}
    MAX_FILE_SIZE_MB: int = 50
    MAX_BATCH_SIZE: int = 50
    SUPABASE_STORAGE_BUCKET: str = "documentos"
    UPLOAD_DIR: str = "data/uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

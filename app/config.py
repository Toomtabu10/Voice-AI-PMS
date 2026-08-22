from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    LLM_MODEL: str = "openai/gpt-4o-mini"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    XAI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    OLLAMA_API_BASE: str | None = None

    DATABASE_URL: str = "sqlite:///./data/patient_records.db"
    UPLOAD_DIR: str = "./uploads"
    SECRET_KEY: str = "dev-secret-change-me"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Application
    APP_NAME: str = Field(default="MultiAgentCodeReviewer", env="APP_NAME")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    # Database (default to SQLite for local testing)
    POSTGRES_DSN: str = Field(default="sqlite+aiosqlite:///./dev.db", env="POSTGRES_DSN")
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    # GitHub
    GITHUB_APP_ID: int = Field(default=0, env="GITHUB_APP_ID")
    GITHUB_PRIVATE_KEY: str = Field(default="", env="GITHUB_PRIVATE_KEY")
    GITHUB_WEBHOOK_SECRET: str = Field(default="test_secret", env="GITHUB_WEBHOOK_SECRET")
    # LLM Provider
    LLM_PROVIDER: str = Field(default="mock", env="LLM_PROVIDER")
    LLM_API_KEY: str | None = Field(default=None, env="LLM_API_KEY")
    LLM_MODEL: str = Field(default="gpt-4o-mini", env="LLM_MODEL")

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

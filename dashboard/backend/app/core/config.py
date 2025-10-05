"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "DataLake Discovery API"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # AWS Settings
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    
    # State File
    STATE_FILE_PATH: str = os.getenv("STATE_FILE_PATH", ".datalake-state.json")
    
    # Database (for storing history)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./datalake_dashboard.db"
    )
    
    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "your-secret-key-change-in-production"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()

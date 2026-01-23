from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Virtual Closet"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_CHANGE_ME"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # Database - SQLite by default (no installation needed)
    DATABASE_URL: str = "sqlite:///./virtual_closet.db"
    
    # Gemini API Key
    GEMINI_API_KEY: str = ""
    
    # Zep API Key
    ZEP_API_KEY: str = ""

    # Pinterest OAuth
    PINTEREST_APP_ID: str = "1543846"
    PINTEREST_APP_SECRET: str = "db774016ccd9aaa2805e688b39fd9055c581efcf"
    PINTEREST_REDIRECT_URI: str = "http://localhost:3000/auth/pinterest-callback"
    PINTEREST_FRONTEND_REDIRECT: str = "http://localhost:3000/onboarding"

    # AWS S3 (optional - for image storage)
    S3_BUCKET: str = "virtual-closet-assets"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

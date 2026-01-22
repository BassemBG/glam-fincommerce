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
    
    # Groq API Key (Main AI service)
    GROQ_API_KEY: str = ""
    
    # Tavily API Key (Price lookup)
    TAVILY_API_KEY: str = ""

    # AWS S3 (optional - for image storage)
    S3_BUCKET: str = "virtual-closet-assets"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    
    # Qdrant Vector Database (Cloud)
    QDRANT_URL: str = "https://86d64e8e-85e3-4573-8605-c55a200e11dc.europe-west3-0.gcp.cloud.qdrant.io"

    QDRANT_API_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.r8hipkRAT0JK8W7ZQfsAvCplnQEd8sJla62Beigmaoc"  # Required for Qdrant Cloud
    QDRANT_COLLECTION_NAME: str = "clothing_embeddings"
    QDRANT_COLLECTION_NAME_CLIP: str = "clothing_clip_embeddings"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

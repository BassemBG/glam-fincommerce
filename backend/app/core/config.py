from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # ===========================
    # CORE PROJECT CONFIG
    # ===========================
    PROJECT_NAME: str = "AI Virtual Closet"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_CHANGE_ME"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # ===========================
    # DATABASE
    # ===========================
    DATABASE_URL: str = "sqlite:///./virtual_closet.db"

    # ===========================
    # EXISTING AI CONFIG
    # ===========================
    GEMINI_API_KEY: str = ""

    # ===========================
    # BRAND INGESTION – QDRANT
    # ===========================
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "clothing"

    # ===========================
    # BRAND INGESTION – EMBEDDINGS
    # ===========================
    BRAND_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    BRAND_EMBEDDING_DIMENSION: int = 384

    # ===========================
    # LLM / EXTERNAL APIS
    # ===========================
    OPENAI_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None

    # ===========================
    # AWS S3 (optional)
    # ===========================
    S3_BUCKET: str = "virtual-closet-assets"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()

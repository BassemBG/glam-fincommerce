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
    # AI SERVICES
    # ===========================
    # Groq API Key (Main AI service)
    GROQ_API_KEY: str = ""
    
    # Tavily API Key (Price lookup)
    TAVILY_API_KEY: str = ""
    
    # Gemini API Key
    GEMINI_API_KEY: str = ""
    
    # Zep API Key
    ZEP_API_KEY: str = ""
    
    # Qdrant Vector DB
    QDRANT_URL: str = "https://86d64e8e-85e3-4573-8605-c55a200e11dc.europe-west3-0.gcp.cloud.qdrant.io"
    QDRANT_API_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.r8hipkRAT0JK8W7ZQfsAvCplnQEd8sJla62Beigmaoc"
    QDRANT_COLLECTION_NAME: str = "clothing_embeddings"

    # ===========================
    # PINTEREST OAUTH
    # ===========================
    PINTEREST_APP_ID: str = "1543846"
    PINTEREST_APP_SECRET: str = "db774016ccd9aaa2805e688b39fd9055c581efcf"
    PINTEREST_REDIRECT_URI: str = "http://localhost:3000/auth/pinterest-callback"
    PINTEREST_FRONTEND_REDIRECT: str = "http://localhost:3000/onboarding"

    # ===========================
    # AZURE STORAGE
    # ===========================
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "images"

    # ===========================
    # AZURE OPENAI (for AI-powered try-on)
    # ===========================
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_IMAGE_DEPLOYMENT: str = "gpt-image-1.5"

    # ===========================
    # LANGCHAIN
    # ===========================
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = ""
    LANGSMITH_ENDPOINT: str = ""

    # ===========================
    # AWS S3 (optional - for image storage)
    # ===========================
    S3_BUCKET: str = "virtual-closet-assets"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    
    # ===========================
    # QDRANT VECTOR DATABASE
    # ===========================
    QDRANT_URL: str = "https://86d64e8e-85e3-4573-8605-c55a200e11dc.europe-west3-0.gcp.cloud.qdrant.io"
    QDRANT_API_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.r8hipkRAT0JK8W7ZQfsAvCplnQEd8sJla62Beigmaoc"
    QDRANT_COLLECTION_NAME: str = "clothing_embeddings"
    QDRANT_COLLECTION_NAME_CLIP: str = "clothing_clip_embeddings"
    QDRANT_COLLECTION_NAME_OUTFITS: str = "outfits_clip_embeddings"

    # ===========================
    # BRAND INGESTION EMBEDDINGS
    # ===========================
    BRAND_EMBEDDING_MODEL: str = "openai/clip-vit-base-patch32"
    BRAND_EMBEDDING_DIMENSION: int = 512

    # ===========================
    # EXTERNAL APIS
    # ===========================
    OPENAI_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()

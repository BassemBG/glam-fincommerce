import google.generativeai as genai
from app.core.config import settings
import logging
from typing import List

class EmbeddingService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        else:
            logging.warning("GEMINI_API_KEY not found. Embedding features will be disabled.")

    async def get_text_embedding(self, text: str) -> List[float]:
        """Generates a text embedding using Gemini."""
        if not settings.GEMINI_API_KEY:
            return [0.0] * 768 # Default size for many models

        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="clustering"
            )
            return result['embedding']
        except Exception as e:
            logging.error(f"Embedding generation error: {e}")
            return [0.0] * 768

embedding_service = EmbeddingService()

from app.core.config import settings
import logging
from typing import List

genai = None
if settings.GEMINI_API_KEY:
    try:
        from google import genai as genai
    except Exception:
        genai = None

class EmbeddingService:
    def __init__(self):
        if settings.GEMINI_API_KEY and genai:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
            except Exception:
                pass

    async def get_text_embedding(self, text: str) -> List[float]:
        """Generates a text embedding using Gemini."""
        if not (settings.GEMINI_API_KEY and genai):
            return [0.0] * 768 # Default size for many models

        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="clustering"
            )
            return result['embedding']
        except Exception as e:
            logging.debug(f"Embedding generation error: {e}")
            return [0.0] * 768

embedding_service = EmbeddingService()

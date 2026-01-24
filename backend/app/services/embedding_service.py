from fastembed import TextEmbedding
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
        try:
            # We use bge-small-en-v1.5 by default (384 dimensions)
            self.model = TextEmbedding()
        except Exception as e:
            logging.error(f"Failed to initialize FastEmbed: {e}")
            self.model = None

    async def get_text_embedding(self, text: str) -> List[float]:
        """Generates a text embedding using FastEmbed."""
        if not self.model:
            return [0.0] * 384

        try:
            # fastembed returns a generator of embeddings
            embeddings = list(self.model.embed([text]))
            if embeddings:
                return embeddings[0].tolist()
            return [0.0] * 384
        except Exception as e:
            logging.error(f"Embedding generation error: {e}")
            return [0.0] * 384

embedding_service = EmbeddingService()

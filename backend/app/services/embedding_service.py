from app.services.groq_vision_service import groq_vision_service
import logging
from typing import List

class EmbeddingService:
    def __init__(self):
        self.groq_service = groq_vision_service
        if not self.groq_service.client:
            logging.warning("GROQ_API_KEY not found. Embedding features will use fallback method.")

    async def get_text_embedding(self, text: str) -> List[float]:
        """Generates a text embedding using Groq service."""
        try:
            return await self.groq_service.generate_text_embedding(text)
        except Exception as e:
            logging.error(f"Embedding generation error: {e}")
            return [0.0] * 768

embedding_service = EmbeddingService()

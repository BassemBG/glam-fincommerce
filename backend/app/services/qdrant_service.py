from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
import logging
import os
from typing import List, Dict, Any, Optional

class QdrantService:
    def __init__(self):
        self.collection_name = "outfits"
        # We'll use a local path for storage if not provided in settings
        storage_path = os.path.join(os.getcwd(), "qdrant_storage")
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)
            
        self.client = QdrantClient(path=storage_path)
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            vector_size = 384 # FastEmbed bge-small-en-v1.5 size
            
            if exists:
                # Check if vector size matches
                collection_info = self.client.get_collection(self.collection_name)
                current_size = collection_info.config.params.vectors.size
                if current_size != vector_size:
                    logging.warning(f"Vector size mismatch ({current_size} != {vector_size}). Recreating collection.")
                    self.client.delete_collection(self.collection_name)
                    exists = False

            if not exists:
                logging.info(f"Creating collection: {self.collection_name} with size {vector_size}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
        except Exception as e:
            logging.error(f"Error ensuring Qdrant collection: {e}")

    async def upsert_outfit(self, outfit_id: str, vector: List[float], payload: Dict[str, Any]):
        """Upserts an outfit embedding and its metadata."""
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=outfit_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            logging.error(f"Qdrant upsert error: {e}")
            return False

    async def search_similar_outfits(self, vector: List[float], limit: int = 5, filter_dict: Optional[Dict] = None):
        """Searches for similar outfits."""
        try:
            query_filter = None
            if filter_dict:
                # Basic filter implementation
                must = [
                    models.FieldCondition(
                        key=k,
                        match=models.MatchValue(value=v)
                    ) for k, v in filter_dict.items()
                ]
                query_filter = models.Filter(must=must)

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit
            )
            return results
        except Exception as e:
            logging.error(f"Qdrant search error: {e}")
            return []

qdrant_service = QdrantService()

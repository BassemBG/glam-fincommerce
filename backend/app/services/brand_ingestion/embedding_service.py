import logging
import uuid
from typing import Dict, List, Any
from sentence_transformers import SentenceTransformer
from qdrant_client.models import PointStruct, VectorParams, Distance
from app.core.config import settings
from .qdrant_client import QdrantManager

EMBEDDING_MODEL = settings.BRAND_EMBEDDING_MODEL
QDRANT_COLLECTION_NAME = settings.QDRANT_COLLECTION_NAME


logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        self.qdrant_manager = QdrantManager()
        self.qdrant_client = self.qdrant_manager.get_client()
        self.collection_name = QDRANT_COLLECTION_NAME

        logger.info(
            f"✅ EmbeddingService initialized "
            f"(model={EMBEDDING_MODEL}, dim={self.embedding_dim})"
        )

    # COLLECTION MANAGEMENT

    def create_collection_if_not_exists(self):
        if self.qdrant_client.collection_exists(self.collection_name):
            logger.info(f"✅ Collection '{self.collection_name}' already exists")
            return False

        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE
            )
        )

        logger.info(f"✅ Created collection '{self.collection_name}'")
        return True

    # EMBEDDING GENERATION

    def _compose_style_text(self, style_group: Dict[str, Any], brand_name: str) -> str:
        return (
            f"Brand: {brand_name}. "
            f"Style: {style_group.get('style_name', 'Unknown')}. "
            f"Products: {', '.join(style_group.get('product_types', []))}. "
            f"Aesthetics: {', '.join(style_group.get('aesthetic_keywords', []))}. "
            f"Price range: {style_group.get('price_range', {})}."
        )

    def embed_style_group(self, style_group: Dict[str, Any], brand_name: str) -> List[float]:
        text = self._compose_style_text(style_group, brand_name)
        return self.model.encode(text).tolist()

    # UPSERT TO QDRANT

    def upsert_style_to_qdrant(
        self,
        style_group: Dict[str, Any],
        brand_name: str,
        source: str = "website"
    ) -> str:
        embedding = self.embed_style_group(style_group, brand_name)

        payload = {
            "brand_name": brand_name,
            "style_name": style_group.get("style_name"),
            "product_types": style_group.get("product_types", []),
            "aesthetic_keywords": style_group.get("aesthetic_keywords", []),
            "price_range": style_group.get("price_range"),
            "source": source
        }

        point_id = str(uuid.uuid4())

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload
        )

        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

        logger.info(f"✅ Stored style '{payload['style_name']}' → Qdrant")
        return point_id

    def upsert_brand_styles(self, brand_data: Dict[str, Any], source="website") -> List[str]:
        brand_name = brand_data["brand_name"]
        styles = brand_data["style_groups"]

        return [
            self.upsert_style_to_qdrant(style, brand_name, source)
            for style in styles
        ]

    # LIST / AGGREGATE

    def list_brands(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return aggregated brands and their style groups from Qdrant."""
        if not self.qdrant_client.collection_exists(self.collection_name):
            return []

        offset = None
        brand_map: Dict[str, Dict[str, Any]] = {}

        while True:
            points, next_offset = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                offset=offset,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                break

            for point in points:
                payload = point.payload or {}
                brand_name = payload.get("brand_name") or "Unknown"

                style_group = {
                    "style_name": payload.get("style_name"),
                    "product_types": payload.get("product_types", []),
                    "price_range": payload.get("price_range"),
                    "aesthetic_keywords": payload.get("aesthetic_keywords", []),
                    "target_demographic": payload.get("target_demographic"),
                    "sustainability_score": payload.get("sustainability_score"),
                }

                brand_entry = brand_map.setdefault(
                    brand_name,
                    {"brand_name": brand_name, "style_groups": []},
                )
                brand_entry["style_groups"].append(style_group)

            if next_offset is None:
                break
            offset = next_offset

        for entry in brand_map.values():
            entry["num_styles"] = len(entry.get("style_groups", []))

        return list(brand_map.values())

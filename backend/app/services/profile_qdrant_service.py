import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict

from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, PayloadSchemaType
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.services.brand_ingestion.qdrant_client import QdrantManager

logger = logging.getLogger(__name__)

COLLECTION_NAME = "ProfileBrands"
EMBEDDING_MODEL = settings.BRAND_EMBEDDING_MODEL or "all-MiniLM-L6-v2"


class ProfileQdrantService:
    """Manage brand profile vectors in the existing Qdrant collection."""

    def __init__(self):
        self.client = None
        self.model = None
        self.embedding_dim = settings.BRAND_EMBEDDING_DIMENSION
        self._ensure_client()
        self._ensure_model()
        self._ensure_payload_index()

    # ----------------------------
    # Internal helpers
    # ----------------------------

    def _ensure_client(self):
        if self.client is None:
            try:
                self.client = QdrantManager().get_client()
            except Exception as e:
                raise RuntimeError(f"Qdrant connection failed: {e}") from e

    def _ensure_model(self):
        if self.model is None:
            try:
                self.model = SentenceTransformer(EMBEDDING_MODEL)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
            except Exception as e:
                raise RuntimeError(f"Embedding model load failed: {e}") from e

    def _require_collection(self):
        try:
            if not self.client.collection_exists(COLLECTION_NAME):
                raise RuntimeError(
                    f"Qdrant collection '{COLLECTION_NAME}' not found. Please create it before ingesting profiles."
                )
        except Exception as e:
            # surface connectivity or collection errors cleanly
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Qdrant collection check failed: {e}") from e

    def _ensure_payload_index(self):
        try:
            self._require_collection()
            # Create keyword index for brand_name if missing
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="brand_name",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            # If index exists or creation fails due to existing index, ignore
            pass

    @staticmethod
    def _compose_text(
        brand_name: str,
        brand_website: Optional[str],
        instagram_link: Optional[str],
        brand_logo_url: Optional[str],
        description: Optional[str],
    ) -> str:
        parts = [
            f"Brand name: {brand_name}" if brand_name else "",
            f"Website: {brand_website}" if brand_website else "",
            f"Instagram: {instagram_link}" if instagram_link else "",
            f"Logo: {brand_logo_url}" if brand_logo_url else "",
            f"Description: {description}" if description else "",
        ]
        return " | ".join([p for p in parts if p])

    def _embed(self, text: str) -> List[float]:
        embedding = self.model.encode(text)
        try:
            return embedding.tolist()
        except AttributeError:
            return list(embedding)

    def _get_by_brand(self, brand_name: str) -> Optional[Dict]:
        flt = Filter(must=[FieldCondition(key="brand_name", match=MatchValue(value=brand_name))])
        # Use scroll_filter for compatibility with older qdrant-client versions
        points, _ = self.client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1,
            with_payload=True,
            with_vectors=False,
            scroll_filter=flt,
        )

        if not points:
            return None
        p = points[0]
        payload = p.payload or {}
        return {"id": str(p.id), **payload}

    # ----------------------------
    # Public API
    # ----------------------------

    def upsert_profile(
        self,
        brand_name: str,
        brand_website: Optional[str],
        instagram_link: Optional[str],
        brand_logo_url: Optional[str],
        description: Optional[str],
    ) -> Dict:
        # Ensure dependencies are ready
        self._ensure_client()
        self._ensure_model()
        self._require_collection()

        try:
            existing = self._get_by_brand(brand_name)
            point_id = existing.get("id") if existing else str(uuid.uuid4())
            created_at = existing.get("created_at") if existing else datetime.utcnow().isoformat()
            updated_at = datetime.utcnow().isoformat()

            text = self._compose_text(brand_name, brand_website, instagram_link, brand_logo_url, description)
            vector = self._embed(text)

            payload = {
                "brand_name": brand_name,
                "brand_website": brand_website,
                "instagram_link": instagram_link,
                "brand_logo_url": brand_logo_url,
                "description": description,
                "created_at": created_at,
                "updated_at": updated_at,
            }

            point = PointStruct(id=point_id, vector=vector, payload=payload)
            self.client.upsert(collection_name=COLLECTION_NAME, points=[point])

            return {"id": point_id, **payload}
        except Exception as e:
            raise RuntimeError(f"Failed to upsert profile to Qdrant: {e}") from e

    def list_profiles(self, limit: int = 200) -> List[Dict]:
        self._ensure_client()
        self._require_collection()
        try:
            points, _ = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            return [{"id": p.id, **(p.payload or {})} for p in points]
        except Exception as e:
            raise RuntimeError(f"Failed to list profiles from Qdrant: {e}") from e

    def get_profile(self, brand_name: str) -> Optional[Dict]:
        self._ensure_client()
        self._require_collection()
        try:
            return self._get_by_brand(brand_name)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch profile: {e}") from e


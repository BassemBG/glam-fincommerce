import logging
import uuid
import io
import base64
from typing import Dict, List, Any, Optional
from qdrant_client.models import PointStruct, VectorParams, Distance
from app.core.config import settings
from .qdrant_client import QdrantManager

EMBEDDING_MODEL = settings.BRAND_EMBEDDING_MODEL
# Use separate BrandEmbedding collection for brand products (not clothing_embeddings)
QDRANT_COLLECTION_NAME = "BrandEmbedding"


logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        # Use CLIP for all embeddings (not SentenceTransformer)
        self.embedding_dim = settings.BRAND_EMBEDDING_DIMENSION  # 512 for CLIP
        
        self.qdrant_manager = QdrantManager()
        self.qdrant_client = self.qdrant_manager.get_client()
        self.collection_name = QDRANT_COLLECTION_NAME
        
        # Initialize CLIP model (used for all embeddings now)
        self.clip_model = None
        self.clip_processor = None
        self.clip_device = None
        self._init_clip_model()  # Initialize immediately

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

    # CLIP INITIALIZATION (for product embeddings)

    def _init_clip_model(self):
        """Initialize CLIP model for product image + text embeddings (lazy-loaded)"""
        if self.clip_model is not None:
            return  # Already initialized
        
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            
            model_name = "openai/clip-vit-base-patch32"
            logger.info(f"Loading CLIP model for product embeddings: {model_name}")
            
            self.clip_model = CLIPModel.from_pretrained(model_name)
            self.clip_processor = CLIPProcessor.from_pretrained(model_name)
            self.clip_device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model.to(self.clip_device)
            self.clip_model.eval()
            
            logger.info(f"✅ CLIP model loaded on {self.clip_device} for product embeddings")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            logger.warning("Install transformers and torch: pip install transformers torch pillow")
            self.clip_model = None
    
    def _generate_clip_embedding_for_text(self, text: str) -> Optional[List[float]]:
        """Generate CLIP text embedding for product descriptions"""
        if not self.clip_model or not self.clip_processor:
            self._init_clip_model()
            if not self.clip_model:
                return None
        
        try:
            import torch
            import torch.nn.functional as F
            
            inputs = self.clip_processor(text=[text], return_tensors="pt", padding=True)
            inputs = {k: v.to(self.clip_device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.clip_model.get_text_features(**inputs)

                # Some transformers versions return BaseModelOutputWithPooling
                if hasattr(outputs, "text_embeds"):
                    text_features = outputs.text_embeds
                elif hasattr(outputs, "pooler_output"):
                    text_features = outputs.pooler_output
                elif hasattr(outputs, "last_hidden_state"):
                    text_features = outputs.last_hidden_state
                else:
                    text_features = outputs  # assume tensor

                # Normalize using F.normalize for stability
                text_features = F.normalize(text_features, p=2, dim=-1)
            
            embedding = text_features.cpu().numpy().flatten().tolist()
            logger.debug(f"Generated CLIP text embedding: {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate CLIP text embedding: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_clip_embedding_for_image_url(self, image_url: str) -> Optional[List[float]]:
        """Download and generate CLIP embedding from image URL"""
        if not self.clip_model or not self.clip_processor:
            self._init_clip_model()
            if not self.clip_model:
                return None
        
        try:
            import torch
            import torch.nn.functional as F
            import requests
            from PIL import Image
            
            # Download image from URL
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            
            # Generate CLIP embedding
            inputs = self.clip_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.clip_device) for k, v in inputs.items()}
            
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                # Normalize using F.normalize for stability
                image_features = F.normalize(image_features, p=2, dim=-1)
            
            embedding = image_features.cpu().numpy().flatten().tolist()
            logger.debug(f"Generated CLIP image embedding from URL: {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate CLIP embedding from image URL {image_url}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _combine_embeddings(self, image_embedding: Optional[List[float]], text_embedding: Optional[List[float]]) -> List[float]:
        """
        Combine image and text embeddings
        If both available: average them
        If only one: use that one
        """
        if image_embedding and text_embedding:
            import numpy as np
            combined = (np.array(image_embedding) + np.array(text_embedding)) / 2.0
            return combined.tolist()
        elif image_embedding:
            return image_embedding
        elif text_embedding:
            return text_embedding
        else:
            # Fallback to text embedding of brand + product name
            return [0.0] * 512  # 512-dim CLIP embedding

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
        """Generate embedding for style group using CLIP text embedding"""
        text = self._compose_style_text(style_group, brand_name)
        embedding = self._generate_clip_embedding_for_text(text)
        return embedding if embedding else [0.0] * 512
    
    def embed_product_for_website(
        self,
        brand_name: str,
        product_name: str,
        product_description: str,
        image_url: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding for website product:
        - Try CLIP for image + text combination
        - Fallback to text embedding
        """
        # Try CLIP if image_url provided
        if image_url:
            image_emb = self._generate_clip_embedding_for_image_url(image_url)
            if image_emb:
                text_emb = self._generate_clip_embedding_for_text(f"{brand_name} {product_name} {product_description}")
                return self._combine_embeddings(image_emb, text_emb)
        
        # Fallback: Use CLIP for text-only
        if self.clip_model is None:
            self._init_clip_model()
        
        text_emb = self._generate_clip_embedding_for_text(f"{brand_name} {product_name} {product_description}")
        if text_emb:
            return text_emb

        # Last resort: zero vector with CLIP dimension
        return [0.0] * self.embedding_dim

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
    
    def upsert_product_to_qdrant(
        self,
        brand_name: str,
        product_name: str,
        product_description: str,
        image_url: Optional[str] = None,
        product_url: Optional[str] = None,
        source: str = "website"
    ) -> str:
        """
        Upsert product to Qdrant with CLIP embeddings
        Stores: brand_name, product_name, description, image_url, image_base64, source
        """
        embedding = self.embed_product_for_website(
            brand_name,
            product_name,
            product_description,
            image_url
        )
        
        # Download and encode image as base64 if URL provided
        image_base64 = None
        if image_url:
            try:
                import requests
                from PIL import Image
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                logger.debug(f"✅ Encoded product image as base64: {len(image_base64)} chars")
            except Exception as e:
                logger.warning(f"Could not encode image from {image_url}: {e}")
                image_base64 = None
        
        payload = {
            "brand_name": brand_name,
            "product_name": product_name,
            "product_description": product_description,
            "image_url": image_url,
            "image_base64": image_base64,  # Embedded image
            "product_url": product_url,
            "source": source,
            "embedding_type": "clip" if image_url else "text"
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
        
        logger.info(f"✅ Stored product '{product_name}' from {brand_name} → Qdrant")
        return point_id

    def upsert_brand_styles(self, brand_data: Dict[str, Any], source="extracted") -> List[str]:
        """
        Upsert brand styles from file extraction.
        Converts styles to products for CLIP embedding support.
        Reuses upsert_product_to_qdrant() for consistent embedding handling.
        """
        brand_name = brand_data["brand_name"]
        styles = brand_data["style_groups"]
        point_ids = []

        for style in styles:
            try:
                # Convert style to product format for CLIP embedding support
                product_name = style.get("style_name", "Unknown Style")
                product_description = self._style_to_product_description(style)
                image_url = style.get("image_url")  # If style has image_url, use it
                product_url = style.get("product_url")  # If style has product_url, use it
                
                # Use product embedding function (supports CLIP for images)
                point_id = self.upsert_product_to_qdrant(
                    brand_name=brand_name,
                    product_name=product_name,
                    product_description=product_description,
                    image_url=image_url,
                    product_url=product_url,
                    source=source
                )
                point_ids.append(point_id)
                
            except Exception as e:
                logger.error(f"Failed to upsert style '{style.get('style_name')}' for {brand_name}: {e}")
                continue

        return point_ids

    def _style_to_product_description(self, style: Dict[str, Any]) -> str:
        """
        Convert style data to a rich product description for embedding.
        Combines style_name, product_types, aesthetic_keywords, and other metadata.
        """
        parts = []
        
        if style.get("style_name"):
            parts.append(f"Style: {style['style_name']}")
        
        if style.get("product_types"):
            types_str = ", ".join(style["product_types"])
            parts.append(f"Products: {types_str}")
        
        if style.get("aesthetic_keywords"):
            keywords_str = ", ".join(style["aesthetic_keywords"])
            parts.append(f"Aesthetics: {keywords_str}")
        
        if style.get("target_demographic"):
            parts.append(f"Target: {style['target_demographic']}")
        
        price_range = style.get("price_range")
        if price_range:
            min_p = price_range.get("min_price")
            max_p = price_range.get("max_price")
            if min_p is not None and max_p is not None:
                parts.append(f"Price: ${min_p}-${max_p}")
        
        if style.get("sustainability_score") is not None:
            parts.append(f"Sustainability: {style['sustainability_score']}/100")
        
        return " | ".join(parts) if parts else "Style information"
    
    def upsert_brand_products_from_website(
        self,
        brand_name: str,
        products: List[Dict[str, Any]],
        source: str = "website"
    ) -> List[str]:
        """Upsert multiple products from website crawling"""
        point_ids = []
        
        for product in products:
            try:
                point_id = self.upsert_product_to_qdrant(
                    brand_name=brand_name,
                    product_name=product.get("product_name", "Unknown"),
                    product_description=product.get("description", ""),
                    image_url=product.get("image_url"),
                    product_url=product.get("product_url"),
                    source=source
                )
                point_ids.append(point_id)
            except Exception as e:
                logger.error(f"Failed to upsert product {product.get('product_name')}: {e}")
                continue
        
        logger.info(f"✅ Stored {len(point_ids)} products for {brand_name}")
        return point_ids

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


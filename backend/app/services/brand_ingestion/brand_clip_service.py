"""
Brand Product CLIP Embedding Service
Reuses CLIPQdrantService but with separate BrandEmbedding collection
Keeps clothing embeddings completely isolated
"""

import asyncio
import base64
import io
import logging
import os
import re
import uuid
import warnings
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

from app.core.config import settings
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


class BrandCLIPService:
    """
    Uses CLIP embeddings for brand product ingestion
    Reuses the CLIP model from CLIPQdrantService but with separate collection
    """
    
    def __init__(self):
        """Initialize with CLIPQdrantService CLIP model"""
        try:
            from app.services.clip_qdrant_service import CLIPQdrantService
            
            # Get CLIP model from existing service (reuse CLIP, not collections)
            self.clip_service = CLIPQdrantService()
            self.clip_model = self.clip_service.clip_model
            self.clip_processor = self.clip_service.clip_processor
            self.device = self.clip_service.device
            
            # Create separate Qdrant client for brand products
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            
            self.collection_name = "BrandEmbedding"
            self._initialize_collection()
            
            logger.info(f"BrandCLIPService initialized with CLIP model reuse")
            
        except Exception as e:
            logger.error(f"Failed to initialize BrandCLIPService: {e}")
            self.clip_model = None
            self.clip_processor = None
    
    def _initialize_collection(self):
        """Create BrandEmbedding collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating BrandEmbedding collection...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=512,  # CLIP ViT-B/32 produces 512-dimensional embeddings
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✓ BrandEmbedding collection created")
            else:
                logger.info(f"BrandEmbedding collection already exists")
                
        except Exception as e:
            logger.warning(f"Could not initialize BrandEmbedding collection: {e}")
    
    def generate_text_embedding(self, text: str) -> Optional[List[float]]:
        """Generate CLIP text embedding from brand product description"""
        if not self.clip_model or not self.clip_processor:
            logger.error("CLIP model not initialized")
            return None
        
        try:
            import torch
            
            # Truncate text to max 77 tokens (CLIP limit)
            inputs = self.clip_processor(text=[text], return_tensors="pt", padding=True, truncation=True, max_length=77)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                text_features = self.clip_model.get_text_features(**inputs)
                # Handle BaseModelOutputWithPooling - convert to tensor if needed
                if hasattr(text_features, 'last_hidden_state'):
                    text_features = text_features.pooler_output
                # Normalize manually: text_features shape is (batch_size, 512)
                text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            
            embedding = text_features.cpu().numpy().flatten().tolist()
            logger.debug(f"Generated CLIP text embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate text embedding: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_image_embedding(self, image_url: str) -> Optional[List[float]]:
        """Download and generate CLIP image embedding from URL"""
        if not self.clip_model or not self.clip_processor:
            logger.error("CLIP model not initialized")
            return None
        
        try:
            import torch
            import requests
            from PIL import Image
            
            # Download image from URL
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            
            # Process image
            inputs = self.clip_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                # Handle BaseModelOutputWithPooling - convert to tensor if needed
                if hasattr(image_features, 'last_hidden_state'):
                    image_features = image_features.pooler_output
                # Normalize manually: image_features shape is (batch_size, 512)
                image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            
            embedding = image_features.cpu().numpy().flatten().tolist()
            logger.debug(f"Generated CLIP image embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate image embedding from {image_url}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_image_embedding_from_bytes(self, image_bytes: bytes) -> Optional[List[float]]:
        """Generate CLIP image embedding from raw bytes to avoid double downloads."""
        if not self.clip_model or not self.clip_processor:
            logger.error("CLIP model not initialized")
            return None

        try:
            import torch
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            inputs = self.clip_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                # Handle BaseModelOutputWithPooling - convert to tensor if needed
                if hasattr(image_features, 'last_hidden_state'):
                    image_features = image_features.pooler_output
                image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)

            embedding = image_features.cpu().numpy().flatten().tolist()
            logger.debug(f"Generated CLIP image embedding: {len(embedding)} dimensions (from bytes)")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate image embedding from bytes: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def combine_embeddings(self, image_embedding: Optional[List[float]], text_embedding: Optional[List[float]]) -> Optional[List[float]]:
        """Combine image and text embeddings"""
        if not image_embedding and not text_embedding:
            return None
        
        if image_embedding and text_embedding:
            import numpy as np
            combined = (np.array(image_embedding) + np.array(text_embedding)) / 2.0
            return combined.tolist()
        elif image_embedding:
            return image_embedding
        else:
            return text_embedding
    
    def _slugify(self, value: str, fallback: str = "item") -> str:
        cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return cleaned or fallback

    async def upsert_product(self, brand_name: str, product_name: str, product_description: str,
                      image_url: Optional[str] = None, product_url: Optional[str] = None,
                      product_dict: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate embeddings, upload image to Azure (if configured), and upsert to BrandEmbedding.
        CRITICAL: Must have valid image URL or product is skipped entirely.
        """
        try:
            import mimetypes
            import requests

            # CRITICAL VALIDATION: Skip if NO valid image URL - needed for CLIP embeddings
            if not image_url:
                logger.warning(f"❌ SKIPPING '{product_name}': image_url is None/empty")
                return None
            
            if not isinstance(image_url, str):
                logger.warning(f"❌ SKIPPING '{product_name}': image_url is not a string (type: {type(image_url)})")
                return None
            
            image_url = image_url.strip()
            if not image_url.startswith(("http://", "https://")):
                logger.warning(f"❌ SKIPPING '{product_name}': image_url is not a valid URL: {image_url[:50]}")
                return None

            logger.info(f"✅ Processing '{product_name}' with image: {image_url[:60]}...")

            point_id = str(uuid.uuid4().int)[:18]  # Qdrant requires integer IDs
            brand_slug = self._slugify(brand_name, "brand")
            product_slug = self._slugify(product_name, "product")

            image_bytes = None
            image_embedding = None
            uploaded_url: Optional[str] = None
            image_base64: Optional[str] = None
            content_type = "application/octet-stream"

            # Fetch image once and reuse for embedding + upload
            if image_url:
                import time
                max_retries = 3
                retry_delay = 2
                
                for attempt in range(max_retries):
                    try:
                        response = requests.get(image_url, timeout=15, verify=False)  # Skip SSL cert check for Tunisia site
                        response.raise_for_status()
                        image_bytes = response.content
                        content_type = response.headers.get("Content-Type") or content_type
                        logger.info(f"✓ Downloaded image: {len(image_bytes)} bytes from {image_url}")
                        break  # Success, exit retry loop
                    except requests.exceptions.RequestException as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Image download attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 1.5  # Exponential backoff
                        else:
                            logger.warning(f"Could not download image after {max_retries} attempts: {e}")
                            return None  # Skip product if image download fails

            # Generate embeddings
            text_embedding = self.generate_text_embedding(f"{brand_name} {product_name} {product_description}")
            if image_bytes:
                image_embedding = self.generate_image_embedding_from_bytes(image_bytes)
                if image_embedding:
                    logger.info(f"✓ Generated image embedding: {len(image_embedding)} dims")
                else:
                    logger.warning(f"⚠️ Failed to generate image embedding for {product_name}")
            else:
                logger.warning(f"⚠️ No image bytes available for {product_name}")

            embedding = self.combine_embeddings(image_embedding, text_embedding)
            if not embedding:
                logger.warning(f"Could not generate any embedding for {product_name}")
                embedding = [0.0] * 512

            # Encode and upload image (Azure preferred)
            if image_bytes:
                try:
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                except Exception as e:
                    logger.warning(f"Could not base64-encode image: {e}")
                    image_base64 = None

                try:
                    parsed = urlparse(image_url)
                    ext = os.path.splitext(parsed.path)[1] or mimetypes.guess_extension(content_type) or ".jpg"
                    file_name = f"brands/{brand_slug}/{product_slug}-{point_id}{ext}"
                    
                    # Await storage upload using existing event loop
                    try:
                        uploaded_url = await asyncio.wait_for(
                            storage_service.upload_file(image_bytes, file_name, content_type),
                            timeout=30.0
                        )
                        if uploaded_url:
                            logger.info(f"✓ Uploaded to Azure: {uploaded_url}")
                    except asyncio.TimeoutError:
                        logger.error(f"Azure upload timed out (30s). Using local fallback.")
                        uploaded_url = None
                    except Exception as e:
                        logger.error(f"Async upload failed: {e}")
                        uploaded_url = None
                except Exception as e:
                    logger.error(f"Image upload exception: {e}")
                    import traceback
                    traceback.print_exc()
                    uploaded_url = None

            payload = {
                "brand_name": brand_name,
                "product_name": product_name,
                "product_description": product_description,
                "azure_image_url": uploaded_url,  # Azure/local storage URL
                "image_base64": image_base64,
                "source": "website",
                "storage": "azure" if uploaded_url else "source",
                "embedding_type": "clip"
            }

            # Include raw image embedding in payload when available
            if image_embedding and len(image_embedding) == 512:
                payload["image_embedding"] = image_embedding
                logger.info(f"✓ Storing image_embedding in payload (512 dims)")
            else:
                logger.warning(f"⚠️ No valid image_embedding to store (image_embedding={'None' if not image_embedding else f'{len(image_embedding)} dims'})")

            # Propagate Azure URL back to caller for response rendering (omit original URL)
            if product_dict is not None:
                product_dict["azure_image_url"] = uploaded_url

            point = PointStruct(
                id=int(point_id),
                vector=embedding,
                payload=payload
            )

            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )

            logger.info(f"✓ Upserted product: {brand_name} - {product_name} (ID: {point_id})")
            return point_id

        except Exception as e:
            logger.error(f"Failed to upsert product: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def upsert_products_batch(self, brand_name: str, products: List[Dict[str, Any]]) -> List[str]:
        """Upsert multiple products - STRICT: skip any without images"""
        point_ids = []
        skipped = 0
        
        # Filter out products without images BEFORE processing
        products_with_images = []
        for product in products:
            image_url = product.get("image_url", "").strip() if product.get("image_url") else ""
            if not image_url or not image_url.startswith(("http://", "https://")):
                logger.warning(f"⏭️  SKIPPING (no image): {product.get('product_name', 'Unknown')}")
                skipped += 1
            else:
                products_with_images.append(product)
        
        logger.info(f"📦 Processing {len(products_with_images)}/{len(products)} products with images ({skipped} without images)")
        
        for product in products_with_images:
            try:
                point_id = await self.upsert_product(
                    brand_name=brand_name,
                    product_name=product.get("product_name", ""),
                    product_description=product.get("description", ""),
                    image_url=product.get("image_url"),
                    product_url=product.get("product_url"),
                    product_dict=product
                )
                if point_id:
                    point_ids.append(point_id)
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Failed to upsert product {product.get('product_name')}: {e}")
                skipped += 1
        
        logger.info(f"✅ Successfully stored {len(point_ids)} products ({skipped} skipped)")
        return point_ids

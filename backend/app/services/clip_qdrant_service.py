"""
CLIP-based Qdrant Vector Database Integration Service
Uses CLIP embeddings for visual similarity search with image storage
"""

import logging
import base64
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, PayloadSchemaType
from app.core.config import settings
import numpy as np

logger = logging.getLogger(__name__)

class CLIPQdrantService:
    """
    Manages Qdrant operations using CLIP embeddings for clothing items
    Features:
    - CLIP visual embeddings (512 dimensions)
    - Image storage (base64 encoded)
    - Image-to-image search
    - Text-to-image search
    - All existing metadata preserved
    """
    
    def __init__(self):
        """Initialize Qdrant client and CLIP model"""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            self.collection_name = "clothing_clip_embeddings"  # New collection name
            logger.info(f"Connected to Qdrant at {settings.QDRANT_URL}")
            
            # Initialize CLIP model
            self._initialize_clip_model()
            
            # Initialize collection if it doesn't exist
            self._initialize_collection()
            
            # Initialize outfits collection if it doesn't exist
            self.outfits_collection_name = "outfits_clip_embeddings"
            self._initialize_outfits_collection()
            
        except Exception as e:
            logger.error(f"Failed to initialize CLIP Qdrant: {e}")
            self.client = None
            self.clip_model = None
            self.clip_processor = None
    
    def _initialize_clip_model(self):
        """Initialize CLIP model for embeddings"""
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            
            # Use OpenAI's CLIP model
            model_name = "openai/clip-vit-base-patch32"
            logger.info(f"Loading CLIP model: {model_name}")
            
            self.clip_model = CLIPModel.from_pretrained(model_name)
            self.clip_processor = CLIPProcessor.from_pretrained(model_name)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model.to(self.device)
            self.clip_model.eval()
            
            logger.info(f"✓ CLIP model loaded on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            logger.warning("Install transformers and torch: pip install transformers torch pillow")
            self.clip_model = None
            self.clip_processor = None
    
    def _initialize_collection(self):
        """Create collection with CLIP embedding dimensions if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating CLIP collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=512,  # CLIP ViT-B/32 produces 512-dimensional embeddings
                        distance=Distance.COSINE  # Cosine similarity for CLIP
                    )
                )
                logger.info(f"✓ CLIP collection created: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
            
            # Ensure payload index for user_id
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            
            # Ensure payload indexes for filtered search fields (required by some Qdrant Cloud setups)
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="clothing.category",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="clothing.colors",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            
            logger.info("✓ Payload indexes for user_id, category, and colors ensured")

        except Exception as e:
            logger.warning(f"Could not initialize collection or indexes: {e}")

                
    def _initialize_outfits_collection(self):
        """Create outfits collection with CLIP embedding dimensions if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.outfits_collection_name not in collection_names:
                logger.info(f"Creating outfits CLIP collection: {self.outfits_collection_name}")
                self.client.create_collection(
                    collection_name=self.outfits_collection_name,
                    vectors_config=VectorParams(
                        size=512,
                        distance=Distance.COSINE
                    )
                )
            
            # Ensure payload index for user_id
            self.client.create_payload_index(
                collection_name=self.outfits_collection_name,
                field_name="user_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            
            logger.info(f"✓ Outfits CLIP collection ensured: {self.outfits_collection_name}")
                
        except Exception as e:
            logger.warning(f"Could not initialize outfits collection: {e}")

    def generate_image_embedding(self, image_data: bytes) -> List[float]:
        """
        Generate CLIP embedding from image bytes
        
        Args:
            image_data: Raw image bytes (JPEG, PNG, etc.)
            
        Returns:
            512-dimensional CLIP embedding vector
        """
        if not self.clip_model or not self.clip_processor:
            raise ValueError("CLIP model not initialized")
        
        try:
            from PIL import Image
            import io
            import torch
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            
            # Process image
            inputs = self.clip_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate embedding
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                # Normalize the features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Convert to list
            embedding = image_features.cpu().numpy().flatten().tolist()
            
            logger.info(f"Generated CLIP embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate CLIP embedding: {e}")
            raise
    
    def generate_text_embedding(self, text: str) -> List[float]:
        """
        Generate CLIP embedding from text query
        Enables text-to-image search
        
        Args:
            text: Search query text (e.g., "red summer dress")
            
        Returns:
            512-dimensional CLIP embedding vector
        """
        if not self.clip_model or not self.clip_processor:
            raise ValueError("CLIP model not initialized")
        
        try:
            import torch
            
            # Process text
            inputs = self.clip_processor(text=[text], return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate embedding
            with torch.no_grad():
                text_features = self.clip_model.get_text_features(**inputs)
                # Normalize the features
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            # Convert to list
            embedding = text_features.cpu().numpy().flatten().tolist()
            
            logger.info(f"Generated text CLIP embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate text CLIP embedding: {e}")
            raise
    
    async def store_clothing_with_image(
        self,
        point_id: str,
        image_data: bytes,
        clothing_analysis: Dict[str, Any],
        brand_info: Dict[str, Any],
        user_id: str,
        price: Optional[float] = None,
        image_url: Optional[str] = None
    ) -> bool:
        """
        Store clothing item with CLIP embedding and image
        
        Args:
            point_id: Unique identifier
            image_data: Original clothing image bytes
            clothing_analysis: Clothing attributes from analysis
            brand_info: Brand detection results
            user_id: User identifier
            price: Item price
            image_url: Optional persistent URL (e.g. Azure Blob)
            
        Returns:
            True if successful
        """
        if not self.client:
            logger.error("Qdrant client not initialized")
            return False
        
        try:
            # Generate CLIP embedding from image
            logger.info("Generating CLIP embedding from image...")
            embeddings = self.generate_image_embedding(image_data)
            
            # Encode image as base64 for storage (as fallback/backup)
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create metadata payload with image
            metadata = {
                "user_id": user_id,
                "clothing": clothing_analysis,
                "brand": brand_info.get("detected_brand", "Unknown"),
                "brand_confidence": brand_info.get("brand_confidence", 0),
                "price": price,
                "price_range": brand_info.get("price_range"),
                "image_url": image_url,  # Store the persistent URL!
                "image_base64": image_base64,  # Keep base64 as backup
                "image_size_kb": len(image_data) / 1024,
                "embedding_type": "clip-vit-base-patch32",
                "ingested_at": __import__('datetime').datetime.now().isoformat()
            }
            
            # Create point
            point = PointStruct(
                id=hash(point_id) % (10 ** 9),
                vector=embeddings,
                payload=metadata
            )
            
            # Upsert the point
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"✓ Stored clothing with CLIP embedding and image: {point_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store clothing with image: {e}")
            return False
    
    async def search_similar_clothing_by_image(
        self,
        image_data: bytes,
        user_id: str,
        category: Optional[str] = None,
        color: Optional[str] = None,
        vibe: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.35  # Lowered from 0.5 to allow similar models with different colors
    ) -> List[Dict[str, Any]]:
        """
        Find similar clothing items using image similarity (CLIP)
        
        Args:
            image_data: Query image bytes
            user_id: Filter results to specific user
            category: Optional category filter
            color: Optional color filter
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of similar clothing items with images
        """
        if not self.client:
            logger.error("Qdrant client not initialized")
            return []
        
        try:
            # Generate CLIP embedding from query image
            query_embedding = self.generate_image_embedding(image_data)
            
            # Build filter conditions
            must_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]
            
            if category:
                must_conditions.append(FieldCondition(key="clothing.category", match=MatchValue(value=category)))
            if color:
                must_conditions.append(FieldCondition(key="clothing.colors", match=MatchValue(value=color)))
            if vibe:
                must_conditions.append(FieldCondition(key="clothing.vibe", match=MatchValue(value=vibe)))
            if season:
                must_conditions.append(FieldCondition(key="clothing.season", match=MatchValue(value=season)))
            
            # Search with filters
            print(f"🔍 [Qdrant Search] Querying for user_id={user_id} with threshold={min_score}")
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=Filter(must=must_conditions),
                limit=limit,
                score_threshold=min_score
            )
            
            print(f"🔍 [Qdrant Result] Found {len(results)} matches.")
            if results:
                print(f"   -> Top Match: ID={results[0].id}, Score={results[0].score}")
            else:
                print(f"   -> No matches found above {min_score}")
                
            # Convert results to readable format
            similar_items = []
            for result in results:
                item = {
                    "id": result.id,
                    "score": result.score,
                    "clothing": result.payload.get("clothing", {}),
                    "brand": result.payload.get("brand"),
                    "price": result.payload.get("price"),
                    "image_base64": result.payload.get("image_base64"),  # Include image!
                    "embedding_type": result.payload.get("embedding_type")
                }
                similar_items.append(item)
            
            logger.info(f"Found {len(similar_items)} similar items for user {user_id}")
            return similar_items
            
        except Exception as e:
            logger.error(f"Image search failed: {e}")
            if hasattr(e, 'content'):
                logger.error(f"Raw response content: {e.content}")
            return []
    
    async def search_by_text(
        self,
        query_text: str,
        user_id: str,
        category: Optional[str] = None,
        color: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.05  # Text-to-image similarity is typically lower (0.1-0.3)
    ) -> List[Dict[str, Any]]:
        """
        Search clothing items using text query (CLIP text-to-image)
        
        Args:
            query_text: Search text (e.g., "red summer dress")
            user_id: Filter results to specific user
            category: Optional category filter
            color: Optional color filter
            limit: Maximum number of results
            min_score: Minimum similarity score
            
        Returns:
            List of matching clothing items with images
        """
        if not self.client:
            logger.error("Qdrant client not initialized")
            return []
        
        try:
            # Generate CLIP text embedding
            query_embedding = self.generate_text_embedding(query_text)
            
            # Build filter conditions
            must_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]
            
            if category:
                must_conditions.append(FieldCondition(key="clothing.category", match=MatchValue(value=category)))
            if color:
                must_conditions.append(FieldCondition(key="clothing.colors", match=MatchValue(value=color)))
            
            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=Filter(must=must_conditions),
                limit=limit,
                score_threshold=min_score
            )
            
            # Convert results
            items = []
            for result in results:
                item = {
                    "id": result.id,
                    "score": result.score,
                    "clothing": result.payload.get("clothing", {}),
                    "brand": result.payload.get("brand"),
                    "price": result.payload.get("price"),
                    "image_base64": result.payload.get("image_base64")
                }
                items.append(item)
            
            logger.info(f"Found {len(items)} items matching '{query_text}'")
            return items
            
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the CLIP collection"""
        if not self.client:
            return {"error": "Qdrant not initialized"}
        
        try:
            stats = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": stats.points_count,
                "vectors_count": stats.vectors_count,
                "embedding_type": "CLIP (openai/clip-vit-base-patch32)",
                "vector_size": 512,
                "status": stats.status
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    async def get_user_items(
        self,
        user_id: str,
        limit: int = 100,
        offset: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Get all clothing items for a user from Qdrant
        
        Args:
            user_id: User identifier
            limit: batch size
            offset: pagination offset
        
        Returns:
            Dict containing items list and next_page offset
        """
        if not self.client:
            logger.error("Qdrant client not initialized")
            return {"items": [], "next_page": None}
            
        try:
            # Build filter conditions
            must_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]
            
            # Scroll (fetch items)
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(must=must_conditions),
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            items = []
            for point in points:
                # Default empty if payload is missing
                payload = point.payload or {}
                
                # Prioritize persistent URL, fallback to data URI
                image_url = payload.get("image_url")
                if not image_url and payload.get("image_base64"):
                    image_url = f"data:image/jpeg;base64,{payload.get('image_base64')}"
                
                item = {
                    "id": str(point.id),
                    "clothing": payload.get("clothing", {}),
                    "brand": payload.get("brand"),
                    "price": payload.get("price"),
                    "image_base64": payload.get("image_base64"),
                    "image_url": image_url,
                    "ingested_at": payload.get("ingested_at")
                }
                items.append(item)
                
            return {
                "items": items,
                "next_page": next_offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get user items: {e}")
            return {"items": [], "next_page": None}

    async def delete_item(self, point_id: str) -> bool:
        """
        Delete an item from Qdrant by its Point ID.
        """
        if not self.client:
            return False
            
        try:
            # Qdrant IDs are stored as integers in this setup
            # Try converting to int, if fails assume it's a UUID string (unlikely given current setup)
            try:
                qdrant_id = int(point_id)
            except ValueError:
                qdrant_id = point_id

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[qdrant_id]
            )
            logger.info(f"Deleted item {point_id} from Qdrant")
            return True
        except Exception as e:
            logger.error(f"Failed to delete item {point_id}: {e}")
            return False


    async def store_outfit_with_image(
        self,
        outfit_id: str,
        image_data: bytes,
        outfit_data: Dict[str, Any],
        user_id: str,
        image_url: Optional[str] = None
    ) -> bool:
        """
        Store generated outfit with CLIP embedding and visualization
        
        Args:
            outfit_id: Unique identifier
            image_data: Generated outfit visualization bytes
            outfit_data: Outfit metadata (name, description, items, reasoning, score)
            user_id: User identifier
            
        Returns:
            True if successful
        """
        if not self.client:
            logger.error("Qdrant client not initialized")
            return False
        
        try:
            # Generate CLIP embedding from the generated visualization
            logger.info("Generating CLIP embedding from outfit image...")
            embeddings = self.generate_image_embedding(image_data)
            
            # Encode image as base64 for storage
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create metadata payload
            metadata = {
                "user_id": user_id,
                "outfit_id": outfit_id,
                "name": outfit_data.get("name"),
                "description": outfit_data.get("description"),
                "items": outfit_data.get("items", []),
                "reasoning": outfit_data.get("reasoning"),
                "score": outfit_data.get("score"),
                "style_tags": outfit_data.get("style_tags", []),
                "image_url": image_url,  # Store the persistent URL
                "image_base64": image_base64,
                "image_size_kb": len(image_data) / 1024,
                "embedding_type": "clip-vit-base-patch32",
                "stored_at": __import__('datetime').datetime.now().isoformat()
            }
            
            # Create point (use generic ID logic)
            import uuid
            try:
                # If outfit_id is a UUID string, it might not hash well to an int for Qdrant if not handled carefully
                # Qdrant accepts strings/UUIDs as IDs now, but let's stick to a consistent format
                qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"outfit-{outfit_id}"))
            except Exception:
                qdrant_id = str(uuid.uuid4())
            
            point = PointStruct(
                id=qdrant_id,
                vector=embeddings,
                payload=metadata
            )
            
            # Upsert the point
            self.client.upsert(
                collection_name=self.outfits_collection_name,
                points=[point]
            )
            
            logger.info(f"✓ Stored outfit with CLIP embedding and image: {outfit_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store outfit with image: {e}")
            return False

    async def get_items_by_ids(self, point_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve specific clothing items from Qdrant by their IDs
        """
        if not self.client:
            return []
            
        try:
            # Qdrant retrieve by IDs
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[int(pid) if pid.isdigit() else pid for pid in point_ids],
                with_payload=True,
                with_vectors=False
            )
            
            items = []
            for point in points:
                payload = point.payload or {}
                # Prioritize persistent URL, fallback to data URI
                image_url = payload.get("image_url")
                if not image_url and payload.get("image_base64"):
                    image_url = f"data:image/jpeg;base64,{payload.get('image_base64')}"
                
                items.append({
                    "id": str(point.id),
                    "clothing": payload.get("clothing", {}),
                    "brand": payload.get("brand"),
                    "price": payload.get("price"),
                    "image_base64": payload.get("image_base64"),
                    "category": payload.get("clothing", {}).get("category"),
                    "sub_category": payload.get("clothing", {}).get("sub_category"),
                    "body_region": payload.get("clothing", {}).get("body_region"),
                    "image_url": image_url
                })
            return items
        except Exception as e:
            logger.error(f"Failed to retrieve items by IDs: {e}")
            return []

    async def get_user_outfits(
        self,
        user_id: str,
        limit: int = 50,
        offset: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Get all outfits for a user from Qdrant
        """
        if not self.client:
            return {"items": [], "next_page": None}
            
        try:
            must_conditions = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]
            
            points, next_offset = self.client.scroll(
                collection_name=self.outfits_collection_name,
                scroll_filter=Filter(must=must_conditions),
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            outfits = []
            for point in points:
                # Prioritize persistent URL, fallback to data URI
                image_url = payload.get("image_url")
                if not image_url and payload.get("image_base64"):
                    image_url = f"data:image/jpeg;base64,{payload.get('image_base64')}"

                outfits.append({
                    "id": str(point.id),
                    "outfit_id": payload.get("outfit_id"),
                    "name": payload.get("name"),
                    "description": payload.get("description"),
                    "items": payload.get("items", []),
                    "reasoning": payload.get("reasoning"),
                    "score": payload.get("score"),
                    "style_tags": payload.get("style_tags", []),
                    "image_base64": payload.get("image_base64"),
                    "image_url": image_url,
                    "tryon_image_url": image_url,  # Alias for frontend compatibility
                    "stored_at": payload.get("stored_at")
                })
                
            return {
                "items": outfits,
                "next_page": next_offset
            }
        except Exception as e:
            logger.error(f"Failed to get user outfits: {e}")
            return {"items": [], "next_page": None}

    async def get_outfit_by_id(self, outfit_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single outfit from Qdrant by its original DB ID
        """
        if not self.client:
            return None
            
        try:
            import uuid
            # Deterministically calculate the Qdrant Point ID used in store_outfit_with_image
            qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"outfit-{outfit_id}"))
            
            points = self.client.retrieve(
                collection_name=self.outfits_collection_name,
                ids=[qdrant_id],
                with_payload=True,
                with_vectors=False
            )
            
            if not points:
                # If deterministic hash fails (maybe it was a uuid4 fallback), search by payload
                results = self.client.search(
                    collection_name=self.outfits_collection_name,
                    query_vector=[0.0] * 512, # Dummy vector for filter-only search
                    query_filter=Filter(must=[FieldCondition(key="outfit_id", match=MatchValue(value=outfit_id))]),
                    limit=1
                )
                if not results:
                    return None
                payload = results[0].payload
                point_id = results[0].id
            else:
                payload = points[0].payload
                point_id = points[0].id
                
            # Prioritize persistent URL, fallback to data URI
            image_url = payload.get("image_url")
            if not image_url and payload.get("image_base64"):
                image_url = f"data:image/jpeg;base64,{payload.get('image_base64')}"

            return {
                "id": str(point_id),
                "outfit_id": payload.get("outfit_id"),
                "name": payload.get("name"),
                "description": payload.get("description"),
                "items": payload.get("items", []),
                "reasoning": payload.get("reasoning"),
                "score": payload.get("score"),
                "style_tags": payload.get("style_tags", []),
                "image_base64": payload.get("image_base64"),
                "image_url": image_url,
                "tryon_image_url": image_url  # Alias for frontend compatibility
            }
        except Exception as e:
            logger.error(f"Failed to retrieve outfit by ID: {e}")
            return None

# Global instance
clip_qdrant_service = CLIPQdrantService()

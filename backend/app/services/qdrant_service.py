"""
Qdrant Vector Database Integration Service
Handles embedding storage and semantic search for clothing items
"""

import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

from qdrant_client.http.models import SearchRequest


logger = logging.getLogger(__name__)

class QdrantService:
    """Manages all Qdrant operations for clothing embeddings"""
    
    def __init__(self):
        """Initialize Qdrant client"""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            self.collection_name = settings.QDRANT_COLLECTION_NAME
            logger.info(f"Connected to Qdrant at {settings.QDRANT_URL}")
            
            # Initialize collection if it doesn't exist
            self._initialize_collection()
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            self.client = None
    
    def _initialize_collection(self):
        """Create collection if it doesn't exist"""
        try:
            # Try to get collection info
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Size of embeddings (768 dimensions)
                        distance=Distance.COSINE  # Cosine distance for semantic similarity
                    )
                )
                logger.info(f"✓ Collection created: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
                
        except Exception as e:
            logger.warning(f"Could not initialize collection: {e}")
    
    async def store_embedding(
        self,
        point_id: str,
        embeddings: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store a clothing embedding with metadata
        
        Args:
            point_id: Unique identifier for the point
            embeddings: Vector embedding (768 dimensions)
            metadata: Clothing metadata and analysis results
            
        Returns:
            True if successful, False otherwise
        """
        
        if not self.client:
            logger.error("Qdrant client not initialized")
            return False
        
        try:
            # Create point with embeddings and payload
            point = PointStruct(
                id=hash(point_id) % (10 ** 9),  # Convert to uint64
                vector=embeddings,
                payload=metadata
            )
            
            # Upsert the point (insert or update)
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"✓ Stored embedding for {point_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            return False
    
    async def search_similar_clothing(
        self,
        embeddings: List[float],
        user_id: str,
        limit: int = 10,
        min_score: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Find similar clothing items using semantic search
        
        Args:
            embeddings: Query embedding vector
            user_id: Filter results to specific user
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of similar clothing items with scores
        """
        
        if not self.client:
            logger.error("Qdrant client not initialized")
            return []
        
        try:

            
            # Search with filter for user_id
            results = qdrant_service.client.http.post(
                collection_name=self.collection_name,
                query_vector=embeddings,
                query_filter={
                    "must": [
                        {
                            "key": "user_id",
                            "match": {"value": user_id}
                        }
                    ]
                },
                limit=limit,
                score_threshold=min_score
            )
            
            # Convert results to readable format
            similar_items = []
            for result in results:
                similar_items.append({
                    "id": result.id,
                    "score": result.score,
                    "clothing": result.payload.get("clothing", {}),
                    "brand": result.payload.get("brand"),
                    "price": result.payload.get("price"),
                    "image_url": result.payload.get("image_url")
                })
            
            logger.info(f"Found {len(similar_items)} similar items for user {user_id}")
            return similar_items
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def search_by_attributes(
        self,
        user_id: str,
        category: Optional[str] = None,
        color: Optional[str] = None,
        vibe: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find clothing items by attributes (filters)
        
        Args:
            user_id: Filter by user
            category: Filter by category (clothing, shoes, accessory)
            color: Filter by color
            vibe: Filter by vibe (chic, casual, etc.)
            season: Filter by season
            limit: Maximum results
            
        Returns:
            List of matching items
            
        Note: Body type filtering is kept as independent for future integration
        """
        
        if not self.client:
            logger.error("Qdrant client not initialized")
            return []
        
        try:
            # Build filter conditions
            must_conditions = [
                {"key": "user_id", "match": {"value": user_id}}
            ]
            
            if category:
                must_conditions.append({
                    "key": "clothing.category",
                    "match": {"value": category}
                })
            
            if color:
                must_conditions.append({
                    "key": "clothing.colors",
                    "match": {"value": color}
                })
            
            if vibe:
                must_conditions.append({
                    "key": "clothing.vibe",
                    "match": {"value": vibe}
                })
            
            if season:
                must_conditions.append({
                    "key": "clothing.season",
                    "match": {"value": season}
                })
            
            # Note: body_type filtering removed - kept as independent for future integration
            
            # Scroll through collection with filters
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                query_filter={"must": must_conditions}
            )
            
            items = []
            for point in results:
                items.append({
                    "id": point.id,
                    "clothing": point.payload.get("clothing", {}),
                    "brand": point.payload.get("brand"),
                    "price": point.payload.get("price"),
                    "image_url": point.payload.get("image_url")
                })
            
            logger.info(f"Found {len(items)} items matching filters")
            return items
            
        except Exception as e:
            logger.error(f"Attribute search failed: {e}")
            return []
    
    async def delete_embedding(self, point_id: str) -> bool:
        """Delete an embedding from Qdrant"""
        
        if not self.client:
            logger.error("Qdrant client not initialized")
            return False
        
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector={
                    "ids": [hash(point_id) % (10 ** 9)]
                }
            )
            logger.info(f"✓ Deleted embedding: {point_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        
        if not self.client:
            return {"error": "Qdrant not initialized"}
        
        try:
            stats = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": stats.points_count,
                "vectors_count": stats.vectors_count,
                "status": stats.status
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


# Global instance
qdrant_service = QdrantService()

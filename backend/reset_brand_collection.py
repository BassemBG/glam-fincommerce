"""
Reset BrandEmbedding collection to use 512-dim CLIP embeddings
Run this once to migrate from 384-dim FastEmbed to 512-dim CLIP
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings

def reset_brand_collection():
    """Delete and recreate BrandEmbedding with correct dimensions"""
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
    
    collection_name = "BrandEmbedding"
    
    # Check if collection exists
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    
    if collection_name in collection_names:
        print(f"🗑️  Deleting existing {collection_name} collection...")
        client.delete_collection(collection_name)
        print(f"✓ Deleted")
    
    # Recreate with 512 dimensions for CLIP
    print(f"🔨 Creating {collection_name} with 512 dimensions (CLIP)...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=512,  # CLIP ViT-B/32
            distance=Distance.COSINE
        )
    )
    print(f"✓ Created {collection_name} collection with CLIP dimensions")
    
    # Verify
    info = client.get_collection(collection_name)
    print(f"\n✅ Collection ready:")
    print(f"   - Name: {info.config.params.vectors.size}")
    print(f"   - Dimensions: {info.config.params.vectors.size}")
    print(f"   - Distance: {info.config.params.vectors.distance}")
    print(f"   - Points: {info.points_count}")

if __name__ == "__main__":
    reset_brand_collection()

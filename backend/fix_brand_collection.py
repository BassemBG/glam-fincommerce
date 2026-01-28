"""
Fix BrandEmbedding collection dimension mismatch
Recreates the collection with 512 dimensions to match CLIP embeddings
"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

load_dotenv()

def fix_brand_collection():
    """Recreate BrandEmbedding collection with correct dimensions (512)"""
    
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    print(f"🔗 Connecting to Qdrant at {qdrant_url}...")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
    
    collection_name = "BrandEmbedding"
    
    try:
        # Check if collection exists
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if collection_name in collection_names:
            # Get current collection info
            info = client.get_collection(collection_name)
            current_size = info.config.params.vectors.size
            print(f"📊 Current collection: {collection_name}")
            print(f"   Vector size: {current_size} (should be 512 for CLIP)")
            print(f"   Points: {info.points_count}")
            
            if current_size == 512:
                print("✅ Collection already has correct dimensions (512)")
                return
            
            print(f"\n⚠️  Collection has wrong dimensions ({current_size} instead of 512)")
            print(f"   Recreating with 512 dimensions...")
        
        # Recreate collection with correct dimensions
        print(f"🔧 Creating {collection_name} collection with 512 dimensions...")
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=512,  # CLIP ViT-B/32 produces 512-dimensional embeddings
                distance=Distance.COSINE
            )
        )
        
        print(f"✅ Collection '{collection_name}' created successfully!")
        print(f"   Vector size: 512 (matches CLIP)")
        print(f"   Distance: COSINE")
        print("\n💡 You can now re-run brand ingestion: POST /api/v1/brands/ingest")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    fix_brand_collection()

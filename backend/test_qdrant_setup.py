"""
🧪 Qdrant Setup Test Script
Tests Qdrant connection, collection creation, and basic operations
"""

import asyncio
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.models import SearchRequest




from app.core.config import settings
from app.services.qdrant_service import qdrant_service

def test_connection():
    """Test 1: Check if Qdrant is accessible"""
    print("\n" + "="*70)
    print("🧪 TEST 1: QDRANT CONNECTION")
    print("="*70)
    
    try:
        client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        collections = client.get_collections()
        print(f"✅ Connected to Qdrant at {settings.QDRANT_URL}")
        print(f"   Found {len(collections.collections)} collection(s)")
        return True
    except Exception as e:
        print(f"❌ Cannot connect to Qdrant: {e}")
        print(f"\n💡 Make sure Qdrant is running:")
        print(f"   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")
        return False

def test_collection_exists():
    """Test 2: Check if collection exists"""
    print("\n" + "="*70)
    print("🧪 TEST 2: COLLECTION CHECK")
    print("="*70)
    
    try:
        client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if settings.QDRANT_COLLECTION_NAME in collection_names:
            print(f"✅ Collection '{settings.QDRANT_COLLECTION_NAME}' exists")
            collection_info = client.get_collection(settings.QDRANT_COLLECTION_NAME)
            vectors_config = collection_info.config.params.vectors
            print(f"   Vector size: {vectors_config.size}")
            print(f"   Distance: {vectors_config.distance}")
            # Points count via client.count
            count = client.count(settings.QDRANT_COLLECTION_NAME).count
            print(f"   Points count: {count}")
            return True
        else:
            print(f"⚠️ Collection '{settings.QDRANT_COLLECTION_NAME}' not found")
            print("   It will be created automatically during ingestion")
            return False
    except Exception as e:
        print(f"❌ Error checking collection: {e}")
        return False

def test_create_collection_manual():
    """Test 3: Manually create collection"""
    print("\n" + "="*70)
    print("🧪 TEST 3: MANUAL COLLECTION CREATION")
    print("="*70)
    
    try:
        client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if settings.QDRANT_COLLECTION_NAME in collection_names:
            print("✅ Collection already exists, skipping creation")
            return True
        
        print(f"Creating collection: {settings.QDRANT_COLLECTION_NAME}")
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            )
        )
        print("✅ Collection created successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create collection: {e}")
        return False

async def test_store_and_search():
    """Test 4: Store a test embedding and search"""
    print("\n" + "="*70)
    print("🧪 TEST 4: STORE & SEARCH")
    print("="*70)
    
    if not qdrant_service.client:
        print("❌ Qdrant service not initialized")
        return False
    
    try:
        # Create a test embedding (768 dimensions)
        test_embedding = [0.1] * 768
        test_metadata = {
            "user_id": "test-user",
            "clothing": {
                "category": "clothing",
                "sub_category": "Test T-shirt",
                "colors": ["blue"],
                "vibe": "casual"
            },
            "brand": "Test Brand",
            "price": 50.0,
            "price_range": "mid-range"
        }
        
        print("📤 Storing test embedding...")
        success = await qdrant_service.store_embedding(
            point_id="test-point-123",
            embeddings=test_embedding,
            metadata=test_metadata
        )
        if success:
            print("✅ Test embedding stored successfully!")
            
            # Use new search_points API
            print("\n🔍 Testing semantic search...")
            results = qdrant_service.client.http.post(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=test_embedding,
                limit=5,
            )
            print(f"✅ Found {len(results)} similar items")
            if results:
                top_score = results[0].score if results[0].score else 0
                print(f"   Top result score: {top_score:.4f}")
            return True
        else:
            print("❌ Failed to store embedding")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_collection_stats():
    """Test 5: Get collection statistics"""
    print("\n" + "="*70)
    print("🧪 TEST 5: COLLECTION STATISTICS")
    print("="*70)
    
    try:
        count = qdrant_service.client.count(settings.QDRANT_COLLECTION_NAME).count
        print("✅ Collection Statistics:")
        print(f"   Name: {settings.QDRANT_COLLECTION_NAME}")
        print(f"   Points: {count}")
        return True
    except Exception as e:
        print(f"❌ Error fetching stats: {e}")
        return False

async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 QDRANT SETUP TEST SUITE")
    print("="*70)
    
    print("\n📋 Configuration:")
    print(f"   QDRANT_URL: {settings.QDRANT_URL}")
    print(f"   Collection: {settings.QDRANT_COLLECTION_NAME}")
    print(f"   API Key: {'Set' if settings.QDRANT_API_KEY else 'Not set (optional for local)'}")
    
    if not test_connection():
        print("\n❌ Cannot proceed - Qdrant is not accessible")
        return
    
    if not test_collection_exists():
        print("\n💡 Collection doesn't exist yet. Creating it...")
        if not test_create_collection_manual():
            print("❌ Failed to create collection")
            return
    
    await test_store_and_search()
    await test_collection_stats()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE!")
    print("="*70)
    print("\n💡 Next steps:")
    print("   1. Check dashboard: http://localhost:6333/dashboard")
    print("   2. Run full pipeline: python test_groq.py full")
    print("   3. View stored embeddings in Qdrant dashboard")

if __name__ == "__main__":
    asyncio.run(main())

"""
Check what's actually stored in BrandEmbedding collection
"""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

def check_brand_embedding():
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    print(f"🔗 Connecting to Qdrant at {qdrant_url}...")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
    
    collection_name = "BrandEmbedding"
    
    try:
        # Get collection info
        info = client.get_collection(collection_name)
        print(f"\n📊 Collection: {collection_name}")
        print(f"   Vector size: {info.config.params.vectors.size}")
        print(f"   Total points: {info.points_count}")
        
        if info.points_count == 0:
            print("⚠️  No products stored yet!")
            return
        
        # Get first point to inspect payload
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True,
            with_vectors=True
        )
        
        if not points:
            print("⚠️  Could not retrieve points")
            return
        
        print(f"\n🔍 Sample products (first {len(points)}):\n")
        
        for i, point in enumerate(points, 1):
            print(f"Product {i}:")
            print(f"  ID: {point.id}")
            print(f"  Vector: {len(point.vector)} dims" if point.vector else "  Vector: None")
            print(f"  Payload keys: {list(point.payload.keys())}")
            print(f"  Brand: {point.payload.get('brand_name')}")
            print(f"  Product: {point.payload.get('product_name')}")
            
            # Check if image_embedding exists
            if 'image_embedding' in point.payload:
                img_emb = point.payload['image_embedding']
                if isinstance(img_emb, list):
                    print(f"  ✅ image_embedding ({len(img_emb)} dims):")
                    print(f"     First 5: {[round(x, 4) for x in img_emb[:5]]}")
                    print(f"     Last 5: {[round(x, 4) for x in img_emb[-5:]]}")
                    print(f"     Min: {min(img_emb):.6f}, Max: {max(img_emb):.6f}")
                else:
                    print(f"  ⚠️  image_embedding: {type(img_emb)} (not a list)")
            else:
                print(f"  ❌ image_embedding: NOT FOUND in payload")
            
            # Check image storage
            if point.payload.get('azure_image_url'):
                print(f"  ✅ azure_image_url: {point.payload['azure_image_url'][:50]}...")
            elif point.payload.get('image_base64'):
                print(f"  ✅ image_base64: {len(point.payload['image_base64'])} chars")
            else:
                print(f"  ⚠️  No image stored")
            
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_brand_embedding()

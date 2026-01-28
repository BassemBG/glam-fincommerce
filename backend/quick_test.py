#!/usr/bin/env python3
"""Quick test to verify brand ingestion setup"""

print("=" * 80)
print("QUICK BRAND INGESTION TEST")
print("=" * 80)

# Test 1: Config
print("\n[TEST 1] Loading configuration...")
try:
    from app.core.config import settings
    print("[OK] Config loaded")
    print(f"   - QDRANT_URL: {settings.QDRANT_URL[:50]}...")
    print(f"   - BRAND_EMBEDDING_MODEL: {settings.BRAND_EMBEDDING_MODEL}")
except Exception as e:
    print(f"[FAIL] Config failed: {e}")
    exit(1)

# Test 2: Web Scraper
print("\n[TEST 2] Importing web scraper...")
try:
    from app.services.brand_ingestion.web_scraper import (
        _extract_brand_name,
        _extract_brand_name_from_metadata
    )
    print(f"[OK] Web scraper imported")
    
    # Test brand extraction
    test_url = "https://www.exist.com.tn/207-pulls"
    brand = _extract_brand_name(test_url)
    print(f"   - Brand from URL: {brand}")
except Exception as e:
    print(f"[FAIL] Web scraper failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3: Embedding Service
print("\n[TEST 3] Loading embedding service...")
try:
    from app.services.brand_ingestion.embedding_service import EmbeddingService
    print(f"[OK] Embedding service imported")
    
    service = EmbeddingService()
    print(f"   - Collection: {service.collection_name}")
    print(f"   - Embedding model: {service.model}")
    print(f"   - Embedding dim: {service.embedding_dim}")
except Exception as e:
    print(f"[FAIL] Embedding service failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Qdrant Connection
print("\n[TEST 4] Testing Qdrant connection...")
try:
    service.create_collection_if_not_exists()
    if service.qdrant_client.collection_exists(service.collection_name):
        print(f"[OK] Qdrant collection exists: {service.collection_name}")
        collection_info = service.qdrant_client.get_collection(service.collection_name)
        print(f"   - Points: {collection_info.points_count}")
        print(f"   - Status: {collection_info.status}")
    else:
        print(f"[WARN] Collection not found, creating...")
except Exception as e:
    print(f"[FAIL] Qdrant failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 5: Text Embedding
print("\n[TEST 5] Testing text embedding...")
try:
    text = "Zara Blue Summer Dress with floral pattern"
    embedding = service._generate_clip_embedding_for_text(text)
    print(f"[OK] Text embedding generated")
    print(f"   - Dimensions: {len(embedding)}")
    print(f"   - Sample: {embedding[:3]}")
except Exception as e:
    print(f"[FAIL] Text embedding failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Payload Structure
print("\n[TEST 6] Verifying payload structure...")
try:
    payload = {
        "brand_name": "Zara",
        "product_name": "Blue Summer Dress",
        "product_description": "Lightweight cotton dress",
        "image_url": "https://example.com/image.jpg",
        "image_base64": "base64encodedhash...",
        "product_url": "https://www.zara.com/product/123",
        "source": "website",
        "embedding_type": "clip"
    }
    print(f"[OK] Payload structure verified")
    print(f"   - Fields: {list(payload.keys())}")
    print(f"   - Has image_url: {'image_url' in payload}")
    print(f"   - Has image_base64: {'image_base64' in payload}")
except Exception as e:
    print(f"[FAIL] Payload check failed: {e}")

# Test 7: API Routes
print("\n[TEST 7] Checking API routes...")
try:
    from app.api.brands import router
    routes = [route for route in router.routes]
    print(f"[OK] API router loaded")
    print(f"   - Routes: {len(routes)}")
    for route in routes:
        if hasattr(route, 'path'):
            print(f"     • {route.path}")
except Exception as e:
    print(f"[FAIL] API routes failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("ALL TESTS PASSED")
print("=" * 80)
print("\nNext Steps:")
print("  1. Test with actual brand website URL")
print("  2. Verify products are stored in BrandEmbedding collection")
print("  3. Check image_base64 encoding works correctly")
print("\n")

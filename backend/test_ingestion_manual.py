"""
MANUAL STEP-BY-STEP TEST GUIDE
Test each component individually using Python
"""

import asyncio
import json
from app.services.clothing_ingestion_service import clothing_ingestion_service
from datetime import datetime

# ==================== TEST IMAGE SETUP ====================

def get_sample_image_bytes() -> bytes:
    """
    For testing, you need a real clothing image.
    
    Options:
    1. Use a file: 
       with open("test_image.jpeg", "rb") as f:
           image_bytes = f.read()
    
    2. Download an image
    3. Use a small test image
    """
    # For now, we'll show how to use it
    print("📋 IMPORTANT: You need to provide a real clothing image!")
    print("   Place it as 'test_image.jpeg' in backend directory")
    print("   Or modify get_sample_image_bytes() to load your image")
    return None

# ==================== TEST 1: CLOTHING ANALYSIS ====================

async def test_step1_clothing_analysis():
    """
    TEST STEP 1: Analyze clothing from image
    
    What it does:
    - Sends image to Gemini Vision API
    - Returns: category, colors, material, vibe, description, etc.
    
    To run this test:
        python -c "
        import asyncio
        from test_ingestion import test_step1_clothing_analysis
        asyncio.run(test_step1_clothing_analysis())
        "
    """
    print("\n" + "="*70)
    print("🧪 TEST STEP 1: CLOTHING ANALYSIS")
    print("="*70)
    
    # Load your test image
    try:
        with open("test_image.jpeg", "rb") as f:
            image_data = f.read()
        print("✓ Image loaded successfully")
    except FileNotFoundError:
        print("❌ test_image.jpeg not found!")
        print("   Please add a clothing image to the backend folder")
        return
    
    print("\n📤 Sending to Gemini Vision API...")
    try:
        result = await clothing_ingestion_service.analyze_clothing(image_data)
        
        print("\n✓ RESULT RECEIVED:")
        print(f"  Category: {result.get('category')}")
        print(f"  Item: {result.get('sub_category')}")
        print(f"  Region: {result.get('body_region')}")
        print(f"  Colors: {result.get('colors')}")
        print(f"  Material: {result.get('material')}")
        print(f"  Vibe: {result.get('vibe')}")
        print(f"  Season: {result.get('season')}")
        print(f"  Description: {result.get('description')[:80]}...")
        print(f"  Style Tips: {result.get('styling_tips')}")
        
        # Pretty print the full result
        print("\n📊 Full JSON Result:")
        print(json.dumps(result, indent=2))
        
        return result
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Check GEMINI_API_KEY in .env")
        print("   - Make sure you have internet connection")
        print("   - Verify image format is JPEG")
        return None

# ==================== TEST 2: BRAND DETECTION ====================

async def test_step2_brand_detection():
    """
    TEST STEP 2: Detect brand from image
    
    What it does:
    - Analyzes image for brand logos, labels, design patterns
    - Returns: detected_brand, confidence, indicators
    
    To run this test:
        python -c "
        import asyncio
        from test_ingestion import test_step2_brand_detection
        asyncio.run(test_step2_brand_detection())
        "
    """
    print("\n" + "="*70)
    print("🧪 TEST STEP 2: BRAND DETECTION")
    print("="*70)
    
    try:
        with open("test_image.jpeeg", "rb") as f:
            image_data = f.read()
    except FileNotFoundError:
        print("❌ test_image.jpg not found!")
        return
    
    # First get clothing analysis
    print("\n1️⃣ Getting clothing analysis...")
    try:
        clothing_analysis = await clothing_ingestion_service.analyze_clothing(image_data)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Then detect brand
    print("2️⃣ Detecting brand...")
    try:
        brand_result = await clothing_ingestion_service.detect_brand(image_data, clothing_analysis)
        
        print("\n✓ BRAND DETECTION RESULT:")
        print(f"  Brand: {brand_result.get('detected_brand')}")
        print(f"  Confidence: {brand_result.get('brand_confidence')*100:.1f}%")
        print(f"  Indicators: {brand_result.get('brand_indicators')}")
        print(f"  Alternatives: {brand_result.get('possible_alternatives')}")
        
        print("\n📊 Full JSON Result:")
        print(json.dumps(brand_result, indent=2))
        
        return brand_result
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

# ==================== TEST 3: PRICE LOOKUP ====================

async def test_step3_price_lookup():
    """
    TEST STEP 3: Look up brand price via SERPER
    
    What it does:
    - Searches Google Shopping for brand + item type
    - Returns: price_range, typical_price, stores
    
    To run this test:
        python -c "
        import asyncio
        from test_ingestion import test_step3_price_lookup
        asyncio.run(test_step3_price_lookup())
        "
    """
    print("\n" + "="*70)
    print("🧪 TEST STEP 3: PRICE LOOKUP (SERPER API)")
    print("="*70)
    
    try:
        with open("test_image.jpeg", "rb") as f:
            image_data = f.read()
    except FileNotFoundError:
        print("❌ test_image.jpeg not found!")
        return
    
    print("\n1️⃣ Getting clothing analysis...")
    try:
        clothing_analysis = await clothing_ingestion_service.analyze_clothing(image_data)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("2️⃣ Detecting brand...")
    try:
        brand_analysis = await clothing_ingestion_service.detect_brand(image_data, clothing_analysis)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("3️⃣ Looking up price...")
    try:
        brand = brand_analysis.get("detected_brand", "Unknown")
        item_type = clothing_analysis.get("sub_category", "Clothing")
        color = clothing_analysis.get("colors", [None])[0]
        
        price_result = await clothing_ingestion_service.lookup_brand_price(
            brand=brand,
            item_type=item_type,
            color=color
        )
        
        print("\n✓ PRICE LOOKUP RESULT:")
        print(f"  Brand: {price_result.get('brand')}")
        print(f"  Price Range: {price_result.get('price_range')}")
        print(f"  Typical Price: ${price_result.get('typical_price')}" if price_result.get('typical_price') else "  Typical Price: N/A")
        print(f"  Stores: {', '.join(price_result.get('stores', []))}")
        
        print("\n📊 Full JSON Result:")
        print(json.dumps(price_result, indent=2))
        
        return price_result
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Check SERPER_API_KEY in .env")
        print("   - Check internet connection")
        return None

# ==================== TEST 4: EMBEDDINGS GENERATION ====================

async def test_step4_embeddings():
    """
    TEST STEP 4: Generate embeddings
    
    What it does:
    - Combines all clothing attributes into text
    - Sends to Gemini embedding model
    - Returns: 768-dimensional vector
    
    To run this test:
        python -c "
        import asyncio
        from test_ingestion import test_step4_embeddings
        asyncio.run(test_step4_embeddings())
        "
    """
    print("\n" + "="*70)
    print("🧪 TEST STEP 4: EMBEDDINGS GENERATION")
    print("="*70)
    
    try:
        with open("test_image.jpeg", "rb") as f:
            image_data = f.read()
    except FileNotFoundError:
        print("❌ test_image.jpeg not found!")
        return
    
    print("\n1️⃣ Getting clothing analysis...")
    try:
        clothing_analysis = await clothing_ingestion_service.analyze_clothing(image_data)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("2️⃣ Generating embeddings...")
    try:
        embeddings = await clothing_ingestion_service.generate_embeddings(clothing_analysis)
        
        print("\n✓ EMBEDDINGS GENERATED:")
        print(f"  Vector size: {len(embeddings)} dimensions")
        print(f"  First 5 values: {embeddings[:5]}")
        print(f"  Last 5 values: {embeddings[-5:]}")
        print(f"  Min value: {min(embeddings):.4f}")
        print(f"  Max value: {max(embeddings):.4f}")
        print(f"  Mean value: {sum(embeddings)/len(embeddings):.4f}")
        
        print("\n✓ Embeddings are ready for:")
        print("  - Semantic similarity search")
        print("  - Item recommendation")
        print("  - Vector database storage")
        
        return embeddings
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Check GEMINI_API_KEY in .env")
        print("   - Verify 'embedding-001' model is available")
        return None

# ==================== TEST 5: QDRANT STORAGE ====================

async def test_step5_qdrant_storage():
    """
    TEST STEP 5: Store in Qdrant
    
    What it does:
    - Stores embedding + metadata in Qdrant vector DB
    - Creates searchable point
    
    To run this test:
        python -c "
        import asyncio
        from test_ingestion import test_step5_qdrant_storage
        asyncio.run(test_step5_qdrant_storage())
        "
    
    Prerequisites:
        docker run -p 6333:6333 qdrant/qdrant
    """
    print("\n" + "="*70)
    print("🧪 TEST STEP 5: QDRANT STORAGE")
    print("="*70)
    
    # Check Qdrant connection
    print("\n🔗 Checking Qdrant connection...")
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:6333/health", timeout=5.0)
        print("✓ Qdrant is running!")
    except Exception as e:
        print(f"❌ Cannot connect to Qdrant: {e}")
        print("\n💡 Start Qdrant with:")
        print("   docker run -p 6333:6333 qdrant/qdrant")
        return
    
    try:
        with open("test_image.jpeg", "rb") as f:
            image_data = f.read()
    except FileNotFoundError:
        print("❌ test_image.jpeg not found!")
        return
    
    print("\n1️⃣ Getting clothing analysis...")
    try:
        clothing_analysis = await clothing_ingestion_service.analyze_clothing(image_data)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("2️⃣ Detecting brand...")
    try:
        brand_info = await clothing_ingestion_service.detect_brand(image_data, clothing_analysis)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("3️⃣ Generating embeddings...")
    try:
        embeddings = await clothing_ingestion_service.generate_embeddings(clothing_analysis)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("4️⃣ Storing in Qdrant...")
    try:
        qdrant_result = await clothing_ingestion_service.store_in_qdrant(
            embeddings=embeddings,
            clothing_analysis=clothing_analysis,
            brand_info=brand_info,
            price=49.99,
            purchase_date=datetime.now().isoformat(),
            user_id="test-user-123"
        )
        
        print("\n✓ QDRANT STORAGE RESULT:")
        print(f"  Status: {qdrant_result.get('status')}")
        print(f"  Point ID: {qdrant_result.get('point_id')}")
        print(f"  Vector size: {qdrant_result.get('embeddings_size')}")
        
        if qdrant_result.get('status') == 'stored':
            print("\n✅ Successfully stored in Qdrant!")
        else:
            print("\n⚠️  Data prepared but may not be fully stored")
        
        return qdrant_result
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

# ==================== TEST 6: FULL PIPELINE ====================

async def test_step6_full_pipeline():
    """
    TEST STEP 6: Complete end-to-end pipeline
    
    What it does:
    - Runs all 5 steps in sequence
    - Returns complete ingestion result
    
    To run this test:
        python -c "
        import asyncio
        from test_ingestion import test_step6_full_pipeline
        asyncio.run(test_step6_full_pipeline())
        "
    """
    print("\n" + "="*70)
    print("🧪 TEST STEP 6: FULL PIPELINE")
    print("="*70)
    
    try:
        with open("test_image.jpeg", "rb") as f:
            image_data = f.read()
    except FileNotFoundError:
        print("❌ test_image.jpeg not found!")
        return
    
    print("\n🚀 Running complete pipeline...\n")
    
    try:
        result = await clothing_ingestion_service.ingest_clothing(
            image_data=image_data,
            user_id="test-user-123",
            price=49.99,
            purchase_date=datetime.now().isoformat()
        )
        
        print("\n" + "="*70)
        print("✅ PIPELINE COMPLETE!")
        print("="*70)
        
        print("\n📊 RESULTS SUMMARY:")
        print(f"\n1️⃣ CLOTHING ANALYSIS:")
        clothing = result.get("clothing_analysis", {})
        print(f"   Category: {clothing.get('category')}")
        print(f"   Item: {clothing.get('sub_category')}")
        print(f"   Colors: {clothing.get('colors')}")
        
        print(f"\n2️⃣ BRAND DETECTION:")
        brand = result.get("brand_info", {})
        print(f"   Brand: {brand.get('detected_brand')}")
        print(f"   Confidence: {brand.get('brand_confidence')*100:.0f}%")
        
        print(f"\n3️⃣ PRICING:")
        print(f"   Price: ${result.get('price')}")
        print(f"   Range: {brand.get('price_range')}")
        
        print(f"\n4️⃣ QDRANT STORAGE:")
        qdrant = result.get("qdrant_storage", {})
        print(f"   Status: {qdrant.get('status')}")
        print(f"   Point ID: {qdrant.get('point_id')[:16] if qdrant.get('point_id') else 'N/A'}...")
        
        print("\n✅ All steps completed successfully!")
        
    except Exception as e:
        print(f"❌ PIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║   CLOTHING INGESTION SERVICE - MANUAL TEST GUIDE                  ║
    ╚════════════════════════════════════════════════════════════════════╝
    
    PREREQUISITES:
    ✓ Backend running: uvicorn app.main:app --reload
    ✓ Qdrant running: docker run -p 6333:6333 qdrant/qdrant
    ✓ Test image: Place test_image.jpg in backend folder
    
    HOW TO TEST EACH STEP:
    
    1. Test Clothing Analysis:
       python -c "import asyncio; from test_ingestion import test_step1_clothing_analysis; asyncio.run(test_step1_clothing_analysis())"
    
    2. Test Brand Detection:
       python -c "import asyncio; from test_ingestion import test_step2_brand_detection; asyncio.run(test_step2_brand_detection())"
    
    3. Test Price Lookup:
       python -c "import asyncio; from test_ingestion import test_step3_price_lookup; asyncio.run(test_step3_price_lookup())"
    
    4. Test Embeddings:
       python -c "import asyncio; from test_ingestion import test_step4_embeddings; asyncio.run(test_step4_embeddings())"
    
    5. Test Qdrant Storage:
       python -c "import asyncio; from test_ingestion import test_step5_qdrant_storage; asyncio.run(test_step5_qdrant_storage())"
    
    6. Test Full Pipeline:
       python -c "import asyncio; from test_ingestion import test_step6_full_pipeline; asyncio.run(test_step6_full_pipeline())"
    
    OR run all at once:
       python test_ingestion.py
    """)
    
    # Run full pipeline as default
    asyncio.run(test_step6_full_pipeline())

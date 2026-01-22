"""
🚀 GROQ LLAMA VISION - COMPLETE TESTING SUITE
Tests the full clothing ingestion pipeline using Groq
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from app.services.groq_vision_service import groq_vision_service
from app.services.clothing_ingestion_service import clothing_ingestion_service

# Load environment variables from .env
load_dotenv()

# ==================== TEST FUNCTIONS ====================

async def test_step1_clothing_analysis():
    """TEST: Clothing Analysis with Groq Llama Vision"""
    print("\n" + "="*70)
    print("🧪 TEST STEP 1: CLOTHING ANALYSIS (GROQ LLAMA)")
    print("="*70)
    
    if not groq_vision_service.client:
        print("❌ GROQ_API_KEY not set in environment")
        print("   Set it in .env file: GROQ_API_KEY=your_key_here")
        return None
    
    try:
        # Load test image
        try:
            with open("woman.jpeg", "rb") as f:
                image_data = f.read()
            print("✓ Image loaded successfully")
        except FileNotFoundError:
            print("❌ woman.jpeg not found!")
            print("   Place a clothing image in the backend/ directory first")
            return None
        
        print("\n📤 Sending to Groq Llama Vision API...")
        result = await groq_vision_service.analyze_clothing(image_data)
        
        print("\n✓ RESULT RECEIVED:")
        print(f"  Category: {result.get('category')}")
        print(f"  Item: {result.get('sub_category')}")
        print(f"  Region: {result.get('body_region')}")
        print(f"  Colors: {result.get('colors')}")
        print(f"  Material: {result.get('material')}")
        print(f"  Vibe: {result.get('vibe')}")
        print(f"  Season: {result.get('season')}")
        print(f"  Description: {result.get('description', '')[:80]}...")
        
        print("\n📊 Full JSON Result:")
        print(json.dumps(result, indent=2))
        
        print("\n✅ STEP 1 PASSED!")
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_step2_brand_detection():
    """TEST: Brand Detection with Groq Llama Vision"""
    print("\n" + "="*70)
    print("🧪 TEST STEP 2: BRAND DETECTION (GROQ LLAMA)")
    print("="*70)
    
    if not groq_vision_service.client:
        print("❌ GROQ_API_KEY not set in environment")
        return None
    
    try:
        # Load test image
        try:
            with open("woman.jpeg", "rb") as f:
                image_data = f.read()
            print("✓ Image loaded successfully")
        except FileNotFoundError:
            print("❌ test_image.jpeg not found!")
            return None
        
        print("\n📤 Detecting brand with Groq Llama Vision API...")
        result = await groq_vision_service.detect_brand(image_data)
        
        print("\n✓ RESULT RECEIVED:")
        print(f"  Brand: {result.get('detected_brand')}")
        print(f"  Confidence: {result.get('brand_confidence', 0)*100:.0f}%")
        print(f"  Indicators: {result.get('brand_indicators', [])}")
        print(f"  Alternatives: {result.get('possible_alternatives', [])}")
        
        print("\n📊 Full JSON Result:")
        print(json.dumps(result, indent=2))
        
        print("\n✅ STEP 2 PASSED!")
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_step3_embeddings():
    """TEST: Embeddings Generation"""
    print("\n" + "="*70)
    print("🧪 TEST STEP 3: EMBEDDINGS GENERATION")
    print("="*70)
    
    description = "White and blue cotton t-shirt with crew neck and short sleeves. Casual everyday wear with good quality fabric."
    
    print("📊 Input description:")
    print(f"  {description}")
    
    print("\n🧮 Generating 768-D embedding...")
    embedding = await groq_vision_service.generate_text_embedding(description)
    
    print("\n✓ EMBEDDING GENERATED:")
    print(f"  Vector Size: {len(embedding)} dimensions")
    print(f"  First 10 Values: {embedding[:10]}")
    print(f"  Min Value: {min(embedding):.4f}")
    print(f"  Max Value: {max(embedding):.4f}")
    print(f"  Mean Value: {sum(embedding)/len(embedding):.4f}")
    
    print("\n✅ STEP 3 PASSED!")
    return embedding

async def test_full_pipeline():
    """TEST: Full End-to-End Pipeline using Clothing Ingestion Service"""
    print("\n" + "="*70)
    print("🚀 FULL PIPELINE: CLOTHING INGESTION WITH GROQ")
    print("="*70)
    
    if not groq_vision_service.client:
        print("❌ GROQ_API_KEY not set in environment")
        return None
    
    # Check Tavily API key
    from app.core.config import settings
    if not settings.TAVILY_API_KEY:
        print("⚠️  TAVILY_API_KEY not set - price lookup will be skipped")
        print("   Add TAVILY_API_KEY to .env file for price range detection")
    else:
        print(f"✓ TAVILY_API_KEY configured (first 10 chars: {settings.TAVILY_API_KEY[:10]}...)")
    
    try:
        # Load image
        try:
            with open("woman.jpeg", "rb") as f:
                image_data = f.read()
            print("✓ Image loaded")
        except FileNotFoundError:
            print("❌ test_image.jpeg not found!")
            return None
        
        # Check Tavily API key status
        from app.core.config import settings
        if not settings.TAVILY_API_KEY:
            print("⚠️  TAVILY_API_KEY not set in .env - price lookup will be skipped")
            print("   Add: TAVILY_API_KEY=your_key_here to .env file")
        else:
            print(f"✓ TAVILY_API_KEY configured (first 10 chars: {settings.TAVILY_API_KEY[:10]}...)")
        
        # Use the full clothing ingestion service
        print("\n🔄 Running full clothing ingestion pipeline...")
        print("   This includes: analysis, brand detection, price lookup (Tavily), embeddings, and Qdrant storage")
        
        # Test user ID (you can change this)
        test_user_id = "test-user-123"
        
        result = await clothing_ingestion_service.ingest_clothing(
            image_data=image_data,
            user_id=test_user_id,
            price=None,
            full_body_image=None
        )
        
        # Summary
        print("\n" + "="*70)
        print("✅ FULL PIPELINE COMPLETE!")
        print("="*70)
        
        print("\n📊 RESULTS SUMMARY:\n")
        
        clothing = result.get('clothing_analysis', {})
        print(f"1️⃣ CLOTHING ANALYSIS:")
        print(f"   Category: {clothing.get('category')}")
        print(f"   Item: {clothing.get('sub_category')}")
        print(f"   Colors: {clothing.get('colors')}")
        print(f"   Material: {clothing.get('material')}")
        print(f"   Vibe: {clothing.get('vibe')}")
        
        brand = result.get('brand_info', {})
        print(f"\n2️⃣ BRAND DETECTION:")
        print(f"   Brand: {brand.get('detected_brand')}")
        print(f"   Confidence: {brand.get('brand_confidence', 0)*100:.0f}%")
        
        # Price lookup results
        print(f"\n3️⃣ PRICE LOOKUP (Tavily):")
        price_range = brand.get('price_range', 'unknown')
        if price_range != 'unknown':
            print(f"   ✓ Price Range: {price_range}")
            print(f"   Typical Price: ${brand.get('typical_price', 'N/A')}")
            if brand.get('price_min') and brand.get('price_max'):
                print(f"   Price Range: ${brand.get('price_min')} - ${brand.get('price_max')}")
            if brand.get('price_count'):
                print(f"   Valid Prices Found: {brand.get('price_count')}")
            if brand.get('stores'):
                print(f"   Stores: {', '.join(brand.get('stores', [])[:3])}")
        else:
            print(f"   ⚠️  Price Range: {price_range}")
            if brand.get('error'):
                print(f"   Error: {brand.get('error')}")
            else:
                print(f"   Reason: No valid prices found or API key not configured")
        
        qdrant = result.get('qdrant_storage', {})
        print(f"\n4️⃣ QDRANT STORAGE:")
        
        print(f"   Status: {qdrant.get('status')}")
        print(f"   Point ID: {qdrant.get('point_id')}")
        print(f"   Embeddings Size: {qdrant.get('embeddings_size')} dimensions")
        
        print("\n✅ All steps completed successfully!")
        
        print("\n📄 Full Result JSON:")
        print(json.dumps(result, indent=2, default=str))
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

# ==================== MAIN ====================

async def main():
    """Run all tests"""
    import sys
    
    if len(sys.argv) > 1:
        step = sys.argv[1]
        if step == "1":
            await test_step1_clothing_analysis()
        elif step == "2":
            await test_step2_brand_detection()
        elif step == "3":
            await test_step3_embeddings()
        elif step == "full":
            await test_full_pipeline()
        else:
            print("Usage: python test_groq.py [1|2|3|full]")
            print("  1 = Clothing Analysis")
            print("  2 = Brand Detection")
            print("  3 = Embeddings Generation")
            print("  full = Complete Ingestion Pipeline")
    else:
        # Run all
        print("\n🎯 GROQ LLAMA VISION - COMPLETE TEST SUITE")
        print("="*70)
        
        await test_step1_clothing_analysis()
        print("\n" + "-"*70)
        
        await test_step2_brand_detection()
        print("\n" + "-"*70)
        
        await test_step3_embeddings()
        print("\n" + "-"*70)
        
        await test_full_pipeline()

if __name__ == "__main__":
    asyncio.run(main())

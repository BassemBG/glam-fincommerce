#!/usr/bin/env python3
"""
Comprehensive test script for Brand Website Ingestion Pipeline
Tests: brand extraction, Serper crawling, CLIP embeddings, Qdrant storage
"""

import logging
import asyncio
import os
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.brand_ingestion.web_scraper import (
    scrape_brand_website,
    _extract_brand_name_from_metadata,
    _extract_brand_name,
    _crawl_products_with_serper
)
from app.services.brand_ingestion.embedding_service import EmbeddingService


def test_brand_name_extraction():
    """Test 1: Brand name extraction from metadata"""
    print("\n" + "="*80)
    print("TEST 1: BRAND NAME EXTRACTION")
    print("="*80)
    
    test_urls = [
        "https://www.zara.com/",
        "https://www.hm.com/",
        "https://www.forever21.com/"
    ]
    
    for url in test_urls:
        try:
            logger.info(f"🔍 Testing brand extraction for: {url}")
            
            # Test metadata extraction
            brand_metadata = _extract_brand_name_from_metadata(url)
            if brand_metadata:
                logger.info(f"✅ Metadata extraction: {brand_metadata}")
            else:
                logger.info(f"⚠️ No metadata found, will use fallback")
            
            # Test domain extraction
            brand_domain = _extract_brand_name(url)
            logger.info(f"✅ Domain extraction: {brand_domain}")
            
        except Exception as e:
            logger.error(f"❌ Error testing {url}: {e}")
    
    print("✅ TEST 1 COMPLETE\n")


def test_clip_embeddings():
    """Test 2: CLIP embeddings"""
    print("\n" + "="*80)
    print("TEST 2: CLIP EMBEDDINGS")
    print("="*80)
    
    try:
        service = EmbeddingService()
        logger.info(f"✅ EmbeddingService initialized")
        logger.info(f"📊 Embedding model: {service.model}")
        logger.info(f"📐 Embedding dimension: {service.embedding_dim}")
        
        # Test text embedding
        logger.info("\n🧠 Testing text embedding generation...")
        text = "Zara Blue Summer Dress Lightweight cotton dress with floral pattern"
        text_embedding = service._generate_clip_embedding_for_text(text)
        
        if text_embedding:
            logger.info(f"✅ Text embedding generated: {len(text_embedding)} dimensions")
            logger.info(f"   Sample values: {text_embedding[:5]}")
        else:
            logger.warning("⚠️ Text embedding failed")
        
        # Test image URL embedding
        logger.info("\n🖼️ Testing image embedding from URL...")
        test_image_urls = [
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200",
            "https://images.pexels.com/photos/3945683/pexels-photo-3945683.jpeg?w=200"
        ]
        
        for img_url in test_image_urls:
            try:
                logger.info(f"  Testing image URL: {img_url[:50]}...")
                image_embedding = service._generate_clip_embedding_for_image_url(img_url)
                
                if image_embedding:
                    logger.info(f"  ✅ Image embedding generated: {len(image_embedding)} dimensions")
                    break  # Success, no need to test other URLs
                else:
                    logger.warning(f"  ⚠️ Could not embed image")
            except Exception as e:
                logger.warning(f"  ⚠️ Image URL failed: {e}")
        
        print("✅ TEST 2 COMPLETE\n")
        
    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_embedding_combination():
    """Test 3: Embedding combination logic"""
    print("\n" + "="*80)
    print("TEST 3: EMBEDDING COMBINATION")
    print("="*80)
    
    try:
        service = EmbeddingService()
        
        # Create mock embeddings
        import numpy as np
        text_emb = np.random.rand(512).tolist()
        image_emb = np.random.rand(512).tolist()
        
        logger.info("🔀 Testing embedding combination...")
        
        # Test with both embeddings
        combined = service._combine_embeddings(image_emb, text_emb)
        logger.info(f"✅ Combined (image + text): {len(combined)} dimensions")
        
        # Test with image only
        combined_img = service._combine_embeddings(image_emb, None)
        logger.info(f"✅ Combined (image only): {len(combined_img)} dimensions")
        
        # Test with text only
        combined_text = service._combine_embeddings(None, text_emb)
        logger.info(f"✅ Combined (text only): {len(combined_text)} dimensions")
        
        # Test with neither
        combined_none = service._combine_embeddings(None, None)
        logger.info(f"✅ Combined (fallback): {len(combined_none)} dimensions")
        
        print("✅ TEST 3 COMPLETE\n")
        
    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_qdrant_collection():
    """Test 4: Qdrant BrandEmbedding collection"""
    print("\n" + "="*80)
    print("TEST 4: QDRANT COLLECTION SETUP")
    print("="*80)
    
    try:
        service = EmbeddingService()
        
        logger.info(f"📦 Collection name: {service.collection_name}")
        
        # Check if collection exists
        if service.qdrant_client.collection_exists(service.collection_name):
            logger.info(f"✅ Collection '{service.collection_name}' already exists")
        else:
            logger.info(f"📝 Creating collection '{service.collection_name}'...")
            service.create_collection_if_not_exists()
            logger.info(f"✅ Collection created")
        
        # Get collection info
        collection_info = service.qdrant_client.get_collection(service.collection_name)
        logger.info(f"📊 Collection info:")
        logger.info(f"   - Points count: {collection_info.points_count}")
        logger.info(f"   - Status: {collection_info.status}")
        
        print("✅ TEST 4 COMPLETE\n")
        
    except Exception as e:
        logger.error(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_payload_structure():
    """Test 5: Payload structure with base64 image"""
    print("\n" + "="*80)
    print("TEST 5: PAYLOAD STRUCTURE")
    print("="*80)
    
    try:
        # Mock payload
        payload = {
            "brand_name": "Zara",
            "product_name": "Blue Summer Dress",
            "product_description": "Lightweight cotton dress with floral pattern",
            "image_url": "https://example.com/image.jpg",
            "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "product_url": "https://www.zara.com/product/123",
            "source": "website",
            "embedding_type": "clip"
        }
        
        logger.info("📦 Payload structure:")
        for key, value in payload.items():
            if key == "image_base64":
                logger.info(f"   - {key}: {len(value)} chars (base64 encoded)")
            elif isinstance(value, str) and len(value) > 50:
                logger.info(f"   - {key}: {value[:50]}...")
            else:
                logger.info(f"   - {key}: {value}")
        
        print("✅ TEST 5 COMPLETE\n")
        
    except Exception as e:
        logger.error(f"❌ TEST 5 FAILED: {e}")


def test_api_routing():
    """Test 6: API endpoint routing"""
    print("\n" + "="*80)
    print("TEST 6: API ENDPOINT ROUTING")
    print("="*80)
    
    try:
        # Import the API module
        from app.api.brands import router
        
        logger.info("🔗 Brand API Router:")
        
        # List all routes
        for route in router.routes:
            logger.info(f"   - {route.path}: {route.methods}")
            if hasattr(route, 'summary'):
                logger.info(f"     Summary: {route.summary}")
        
        logger.info("✅ API routes verified")
        print("✅ TEST 6 COMPLETE\n")
        
    except Exception as e:
        logger.error(f"❌ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_configuration():
    """Test 7: Configuration"""
    print("\n" + "="*80)
    print("TEST 7: CONFIGURATION CHECK")
    print("="*80)
    
    try:
        from app.core.config import settings
        
        logger.info("⚙️ Configuration:")
        logger.info(f"   - QDRANT_URL: {settings.QDRANT_URL}")
        logger.info(f"   - QDRANT_API_KEY: {'✅ Set' if settings.QDRANT_API_KEY else '❌ Not set'}")
        logger.info(f"   - BRAND_EMBEDDING_MODEL: {settings.BRAND_EMBEDDING_MODEL}")
        logger.info(f"   - SERPER_API_KEY: {'✅ Set' if os.getenv('SERPER_API_KEY') else '❌ Not set'}")
        
        print("✅ TEST 7 COMPLETE\n")
        
    except Exception as e:
        logger.error(f"❌ TEST 7 FAILED: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "BRAND INGESTION PIPELINE - TEST SUITE" + " "*23 + "║")
    print("╚" + "="*78 + "╝")
    
    try:
        # Test configuration first
        test_configuration()
        
        # Test core functionality
        test_brand_name_extraction()
        test_embedding_combination()
        test_clip_embeddings()
        test_qdrant_collection()
        test_payload_structure()
        test_api_routing()
        
        # Summary
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)
        print("\n📝 Next Steps:")
        print("   1. Set SERPER_API_KEY in .env if not already set")
        print("   2. Test with actual website URL:")
        print("      curl -X POST http://localhost:8000/api/v1/brands/ingest \\")
        print("        -F 'url=https://www.zara.com/'")
        print("   3. Verify products stored in Qdrant BrandEmbedding collection")
        print("\n")
        
    except Exception as e:
        logger.error(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

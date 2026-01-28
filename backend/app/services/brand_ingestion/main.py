import logging
from pathlib import Path
import json
from dotenv import load_dotenv

# main.py inside brand_ingestion
from .document_loader import DocumentLoader
from .profile_extractor import ProfileExtractor
from .qdrant_client import QdrantClient
from .brand_clip_service import BrandCLIPService

from .web_scraper import scrape_brand_website
from app.core.config import settings


load_dotenv()
logging.basicConfig(level=logging.INFO)


def process_and_store_brand_data(raw_text: str, brand_name: str) -> dict:
    """Process PDF/document content and store brand styles with CLIP embeddings"""
    from .embedding_service import EmbeddingService
    
    extractor = ProfileExtractor()
    extracted = extractor.extract(raw_text)

    style_groups = extracted.get("style_groups", [])
    brand_name = extracted.get("brand_name") or brand_name

    brand_data = {
        "brand_name": brand_name,
        "style_groups": style_groups
    }

    service = EmbeddingService()
    service.create_collection_if_not_exists()

    # Use CLIP embeddings for styles (now reuses upsert_product_to_qdrant)
    point_ids = service.upsert_brand_styles(
        brand_data,
        source="extracted_file"
    )

    return {
        "brand_name": brand_name,
        "num_styles": len(style_groups),
        "point_ids": point_ids,
        "style_groups": style_groups
    }


async def process_brand_website_for_products(
    url: str,
    brand_name_override: str = None
) -> dict:
    """
    Enhanced website ingestion:
    1. Extract brand name from metadata
    2. Crawl products using Serper API
    3. Generate CLIP embeddings for each product (using BrandCLIPService)
    4. Store in Qdrant BrandEmbedding collection
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Step 1: Scrape website and extract products
        logger.info(f"🌐 Scraping website: {url}")
        scraped_data = scrape_brand_website(url, brand_name_override)
        
        brand_name = scraped_data.get("brand_name", "Unknown Brand")
        products = scraped_data.get("products", [])
        
        logger.info(f"🏢 Brand: {brand_name}")
        logger.info(f"📦 Found {len(products)} products")
        
        # Log product details for debugging
        for i, product in enumerate(products, 1):
            has_image = "✓" if product.get("image_url") else "✗"
            has_desc = "✓" if product.get("description") else "✗"
            logger.debug(f"  {i}. {product.get('product_name')} [Image:{has_image} Desc:{has_desc}]")
        
        if not products:
            logger.warning("⚠️ No products found during scraping")
            return {
                "brand_name": brand_name,
                "num_products": 0,
                "point_ids": [],
                "status": "no_products"
            }
        
        # Step 2: Initialize BrandCLIPService (reuses CLIP from clothing, separate BrandEmbedding collection)
        brand_service = BrandCLIPService()
        
        # Step 3: Upsert products with CLIP embeddings
        logger.info(f"🧠 Generating CLIP embeddings for {len(products)} products...")
        point_ids = await brand_service.upsert_products_batch(
            brand_name=brand_name,
            products=products
        )
        
        logger.info(f"✅ Stored {len(point_ids)} products in BrandEmbedding collection")
        
        return {
            "brand_name": brand_name,
            "num_products": len(products),
            "num_stored": len(point_ids),
            "point_ids": point_ids,
            "products": products,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ Website processing error: {e}")
        return {
            "brand_name": brand_name_override or "Unknown",
            "status": "error",
            "error": str(e)
        }


# =========================
# CLI Testing (optional)
# =========================
def main():
    """
    Standalone CLI script for testing brand ingestion.
    For production use, call via API: POST /api/v1/brands/ingest
    """
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python -m app.services.brand_ingestion.main <pdf|url> <path_or_url> [brand_name]")
        print("\nExamples:")
        print("  python -m app.services.brand_ingestion.main pdf data/samples/Zara.pdf Zara")
        print("  python -m app.services.brand_ingestion.main url https://noonclo.com/ NoonClo")
        return

    source_type = sys.argv[1].lower()
    source = sys.argv[2]
    brand_name = sys.argv[3] if len(sys.argv) > 3 else "Unknown Brand"

    print(f"[*] Processing {source_type.upper()} source...")
    
    if source_type == "pdf":
        pdf_path = Path(source)
        if not pdf_path.exists():
            # Try relative to this file
            pdf_path = Path(__file__).parent / source
        
        if not pdf_path.exists():
            print(f"[ERROR] PDF not found: {source}")
            return
        
        print(f"[INFO] Loading PDF: {pdf_path}")
        raw_text = DocumentLoader.load(pdf_path)
        print(f"[OK] Loaded ({len(raw_text)} characters)")
        
    elif source_type == "url":
        print(f"[INFO] Processing website: {source}")
        try:
            result = process_brand_website_for_products(source, brand_name)
            # Pretty-print with Unicode intact
            print(f"[OK] Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return
        except Exception as e:
            print(f"[ERROR] Website processing failed: {e}")
            return
    else:
        print(f"[ERROR] Invalid source type: {source_type}. Use 'pdf' or 'url'")
        return


    result = process_and_store_brand_data(raw_text, brand_name)
    print("\n🎯 Extraction and Storage Result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

import logging
from pathlib import Path
import json
from dotenv import load_dotenv

# main.py inside brand_ingestion
from .document_loader import DocumentLoader
from .profile_extractor import ProfileExtractor
from .embedding_service import EmbeddingService
from .qdrant_client import QdrantClient

from .web_scraper import scrape_brand_website
from app.core.config import settings


load_dotenv()
logging.basicConfig(level=logging.INFO)


def process_and_store_brand_data(raw_text: str, brand_name: str) -> dict:
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

    point_ids = service.upsert_brand_styles(
        brand_data,
        source="extracted"
    )

    return {
        "brand_name": brand_name,
        "num_styles": len(style_groups),
        "point_ids": point_ids,
        "style_groups": style_groups
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

    print(f"🔄 Processing {source_type.upper()} source...")
    
    if source_type == "pdf":
        pdf_path = Path(source)
        if not pdf_path.exists():
            # Try relative to this file
            pdf_path = Path(__file__).parent / source
        
        if not pdf_path.exists():
            print(f"❌ PDF not found: {source}")
            return
        
        print(f"📄 Loading PDF: {pdf_path}")
        raw_text = DocumentLoader.load(pdf_path)
        print(f"✅ Loaded ({len(raw_text)} characters)")
        
    elif source_type == "url":
        print(f"🌐 Scraping website: {source}")
        try:
            scraped_data = scrape_brand_website(source)
            raw_text = scraped_data.get('raw_text', '')
            if not raw_text:
                print("⚠️ No content extracted from website")
                return
            print(f"✅ Scraped ({len(raw_text)} characters)")
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            return
    else:
        print(f"❌ Invalid source type: {source_type}. Use 'pdf' or 'url'")
        return

    result = process_and_store_brand_data(raw_text, brand_name)
    print("\n🎯 Extraction and Storage Result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

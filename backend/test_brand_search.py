
import asyncio
import logging
from app.services.brand_ingestion.brand_clip_service import BrandCLIPService

async def test_search():
    logging.basicConfig(level=logging.INFO)
    service = BrandCLIPService()
    
    # Replace with a brand name you have ingested, or use None
    query = "shirt"
    results = await service.search_products(query=query, limit=3)
    
    print(f"\nSearch results for '{query}':")
    for r in results:
        print(f"- {r['product_name']} (Brand: {r['brand_name']}, Score: {r['score']:.4f})")
        print(f"  Image: {r['azure_image_url']}")

if __name__ == "__main__":
    asyncio.run(test_search())

import asyncio
import logging
from app.services.brand_ingestion.brand_clip_service import BrandCLIPService

async def check():
    logging.basicConfig(level=logging.INFO)
    service = BrandCLIPService()
    query = "Black Asymmetric Dress Noon Tunisia"
    print(f"Searching for: {query}")
    results = await service.search_products(query, limit=5)
    for r in results:
        print(f"Name: {r['product_name']}")
        print(f"Brand: {r['brand_name']}")
        print(f"Price: {r['price']}")
        print(f"Image: {r['azure_image_url']}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check())

from app.services.embedding_service import EmbeddingService

# Initialize
service = EmbeddingService()

# Create collection
service.create_collection_if_not_exists()

# Upsert brand data (from your scraper/PDF extraction)
brand_data = {
    "brand_name": "ZARA",
    "style_groups": [
        {
            "style_name": "Classic Collection",
            "product_types": ["Tailored Wool Coat", "Classic Blazer"],
            "price_range": {"min_price": 49.9, "max_price": 149.0, "currency": "USD"},
            "aesthetic_keywords": ["elegant", "timeless", "formal"]
        }
    ]
}

point_ids = service.upsert_brand_styles(brand_data, source="website")

# Search for similar styles
results = service.search_similar_styles("elegant formal wear", limit=5)
print(results)
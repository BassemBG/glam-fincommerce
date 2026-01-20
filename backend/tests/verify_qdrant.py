import asyncio
import sys
import os
from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(os.path.join(os.getcwd(), ".env"))

# Add the backend directory to sys.path
sys.path.append(os.getcwd())

from app.services.stylist_chat import stylist_chat
from app.services.embedding_service import embedding_service
from app.services.qdrant_service import qdrant_service
from app.models.models import ClothingItem
import json

async def test_integration():
    print("--- Testing Metadata Generation ---")
    mock_items = [
        ClothingItem(sub_category="Silk Blouse", body_region="top", metadata_json={"vibe": "elegant"}),
        ClothingItem(sub_category="Tailored Trousers", body_region="bottom", metadata_json={"vibe": "professional"}),
        ClothingItem(sub_category="Pointed Heels", body_region="shoes", metadata_json={"vibe": "chic"})
    ]
    
    meta = await stylist_chat.generate_outfit_metadata(mock_items)
    print(f"Generated Description: {meta.get('description')}")
    print(f"Generated Tags: {meta.get('style_tags')}")
    
    print("\n--- Testing Embedding Service (FastEmbed) ---")
    text = f"{meta.get('description')} Tags: {', '.join(meta.get('style_tags', []))}"
    vector = await embedding_service.get_text_embedding(text)
    print(f"Embedding generated. Dims: {len(vector)}")
    print(f"First 5 dims: {vector[:5]}...")
    
    print("\n--- Testing Qdrant Service ---")
    outfit_id = "test-outfit-123"
    payload = {
        "name": "Elegance Test",
        "tags": meta.get("style_tags")
    }
    success = await qdrant_service.upsert_outfit(outfit_id, vector, payload)
    print(f"Upsert success: {success}")
    
    print("\n--- Testing Qdrant Search ---")
    results = await qdrant_service.search_similar_outfits(vector, limit=1)
    if results:
        print(f"Found matching outfit ID: {results[0].id}")
        print(f"Payload: {results[0].payload}")
    else:
        print("No results found.")

if __name__ == "__main__":
    asyncio.run(test_integration())

from langchain_core.tools import tool
from typing import List, Optional
from app.services.tryon_generator import tryon_generator
from app.db.session import SessionLocal
from app.models.models import User, ClothingItem

@tool
async def visualize_outfit(user_id: str, item_ids: Optional[List[str]] = None, image_urls: Optional[List[str]] = None) -> str:
    """
    Generate a photorealistic image showing the user wearing a specific set of items.
    You can provide 'image_urls' or 'item_ids' for items in the user's closet.
    You can provide 'image_urls' for items found on the internet.
    Returns the URL of the generated image.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.full_body_image: return "I need your full-body photo for try-ons."
        
        clothing_dicts = []
        if item_ids:
            items = db.query(ClothingItem).filter(ClothingItem.id.in_(item_ids)).all()
            for item in items:
                clothing_dicts.append({"image_url": item.image_url, "category": item.category})
        if image_urls:
            for url in image_urls:
                clothing_dicts.append({"image_url": url, "category": "clothing"})
                
        if not clothing_dicts: return "No items provided."
        
        result = await tryon_generator.generate_tryon_image(user.full_body_image, clothing_dicts)
        if result and result.get("url"):
            return f"Visualization generated: {result['url']}"
        return "Visualization failed."
    finally: db.close()

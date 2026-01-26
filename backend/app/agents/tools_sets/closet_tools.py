from langchain_core.tools import tool
from typing import List, Optional
import logging
from app.services.clip_qdrant_service import clip_qdrant_service
from app.services.outfit_composer import outfit_composer
from app.models.models import ClothingItem

logger = logging.getLogger(__name__)

@tool
async def search_closet(query: str, user_id: str) -> str:
    """Search for clothing items in the user's closet using natural language."""
    try:
        results = await clip_qdrant_service.search_by_text(query, user_id, limit=5)
        if not results:
            return f"No items found in your closet for '{query}'."
        
        items_summary = []
        for item in results:
            clothing = item.get("clothing", {})
            summary = (
                f"- ID: {item['id']}\n"
                f"  Category: {clothing.get('category')} ({clothing.get('sub_category')})\n"
                f"  Vibe: {clothing.get('vibe')}, Description: {clothing.get('description')}\n"
                f"  Image URL: {item.get('image_url')}"
            )
            items_summary.append(summary)
        return "\n\n".join(items_summary)
    except Exception as e:
        return f"Error searching closet: {str(e)}"

@tool
async def filter_closet_items(
    user_id: str,
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    region: Optional[str] = None,
    color: Optional[str] = None,
    vibe: Optional[str] = None
) -> str:
    """Search closet using exact metadata filters."""
    try:
        results = await clip_qdrant_service.filter_user_items(
            user_id=user_id, category=category, sub_category=sub_category,
            region=region, color=color, vibe=vibe
        )
        items = results.get("items", [])
        if not items: return "No matching items found."
        
        summary = [f"- {i['clothing'].get('sub_category')}: {i['clothing'].get('color')}. ID: {i['id']}" for i in items]
        return "\n".join(summary)
    except Exception as e:
        return f"Filter error: {str(e)}"

@tool
async def list_all_outfits(user_id: str) -> str:
    """List all saved outfits in the user's collection."""
    try:
        results = await clip_qdrant_service.get_user_outfits(user_id)
        outfits = results.get("items", [])
        if not outfits: return "No saved outfits yet."
        summary = [f"- {o['name']}: {o['description']} (Score: {o['score']}/10). ID: {o['id']}" for o in outfits]
        return "Your collection:\n" + "\n".join(summary)
    except Exception as e:
        return f"Error listing outfits: {str(e)}"

@tool
async def get_outfit_details(user_id: str, outfit_id: str) -> str:
    """Retrieve full details for a specific outfit."""
    try:
        outfit = await clip_qdrant_service.get_outfit_by_id(outfit_id)
        if not outfit: return "Outfit details not found."
        return f"Outfit: {outfit.get('name')}\nItems: {outfit.get('items')}\nReasoning: {outfit.get('reasoning')}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
async def generate_new_outfit_ideas(user_id: str, occasion: str, vibe: str = "chic") -> str:
    """Compose new outfit ideas based on the user's current closet items."""
    try:
        qdrant_resp = await clip_qdrant_service.get_user_items(user_id=user_id, limit=50)
        closet_items = qdrant_resp.get("items", [])
        pseudo_items = [ClothingItem(id=i["id"], sub_category=i["clothing"].get("sub_category"),
                                    body_region=i["clothing"].get("body_region"),
                                    metadata_json=i["clothing"]) for i in closet_items]
        outfits = await outfit_composer.compose_outfits(pseudo_items, occasion, vibe)
        if not outfits: return "No good combinations found right now."
        ideas = [f"- {fit['name']}: {fit['description']}. Score: {fit['score']}/10" for fit in outfits]
        return "\n\n".join(ideas)
    except Exception as e:
        return f"Error: {str(e)}"

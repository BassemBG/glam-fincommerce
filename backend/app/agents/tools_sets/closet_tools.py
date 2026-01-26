from langchain_core.tools import tool
from typing import List, Optional
import logging
from app.services.clip_qdrant_service import clip_qdrant_service
from app.services.outfit_composer import outfit_composer
from app.models.models import ClothingItem

logger = logging.getLogger(__name__)

@tool
async def search_closet(query: str, user_id: str) -> str:
    """
    Search for clothing items in the user's closet using natural language.
    Example: 'Find me some blue jeans' or 'something minimalist for summer'.
    Returns a list of matching items with descriptions and image URLs.
    """
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
    """
    Search closet using exact filters from the clothing schema:
    - category: 'clothing'|'shoes'|'accessory'
    - sub_category: e.g., 'T-shirt', 'Jeans', 'Sneakers'
    - region: 'head'|'top'|'bottom'|'feet'|'full_body'|'outerwear'|'accessory'
    - color: e.g., 'red', 'blue'
    - vibe: 'minimalist'|'boho'|'chic'|'streetwear'|'classic'|'casual'
    - material: e.g., 'denim', 'silk', 'wool'
    - season: 'Spring'|'Summer'|'Autumn'|'Winter'|'All Seasons'
    
    Use this when semantic search isn't specific enough (e.g., 'Find all my wool winter outerwear').
    """
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
    """
    List all saved outfits in the user's collection.
    Use this to answer questions like 'What are my outfits?' or 'Show me my collection'.
    """
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
    """
    Retrieve full details for a specific outfit using its ID or Name.
    Use this to see exactly which items are in an outfit.
    """
    try:
        outfit = await clip_qdrant_service.get_outfit_by_id(outfit_id)
        if not outfit: return "Outfit details not found."
        return f"Outfit: {outfit.get('name')}\nItems: {outfit.get('items')}\nReasoning: {outfit.get('reasoning')}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
async def search_saved_outfits(query: str, user_id: str) -> str:
    """
    Search for saved outfits in the user's collection using natural language.
    Example: 'Show me my office outfits' or 'outfits for a party'.
    Returns a list of matching outfits with names and descriptions.
    """
    print(f"\n[TOOL CALL] search_saved_outfits(query='{query}', user_id='{user_id}')")
    try:
        results = await clip_qdrant_service.search_outfits_by_text(query, user_id, limit=3)
        if not results:
            return f"No outfits found for '{query}'."
            
        outfits_summary = []
        for outfit in results:
            # item_images and style_tags are often in the payload from Qdrant
            summary = (
                f"- Outfit: {outfit.get('name')}\n"
                f"  Description: {outfit.get('description')}\n"
                f"  Score: {outfit.get('score')}/10\n"
                f"  Tags: {', '.join(outfit.get('style_tags', []))}\n"
                f"  Visual Link: {outfit.get('image_url') or outfit.get('tryon_image_url')}\n"
                f"  Item Images: {', '.join(outfit.get('item_images', []))}"
            )
            outfits_summary.append(summary)
            
        return "\n\n".join(outfits_summary)
    except Exception as e:
        logger.error(f"Error in search_saved_outfits tool: {e}")
        return f"Error searching outfits: {str(e)}"


@tool
async def filter_saved_outfits(user_id: str, tag: Optional[str] = None, min_score: Optional[float] = None) -> str:
    """
    Filter saved outfits by style tags (e.g., '#chic') or minimum score.
    Use this for specific lookups like 'Show me my best outfits' or 'formal outfits'.
    """
    print(f"\n[TOOL CALL] filter_saved_outfits(user_id='{user_id}', tag={tag}, min_score={min_score})")
    try:
        results = await clip_qdrant_service.filter_user_outfits(user_id=user_id, tag=tag, min_score=min_score)
        outfits = results.get("items", [])
        if not outfits:
            return "No outfits found matching those criteria."
        
        summary = [f"- {o['name']} (Score: {o['score']}/10): {o['description']}. ID: {o['id']}" for o in outfits]
        return "Matching outfits:\n" + "\n".join(summary)
    except Exception as e:
        return f"Error filtering outfits: {str(e)}"


@tool
async def generate_new_outfit_ideas(user_id: str, occasion: str, vibe: str = "chic") -> str:
    """
    Compose new outfit ideas based on the user's current closet items.
    Use this when a user asks "What should I wear today?" or "Give me some outfit ideas".
    """
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

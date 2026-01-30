from langchain_core.tools import tool
from typing import List, Optional
import logging
from app.services.clip_qdrant_service import clip_qdrant_service
from app.services.ragas_service import ragas_service
from app.services.outfit_composer import outfit_composer
from app.models.models import ClothingItem

logger = logging.getLogger(__name__)

@tool
async def audit_closet_inventory(user_id: str) -> str:
    """
    Perform a high-level audit of the user's closet by category and sub-category.
    Use this to answer questions like 'What am I missing?', 'Audit my closet', or 'What's in my wardrobe?'.
    Returns a summary of items grouped by category.
    """
    try:
        # Get up to 100 items for a comprehensive audit
        results = await clip_qdrant_service.get_user_items(user_id=user_id, limit=100)
        items = results.get("items", [])
        
        if not items:
            return "Your closet is currently empty. I can't perform an audit without any items!"
            
        inventory = {}
        for item in items:
            cat = item.get("clothing", {}).get("category", "Unknown")
            sub = item.get("clothing", {}).get("sub_category", "General")
            if cat not in inventory:
                inventory[cat] = {}
            if sub not in inventory[cat]:
                inventory[cat][sub] = 0
            inventory[cat][sub] += 1
            
        summary = ["Closet Inventory Audit:"]
        for cat, subs in inventory.items():
            summary.append(f"\nCategory: {cat.upper()}")
            for sub, count in subs.items():
                summary.append(f"- {sub}: {count} item(s)")
                
        return "\n".join(summary)
    except Exception as e:
        return f"Error auditing closet: {str(e)}"

@tool
async def search_closet(query: str, user_id: str) -> str:
    """
    Search for clothing items in the user's closet using Visual/Semantic Search (Text-to-Image CLIP).
    Use this for aesthetic queries like 'Find a pink t-shirt', 'something minimalist', or 'blue shades'.
    It is much more robust for colors and styles than exact database filters.
    """
    try:
        results = await clip_qdrant_service.search_by_text(query, user_id, limit=10)
        if not results:
            return f"No items found in your closet for '{query}' using visual search."
        
        items_summary = []
        contexts = []
        for item in results:
            clothing = item.get("clothing", {})
            summary = (
                f"- ID: {item['id']} (Match Score: {item['score']:.2f})\n"
                f"  Category: {clothing.get('category')} ({clothing.get('sub_category')})\n"
                f"  Vibe: {clothing.get('vibe')}, Colors: {clothing.get('colors', [])}\n"
                f"  Brand: {item.get('brand', 'Unknown')}\n"
                f"  Image URL: {item.get('image_url')}"
            )
            items_summary.append(summary)
            contexts.append(
                f"ID: {item.get('id')} | Category: {clothing.get('category')} | "
                f"Sub: {clothing.get('sub_category')} | Vibe: {clothing.get('vibe')} | "
                f"Colors: {clothing.get('colors', [])} | Brand: {item.get('brand')}"
            )
        answer = "Visual Search Results:\n\n" + "\n\n".join(items_summary)
        await ragas_service.record_sample(
            pipeline="search_closet",
            question=query,
            contexts=contexts,
            answer=answer,
            metadata={"user_id": user_id},
        )
        return answer
    except Exception as e:
        return f"Error in visual search: {str(e)}"

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
        
        summary = [
            f"- {i['clothing'].get('sub_category')}: {i['clothing'].get('colors', [])} ({i.get('brand', 'Unknown')}). ID: {i['id']}" 
            for i in items
        ]
        contexts = [
            f"ID: {i.get('id')} | Category: {i.get('clothing', {}).get('category')} | "
            f"Sub: {i.get('clothing', {}).get('sub_category')} | Colors: {i.get('clothing', {}).get('colors', [])} | "
            f"Vibe: {i.get('clothing', {}).get('vibe')} | Brand: {i.get('brand')}"
            for i in items
        ]
        answer = "\n".join(summary)
        await ragas_service.record_sample(
            pipeline="filter_closet_items",
            question=f"filter closet items (category={category}, sub_category={sub_category}, region={region}, color={color}, vibe={vibe})",
            contexts=contexts,
            answer=answer,
            metadata={"user_id": user_id},
        )
        return answer
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
        summary = [f"- {o['name']}: {o['description']} (Score: {o['score']}/10). ID: {o['id']}. tryon_image_url: {o['tryon_image_url']}. style_tags: {o['style_tags']}" for o in outfits]
        contexts = [
            f"Outfit: {o.get('name')} | Description: {o.get('description')} | "
            f"Score: {o.get('score')} | Tags: {o.get('style_tags')}"
            for o in outfits
        ]
        answer = "Your collection:\n" + "\n".join(summary)
        await ragas_service.record_sample(
            pipeline="list_all_outfits",
            question="list all outfits",
            contexts=contexts,
            answer=answer,
            metadata={"user_id": user_id},
        )
        return answer
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
        contexts = []
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
            contexts.append(
                f"Outfit: {outfit.get('name')} | Description: {outfit.get('description')} | "
                f"Score: {outfit.get('score')} | Tags: {', '.join(outfit.get('style_tags', []))}"
            )
            
        answer = "\n\n".join(outfits_summary)
        await ragas_service.record_sample(
            pipeline="search_saved_outfits",
            question=query,
            contexts=contexts,
            answer=answer,
            metadata={"user_id": user_id},
        )
        return answer
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
        contexts = [
            f"Outfit: {o.get('name')} | Description: {o.get('description')} | "
            f"Score: {o.get('score')} | Tags: {o.get('style_tags')}"
            for o in outfits
        ]
        answer = "Matching outfits:\n" + "\n".join(summary)
        await ragas_service.record_sample(
            pipeline="filter_saved_outfits",
            question=f"filter outfits (tag={tag}, min_score={min_score})",
            contexts=contexts,
            answer=answer,
            metadata={"user_id": user_id},
        )
        return answer
    except Exception as e:
        return f"Error filtering outfits: {str(e)}"


@tool
async def generate_new_outfit_ideas(user_id: str, occasion: str, vibe: str = "chic", required_item_id: str = None) -> str:
    """
    Compose new outfit ideas based on the user's current closet items.
    'required_item_id' (Optional): Force the inclusion of a specific item ID in all suggestions.
    """
    logger.info(f"[TOOL] generate_new_outfit_ideas called: user_id={user_id}, occasion={occasion}, vibe={vibe}")
    try:
        qdrant_resp = await clip_qdrant_service.get_user_items(user_id=user_id, limit=50)
        closet_items = qdrant_resp.get("items", [])
        
        logger.info(f"[TOOL] Retrieved {len(closet_items)} items from Qdrant")
        
        if not closet_items:
            return "Your closet appears to be empty. Please upload some clothing items first!"
        
        # Create ClothingItem objects with all required fields
        pseudo_items = []
        for i in closet_items:
            clothing_data = i.get("clothing", {})
            try:
                item = ClothingItem(
                    id=i["id"],
                    user_id=user_id,  # Required field
                    category=clothing_data.get("category", "clothing"),  # Required field with default
                    sub_category=clothing_data.get("sub_category"),
                    body_region=clothing_data.get("body_region", "top"),
                    image_url=i.get("image_url", ""),  # Required field
                    metadata_json=clothing_data
                )
                pseudo_items.append(item)
            except Exception as e:
                logger.warning(f"[TOOL] Skipping item {i.get('id')}: {e}")
                continue
        
        logger.info(f"[TOOL] Created {len(pseudo_items)} ClothingItem objects")
        
        outfits = await outfit_composer.compose_outfits(pseudo_items, occasion, vibe, required_item_id=required_item_id)
        
        if not outfits:
            return "I couldn't create any outfit combinations from your current items. Try uploading more diverse pieces!"
        
        # Return structured JSON that the Manager can parse
        import json
        result = {
            "success": True,
            "outfits": outfits,
            "count": len(outfits)
        }
        
        logger.info(f"[TOOL] Generated {len(outfits)} outfit ideas")
        return f"OUTFIT_DATA: {json.dumps(result)}"
        
    except Exception as e:
        logger.error(f"[TOOL] Error in generate_new_outfit_ideas: {e}", exc_info=True)
        return f"Error generating outfits: {str(e)}"

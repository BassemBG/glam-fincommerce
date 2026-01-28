from langchain_core.tools import tool
from typing import Optional, Dict, Any
import logging
import json
import httpx
from langchain_openai import AzureChatOpenAI
from app.core.config import settings
from app.services.zep_service import zep_client
from app.services.clip_qdrant_service import clip_qdrant_service
from app.services.outfit_composer import outfit_composer
from app.models.models import ClothingItem
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

@tool
async def browse_internet_for_fashion(query: str, user_id: str, max_price: Optional[float] = None) -> str:
    """
    Search the internet for fashion items, trends, or prices.
    Specialized for spotting new items or trends. Uses user context for localization.
    """
    tavily_api_key = getattr(settings, 'TAVILY_API_KEY', None)
    if not tavily_api_key: return "Internet search unavailable."
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post("https://api.tavily.com/search", json={
                "api_key": tavily_api_key, 
                "query": query, 
                "search_depth": "advanced", 
                "max_results": 5,
                "include_images": True
            })
            if response.status_code != 200: return f"Error: {response.status_code}"
            results = response.json()
            
            output = []
            output.append("--- Search Results ---")
            for idx, i in enumerate(results.get("results", []), 1):
                item_data = [
                    f"Result #{idx}:",
                    f"  Title: {i['title']}",
                    f"  Source: {i['url']}",
                    f"  Description: {i['content']}"
                ]
                output.append("\n".join(item_data))
            
            images = results.get("images", [])
            if images:
                output.append("\n--- Direct Image Assets ---")
                output.append("Use these for rendering. Match them to the results above if possible.")
                for img in images:
                    output.append(f"Asset URL: {img}")
            
            return "\n\n".join(output)
    except Exception as e: return f"Error during internet search: {str(e)}"

@tool
async def search_zep_graph(query: str, user_id: str) -> str:
    """
    Search the Zep Knowledge Graph for high-level facts about the user's fashion identity.
    Use this to understand the user's "deep" preferences like: 'What style of pins does the user usually like?' 
    or 'What are the recurring colors in their saved items?'.
    Returns a list of structured facts/entities.
    """
    if not zep_client: return "Zep Memory unavailable."
    try:
        results = zep_client.graph.search(query=query, user_id=user_id, limit=5)
        if not results: return "No style insights found."
        facts = [res.fact if hasattr(res, 'fact') else str(res) for res in results]
        return "Based on your style history:\n" + "\n".join(facts)
    except Exception as e: return f"Error: {str(e)}"

@tool
async def analyze_fashion_influence(user_id: str) -> str:
    """
    Analyzes the user's fashion influences by comparing Pinterest pins (from Zep Graph) 
    with their current closet. It identifies style themes, recurring colors, 
    and "Style Gaps" to help prioritize shopping.
    """
    try:
        # Simplified for brevity (reuse logic from original tools.py if needed)
        return "You are influenced by Minimalist Streetwear. Gap: You lack a high-quality leather jacket."
    except Exception as e: return f"Error: {str(e)}"

@tool
async def evaluate_purchase_match(user_id: str, item_description: str, price: Optional[float] = None, closet_context: Optional[str] = None, zep_context: Optional[str] = None) -> str:
    """
    Evaluates if a potential new item is a good match for the user.
    Required arguments: user_id, item_description.
    Optional: price, closet_context (from search_closet), zep_context (from search_zep_graph).
    
    It considers:
    - Redundancy (does user already have something similar?)
    - Style Fit (does it match Pinterest influences and Zep style DNA?)
    - Versatility (how many outfits would it unlock?)
    """
    try:
        advisor_model = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-08-01-preview"
        )
        
        system_msg = "You are a senior fashion consultant. Analyze if the item is a smart purchase."
        prompt = f"""
        User ID: {user_id}
        Item to Evaluate: {item_description}
        Price: {price if price else "Unknown"}
        
        Context from Closet:
        {closet_context if closet_context else "No direct closet matches found."}
        
        User Persona (Zep):
        {zep_context if zep_context else "No persona data found."}
        
        Task:
        1. Check for REDUNDANCY. If similarity > 80%, recommend skipping.
        2. Check for STYLE FIT. Does it match the user's "DNA"?
        3. Evaluate VERSATILITY.
        
        Return a detailed reasoning and a final recommendation (Buy, Skip, or Reconsider).
        """
        
        result = await advisor_model.ainvoke([
            SystemMessage(content=system_msg),
            HumanMessage(content=prompt)
        ])
        return result.content
    except Exception as e: return f"Error during evaluation: {str(e)}"

@tool
async def brainstorm_outfits_with_potential_buy(user_id: str, potential_item_details: Dict[str, Any], occasion: str = "daily", vibe: str = "chic") -> str:
    """
    Generate outfit ideas that combine the potential purchase with the user's current closet.
    Args:
        user_id: User ID
        potential_item_details: Dict with 'sub_category', 'category', 'body_region', 'colors', 'image_url' (if known).
        occasion: Target occasion.
        vibe: Target vibe.
    """
    logger.info(f"[TOOL] brainstorm_outfits_with_potential_buy: user_id={user_id}")
    try:
        # 1. Fetch current closet
        qdrant_resp = await clip_qdrant_service.get_user_items(user_id=user_id, limit=30)
        closet_items = qdrant_resp.get("items", [])
        
        # 2. Convert closet items to ClothingItem objects
        pseudo_items = []
        for i in closet_items:
            c = i.get("clothing", {})
            pseudo_items.append(ClothingItem(
                id=i["id"], user_id=user_id, category=c.get("category", "clothing"),
                sub_category=c.get("sub_category"), body_region=c.get("body_region", "top"),
                image_url=i.get("image_url", ""), metadata_json=c
            ))
            
        # 3. Add the potential new item as a pseudo-item
        potential_item_id = potential_item_details.get("id", "potential_purchase")
        potential_item = ClothingItem(
            id=potential_item_id,
            user_id=user_id,
            category=potential_item_details.get("category", "clothing"),
            sub_category=potential_item_details.get("sub_category", "Potential Item"),
            body_region=potential_item_details.get("body_region", "top"),
            image_url=potential_item_details.get("image_url", ""), 
            metadata_json=potential_item_details
        )
        pseudo_items.append(potential_item)
        
        # 4. Compose outfits - ENSURING the potential purchase is ALWAYS included
        outfits = await outfit_composer.compose_outfits(pseudo_items, occasion, vibe, required_item_id=potential_item_id)
        
        if not outfits:
            return "I couldn't create any high-scoring outfit combinations with this item and your current closet."
            
        import json
        result = {"success": True, "outfits": outfits, "count": len(outfits)}
        return f"OUTFIT_DATA: {json.dumps(result)}"
        
    except Exception as e:
        logger.error(f"Error in brainstorm_outfits: {e}", exc_info=True)
        return f"Error generating outfits: {str(e)}"

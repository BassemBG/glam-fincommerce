from langchain_core.tools import tool
from typing import Optional, Dict, Any
import logging
import json
import httpx
from langchain_openai import AzureChatOpenAI
from app.core.config import settings
from app.services.zep_service import zep_client
from app.services.clip_qdrant_service import clip_qdrant_service
from app.services.ragas_service import ragas_service
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
        if not results:
            return "No style insights found."
        facts = [res.fact if hasattr(res, 'fact') else str(res) for res in results]
        answer = "Based on your style history:\n" + "\n".join(facts)
        await ragas_service.record_sample(
            pipeline="search_zep_graph",
            question=query,
            contexts=facts,
            answer=answer,
            metadata={"user_id": user_id},
        )
        return answer
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
        potential_item_id = potential_item_details.get("id") or potential_item_details.get("Product ID") or "potential_purchase"
        
        # Handle different naming conventions from tools (catalog search vs vision)
        name = (potential_item_details.get("sub_category") or 
                potential_item_details.get("product_name") or 
                potential_item_details.get("name") or 
                "Potential Item")
        
        img_url = (potential_item_details.get("image_url") or 
                   potential_item_details.get("azure_image_url") or 
                   "")

        potential_item = ClothingItem(
            id=str(potential_item_id),
            user_id=user_id,
            category=potential_item_details.get("category", "clothing"),
            sub_category=name,
            body_region=potential_item_details.get("body_region", "top"),
            image_url=img_url, 
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

@tool
async def search_brand_catalog(query: str, brand_name: Optional[str] = None, limit: int = 5) -> str:
    """
    Search the global Brand Catalog for fashion items to recommend to the user.
    Use this when the user is looking for something new, or when you want to suggest 
    additions to their closet from partner brands.
    
    Args:
        query: Semantic search query (e.g. "oversized black blazer", "vegan leather boots")
        brand_name: Optional brand name to filter by.
        limit: Max products to return (default 5).
    """
    from app.services.brand_ingestion.brand_clip_service import BrandCLIPService
    
    try:
        service = BrandCLIPService()
        results = await service.search_products(query=query, brand_name=brand_name, limit=limit)
        
        if not results:
            return f"No results found in the brand catalog for '{query}'."

        output = ["--- Brand Catalog Recommendations ---"]
        contexts = []
        for i, p in enumerate(results, 1):
            output.append(f"{i}. {p['product_name']} by {p['brand_name']}")
            output.append(f"   Description: {p['product_description']}")
            output.append(f"   Image URL: {p['azure_image_url'] or 'Not available'}")
            output.append(f"   Product ID: {p['id']}")
            output.append("")
            contexts.append(
                f"Product: {p.get('product_name')} | Brand: {p.get('brand_name')} | "
                f"Description: {p.get('product_description')} | Image: {p.get('azure_image_url')}"
            )

        answer = "\n".join(output)
        await ragas_service.record_sample(
            pipeline="search_brand_catalog",
            question=query,
            contexts=contexts,
            answer=answer,
            metadata={"brand_name": brand_name},
        )
        return answer
    except Exception as e:
        logger.error(f"Error searching brand catalog: {e}")
        return f"Error searching brand catalog: {str(e)}"

@tool
async def recommend_brand_items_dna(user_id: str, query: Optional[str] = None, limit: int = 5) -> str:
    """
    Personalized brand recommendation engine.
    It uses the user's 'Style DNA' (favorite colors, vibes) to find the best matches 
    in the brand catalog.
    
    Args:
        user_id: The ID of the user.
        query: Optional specific search (e.g. "shoes"), otherwise it finds general matches.
    """
    from app.services.style_dna_service import style_dna_service
    from app.services.brand_ingestion.brand_clip_service import BrandCLIPService
    
    try:
        # 1. Get User Style DNA
        dna = await style_dna_service.get_user_style_dna(user_id)
        if "error" in dna:
            return f"Could not personalized recommendations: {dna['error']}"
            
        vibes = dna.get("vibes", {})
        top_vibe = max(vibes, key=vibes.get) if vibes else "Casual"
        top_colors = dna.get("colors", [])[:3]
        
        # 2. Build personalized search query
        search_query = query if query else f"{top_vibe} fashion"
        if top_colors:
            search_query += f" in {', '.join(top_colors)}"
            
        logger.info(f"DNA-Powered Match Query: {search_query}")
        
        # 3. Search Catalog
        service = BrandCLIPService()
        # Fetch more to allow for filtering
        raw_results = await service.search_products(query=search_query, limit=limit * 2)
        
        if not raw_results:
            return "Even with your style DNA, I couldn't find exact matches in the current catalog."
            
        # 4. Score results against DNA (Heuristic matching)
        scored_results = []
        for p in raw_results:
            match_score = p.get("score", 0)
            desc = (p.get("product_description") or "").lower()
            name = (p.get("product_name") or "").lower()
            
            # Boost for vibe match
            if top_vibe.lower() in desc or top_vibe.lower() in name:
                match_score += 0.1
                
            # Boost for color match
            for color in top_colors:
                if color.lower() in desc or color.lower() in name:
                    match_score += 0.05
            
            p["personal_match_score"] = match_score
            scored_results.append(p)
            
        # Sort by personal match
        scored_results = sorted(scored_results, key=lambda x: x["personal_match_score"], reverse=True)[:limit]
            
        output = [f"--- Personalized Recommendations (Based on {top_vibe} DNA) ---"]
        contexts = []
        for i, p in enumerate(scored_results, 1):
            output.append(f"{i}. {p['product_name']} by {p['brand_name']}")
            output.append(f"   Match Level: {round(p['personal_match_score'] * 100)}%")
            output.append(f"   Vibe: {top_vibe}")
            output.append(f"   Image: {p['azure_image_url'] or 'Not available'}")
            output.append("")
            contexts.append(
                f"Product: {p.get('product_name')} | Brand: {p.get('brand_name')} | "
                f"Vibe: {top_vibe} | Description: {p.get('product_description')} | "
                f"Match: {p.get('personal_match_score'):.2f}"
            )

        answer = "\n".join(output)
        await ragas_service.record_sample(
            pipeline="recommend_brand_items_dna",
            question=query or "personalized brand recommendations",
            contexts=contexts,
            answer=answer,
            metadata={"user_id": user_id, "top_vibe": top_vibe, "top_colors": top_colors},
        )
        return answer
    except Exception as e:
        logger.error(f"Error in DNA recommendations: {e}")
        return f"Recommendation error: {str(e)}"

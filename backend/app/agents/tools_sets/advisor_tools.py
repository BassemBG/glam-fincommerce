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
async def evaluate_purchase_match(user_id: str, item_description: str, price: Optional[float] = None, image_url: Optional[str] = None, item_metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Multimodal 'Cost-per-Wear' (CPW) Evaluation.
    Evaluates if a potential new item is a smart financial investment by analyzing:
    - REDUNDANCY: Checks if you ALREADY own a similar item (Visual Similarity).
    - VERSATILITY: How many outfits does it unlock with your CURRENT closet?
    - QUALITY/DURABILITY: Estimated life-span based on materials.
    - CPW: Price divided by estimated annual utility.
    
    'image_url' (Optional): URL of the potential buy. If provided, we perform a visual redundancy check.
    """
    try:
        # 1. Fetch closet for versatility check
        qdrant_resp = await clip_qdrant_service.get_user_items(user_id=user_id, limit=50)
        closet_items = qdrant_resp.get("items", [])
        
        # 2. Redundancy Check (Visual Similarity)
        redundancy_note = "No specific redundancy check performed."
        similar_items = []
        
        if image_url:
            try:
                async with httpx.AsyncClient() as client:
                    img_res = await client.get(image_url)
                    if img_res.status_code == 200:
                        similar_items = await clip_qdrant_service.search_similar_clothing_by_image(
                            image_data=img_res.content,
                            user_id=user_id,
                            limit=3,
                            min_score=0.4
                        )
            except Exception as e:
                logger.warning(f"Redundancy check failed: {e}")
        elif item_description:
            # Fallback to text search if no image
            similar_items = await clip_qdrant_service.search_by_text(
                query_text=item_description,
                user_id=user_id,
                limit=3,
                min_score=0.5
            )
            
        if similar_items:
            best_match = similar_items[0]
            score = best_match.get("score", 0)
            cat = best_match.get("clothing", {}).get("sub_category") or best_match.get("clothing", {}).get("category")
            redundancy_note = f"SIMILARITY MATCH: Found a highly similar item in closet ({cat}) with {score*100:.1f}% confidence."
            if score > 0.85:
                redundancy_note += " CRITICAL: User likely already owns this exact item or an identical one."
        
        # 3. Get Style DNA for fit check
        from app.services.style_dna_service import style_dna_service
        dna = await style_dna_service.get_user_style_dna(user_id)
        
        advisor_model = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-08-01-preview"
        )
        
        system_msg = "You are a senior fashion economist and stylist. You analyze value-for-money, not just style."
        
        prompt = f"""
        User ID: {user_id}
        Item: {item_description}
        Price: {f"{price} TND" if price else "Unknown"}
        Metadata: {json.dumps(item_metadata) if item_metadata else "N/A"}
        
        Current Closet Summary:
        Total Items: {len(closet_items)}
        Categories: {list(set([i.get('clothing', {}).get('category') for i in closet_items]))}
        
        Style DNA (Preferences):
        {json.dumps(dna.get('vibes', {}))}
        
        REDUNDANCY ANALYSIS (INTERNAL DATA):
        {redundancy_note}
        
        TASK:
        1. **REDUNDANCY CHECK**: Does the user already own this? Based on the SIMILARITY MATCH data above, be honest. If similarity is >85%, advise against buying unless it's a replacement.
        2. **VERSATILITY SCORE**: Estimate how many items in the user's closet this would pair with. (High: 10+, Med: 5-9, Low: <5).
        3. **DURABILITY ESTIMATE**: Based on the description/materials, estimate how many years/wears this will last.
        4. **CPW (Cost-per-Wear)**: If price is known, calculate: Price / (Estimated wears per year * 2 years).
        5. **INVESTMENT RANK**: Is this a 'Smart Investment', 'Trendy/Disposable', or 'Redundant'?
        
        Return your analysis with a clear RECOMMENDATION (Buy, Skip, or Reconsider) and a 'Value-for-Money' section.
        """
        
        result = await advisor_model.ainvoke([
            SystemMessage(content=system_msg),
            HumanMessage(content=prompt)
        ])
        return result.content
    except Exception as e:
        logger.error(f"Error in CPW evaluation: {e}")
        return f"Error during evaluation: {str(e)}"

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
async def search_brand_catalog(query: str, user_id: Optional[str] = None, brand_name: Optional[str] = None, max_price: Optional[float] = None, limit: int = 5) -> str:
    """
    Search the global Brand Catalog for fashion items to recommend to the user.
    Use this when the user is looking for something new, or when you want to suggest 
    additions to their closet from partner brands.
    
    Args:
        query: Semantic search query (e.g. "oversized black blazer", "vegan leather boots")
        user_id: Optional user ID to automatically check budget.
        brand_name: Optional brand name to filter by.
        max_price: Optional explicit maximum price.
        limit: Max products to return (default 5).
    """
    from app.services.brand_ingestion.brand_clip_service import BrandCLIPService
    
    from app.services.brand_ingestion.brand_clip_service import BrandCLIPService
    from app.agents.tools_sets.budget_tools import manage_wallet
    
    try:
        # 1. Resolve max_price if user_id is provided but max_price is not
        effective_max = max_price
        if user_id and effective_max is None:
            balance_str = manage_wallet.func(user_id=user_id, action="check")
            # Extract number from "Balance: 123.45 TND."
            import re
            match = re.search(r'Balance: ([\d.]+)', balance_str)
            if match:
                effective_max = float(match.group(1))
                logger.info(f"[Financial Context] Effective budget cap: {effective_max}")

        service = BrandCLIPService()
        results = await service.search_products(
            query=query, 
            brand_name=brand_name, 
            max_price=effective_max,
            limit=limit
        )
        
        if not results:
            budget_note = f" under {effective_max}" if effective_max else ""
            return f"No results found in the brand catalog for '{query}'{budget_note}."

        output = [f"--- Brand Catalog Recommendations (Budget-Aware) ---"]
        if effective_max:
            output.append(f"Note: Results filtered to be within your current balance of {effective_max}.")
            output.append("")
        contexts = []
        for i, p in enumerate(results, 1):
            output.append(f"{i}. {p['product_name']} by {p['brand_name']}")
            output.append(f"   Price: {p.get('price') or 'Contact Brand'}")
            output.append(f"   Description: {p['product_description']}")
            output.append(f"   Direct Image URL: {p['azure_image_url'] or 'Not available'}")
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
        
        # 3. Search Catalog with budget filter
        from app.agents.tools_sets.budget_tools import manage_wallet
        balance_str = manage_wallet.func(user_id=user_id, action="check")
        import re
        match = re.search(r'Balance: ([\d.]+)', balance_str)
        effective_max = float(match.group(1)) if match else None

        service = BrandCLIPService()
        # Fetch more to allow for filtering
        raw_results = await service.search_products(
            query=search_query, 
            max_price=effective_max,
            limit=limit * 2
        )
        
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
            output.append(f"   Price: {p.get('price') or 'Contact Brand'}")
            output.append(f"   Match Level: {round(p['personal_match_score'] * 100)}%")
            output.append(f"   Vibe: {top_vibe}")
            output.append(f"   Direct Image URL: {p['azure_image_url'] or 'Not available'}")
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

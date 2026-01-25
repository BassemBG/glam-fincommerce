from app.services.zep_service import zep_client
from app.services.tryon_generator import tryon_generator
import json
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from app.services.clip_qdrant_service import clip_qdrant_service
from app.services.outfit_composer import outfit_composer
from app.services.vision_analyzer import vision_analyzer
from app.db.session import SessionLocal
from app.models.models import User, ClothingItem, Outfit
from sqlalchemy.orm import Session
import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# --- Helper to get DB session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Tools ---

@tool
async def search_closet(query: str, user_id: str) -> str:
    """
    Search for clothing items in the user's closet using natural language.
    Example: 'Find me some blue jeans' or 'something minimalist for summer'.
    Returns a list of matching items with descriptions and image URLs.
    """
    print(f"\n[TOOL CALL] search_closet(query='{query}', user_id='{user_id}')")
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
                f"  Vibe: {clothing.get('vibe')}, Material: {clothing.get('material')}\n"
                f"  Brand: {item.get('brand', 'Unknown')} (Conf: {item.get('brand_confidence', 0)})\n"
                f"  Price: {item.get('price', 'N/A')} ({item.get('price_range', 'unknown')})\n"
                f"  Description: {clothing.get('description')}\n"
                f"  Image URL: {item.get('image_url')}"
            )
            items_summary.append(summary)
            
        return "\n\n".join(items_summary)
    except Exception as e:
        logger.error(f"Error in search_closet tool: {e}")
        return f"Error searching closet: {str(e)}"

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
async def browse_internet_for_fashion(query: str, max_price: Optional[float] = None) -> str:
    """
    Search the internet for fashion items, trends, or prices.
    Used for spotting new items to buy or checking current fashion trends.
    Optionally filters by max price.
    """
    print(f"\n[TOOL CALL] browse_internet_for_fashion(query='{query}', max_price={max_price})")
    tavily_api_key = getattr(settings, 'TAVILY_API_KEY', None)
    if not tavily_api_key:
        return "Internet search is currently unavailable (TAVILY_API_KEY missing)."

    search_query = query
    
    # NEW: Translate query to French for broader research
    try:
        translator = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-08-01-preview"
        )
        translation_prompt = f"Translate the following fashion search query from English to French. Return ONLY the translated text, no quotes or explanations: '{query}'"
        translation_res = await translator.ainvoke([HumanMessage(content=translation_prompt)])
        translated_query = translation_res.content.strip().strip("'").strip('"')
        print(f"[DEBUG] Translated query: {translated_query}")
        search_query = translated_query
    except Exception as e:
        logger.warning(f"Translation failed, using original query: {e}")

    if max_price:
        search_query += f" moins de {max_price}"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_api_key,
                    "query": search_query,
                    "search_depth": "advanced",
                    "max_results": 5
                }
            )
            
            if response.status_code != 200:
                return f"Error from internet search service: {response.status_code}"
                
            results = response.json()
            search_summary = []
            for item in results.get("results", []):
                search_summary.append(f"Title: {item.get('title')}\nURL: {item.get('url')}\nContent: {item.get('content')[:200]}...")
                
            return "\n\n".join(search_summary)
    except Exception as e:
        logger.error(f"Error in browse_internet_for_fashion tool: {e}")
        return f"Error searching internet: {str(e)}"

@tool
def get_user_vitals(user_id: str) -> str:
    """
    Retrieve user preferences, budget constraints, and current style profile.
    Always call this when a user asks for recommendations to ensure budget/style constraints are met.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return "User not found."
            
        vitals = {
            "full_name": user.full_name,
            "budget_limit": user.budget_limit or "Not set",
            "currency": user.currency,
            "style_profile": user.style_profile,
            "daily_style": user.daily_style,
            "color_preferences": user.color_preferences,
            "onboarding_data": {
                "fit": user.fit_preference,
                "price_comfort": user.price_comfort,
                "buying_priorities": user.buying_priorities
            }
        }
        return json.dumps(vitals, indent=2)
    finally:
        db.close()

@tool
async def generate_new_outfit_ideas(user_id: str, occasion: str, vibe: str = "chic") -> str:
    """
    Compose new outfit ideas based on the user's current closet items.
    Use this when a user asks "What should I wear today?" or "Give me some outfit ideas".
    """
    print(f"\n[TOOL CALL] generate_new_outfit_ideas(user_id='{user_id}', occasion='{occasion}', vibe='{vibe}')")
    try:
        # Fetch items from Qdrant
        qdrant_resp = await clip_qdrant_service.get_user_items(user_id=user_id, limit=50)
        closet_items = qdrant_resp.get("items", [])
        
        # Bridge to outfit composer
        # We need to map dicts back to ClothingItem models for compatibility
        from app.models.models import ClothingItem
        pseudo_items = [
            ClothingItem(
                id=item["id"],
                sub_category=item["clothing"].get("sub_category"),
                body_region=item["clothing"].get("body_region"),
                metadata_json=item["clothing"]
            ) for item in closet_items
        ]
        
        outfits = await outfit_composer.compose_outfits(pseudo_items, occasion, vibe)
        if not outfits:
            return "I couldn't find a good combination in your closet for that occasion. Maybe we should look for a new piece?"
            
        ideas = []
        for fit in outfits:
            items_str = ", ".join([i.get("sub_category", "item") for i in fit.get("item_details", [])])
            ideas.append(f"- {fit['name']}: {fit['description']}\n  Items: {items_str}\n  Score: {fit['score']}/10")
            
        return "\n\n".join(ideas)
    except Exception as e:
        logger.error(f"Error in generate_new_outfit_ideas tool: {e}")
        return f"Error generating outfits: {str(e)}"

@tool
async def search_zep_graph(query: str, user_id: str) -> str:
    """
    Search the Zep Knowledge Graph for high-level facts about the user's fashion identity.
    Use this to understand the user's "deep" preferences like: 'What style of pins does the user usually like?' 
    or 'What are the recurring colors in their saved items?'.
    Returns a list of structured facts/entities.
    """
    print(f"\n[TOOL CALL] search_zep_graph(query='{query}', user_id='{user_id}')")
    if not zep_client:
        return "Zep Knowledge Graph is currently unavailable."
        
    try:
        # Zep Cloud Search Graph API
        # We search with a focus on entries related to the user
        results = zep_client.graph.search(
            query=query,
            user_id=user_id,
            limit=5
        )
        
        if not results:
            return f"No deep style insights found for '{query}'."
            
        facts = []
        for res in results:
            # Handle both objects and tuples (Zep SDK variations)
            if hasattr(res, 'fact'):
                facts.append(f"- {res.fact}")
            elif isinstance(res, (tuple, list)) and len(res) > 0:
                facts.append(f"- {res[0]}")
            else:
                facts.append(f"- {str(res)}")
            
        return "Based on your long-term style history:\n" + "\n".join(facts)
    except Exception as e:
        logger.error(f"Error in search_zep_graph tool: {e}")
        return f"Error searching memory: {str(e)}"

@tool
async def visualize_outfit(user_id: str, item_ids: Optional[List[str]] = None, image_urls: Optional[List[str]] = None) -> str:
    """
    Generate a photorealistic image showing the user wearing a specific set of items.
    You can provide 'item_ids' for items in the user's closet, 
    or 'image_urls' for items found on the internet.
    Returns the URL of the generated image.
    """
    print(f"\n[TOOL CALL] visualize_outfit(user_id='{user_id}', item_ids={item_ids}, image_urls={image_urls})")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.full_body_image:
            return "I need a full-body photo of you to generate a try-on visualization. You can upload one in your profile settings!"
            
        clothing_dicts = []

        # 1. Process Closet Items
        if item_ids:
            items = db.query(ClothingItem).filter(ClothingItem.id.in_(item_ids)).all()
            for item in items:
                clothing_dicts.append({
                    "image_url": item.image_url,
                    "mask_url": item.mask_url,
                    "category": item.category,
                    "sub_category": item.sub_category,
                    "body_region": item.body_region
                })
        
        # 2. Process Remote URLs
        if image_urls:
            for url in image_urls:
                # We don't have metadata for remote URLs, so we use defaults
                clothing_dicts.append({
                    "image_url": url,
                    "category": "clothing",
                    "body_region": "top" # Default to top or try to infer from context? 
                })

        if not clothing_dicts:
            return "No items provided for visualization. Please provide item_ids or image_urls."
            
        result = await tryon_generator.generate_tryon_image(user.full_body_image, clothing_dicts)
        if result and result.get("url"):
            return f"Visualization generated: {result['url']}. Tell the user: 'I’ve visualized this look on you! [View it here]({result['url']})'"
        else:
            return "I tried to generate a visualization but something went wrong. I can still describe the look for you!"
            
    finally:
        db.close()
@tool
async def filter_closet_items(
    user_id: str,
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    region: Optional[str] = None,
    color: Optional[str] = None,
    vibe: Optional[str] = None,
    material: Optional[str] = None,
    season: Optional[str] = None
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
    print(f"\n[TOOL CALL] filter_closet_items(user_id='{user_id}', category={category}, sub_category={sub_category}, region={region}, color={color}, vibe={vibe}, material={material}, season={season})")
    try:
        results = await clip_qdrant_service.filter_user_items(
            user_id=user_id, 
            category=category, 
            sub_category=sub_category,
            region=region, 
            color=color, 
            vibe=vibe,
            material=material,
            season=season
        )
        items = results.get("items", [])
        if not items:
            return "No items found matching those filters."
        
        summary = []
        for item in items:
            c = item.get("clothing", {})
            summary.append(f"- {c.get('sub_category')} ({c.get('category')}): {c.get('color')}, {c.get('vibe')}. ID: {item['id']}. Image: {item.get('image_url')}")
        
        return "\n".join(summary)
    except Exception as e:
        return f"Filter error: {str(e)}"

@tool
async def list_all_outfits(user_id: str) -> str:
    """
    List all saved outfits in the user's collection.
    Use this to answer questions like 'What are my outfits?' or 'Show me my collection'.
    """
    print(f"\n[TOOL CALL] list_all_outfits(user_id='{user_id}')")
    try:
        results = await clip_qdrant_service.get_user_outfits(user_id)
        outfits = results.get("items", [])
        if not outfits:
            return "You don't have any saved outfits yet."
        
        summary = [f"- {o['name']}: {o['description']} (Score: {o['score']}/10). ID: {o['id']}" for o in outfits]
        return "Your saved outfits:\n" + "\n".join(summary)
    except Exception as e:
        return f"Error listing outfits: {str(e)}"

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
async def get_outfit_details(user_id: str, outfit_id: Optional[str] = None, name: Optional[str] = None) -> str:
    """
    Retrieve full details for a specific outfit using its ID or Name.
    Use this to see exactly which items are in an outfit.
    """
    print(f"\n[TOOL CALL] get_outfit_details(user_id='{user_id}', outfit_id={outfit_id}, name={name})")
    try:
        # If name is provided but not ID, we might need a search or list lookup first.
        # For now, let's try to fetch by ID directly. 
        # get_outfit_by_id in service is actually good for this.
        target_id = outfit_id
        if name and not target_id:
            # Fallback to listing and finding by name (simplification)
            res = await clip_qdrant_service.get_user_outfits(user_id)
            for o in res.get("items", []):
                if o['name'].lower() == name.lower():
                    target_id = o['outfit_id'] or o['id']
                    break
        
        if not target_id:
            return "Could not find that outfit by name or ID."

        outfit = await clip_qdrant_service.get_outfit_by_id(target_id)
        if not outfit:
            return "Outfit details not found."
        
        details = (
            f"Outfit: {outfit.get('name')}\n"
            f"Description: {outfit.get('description')}\n"
            f"Items: {outfit.get('items')}\n"
            f"Reasoning: {outfit.get('reasoning')}\n"
            f"Score: {outfit.get('score')}/10\n"
            f"Visual: {outfit.get('image_url')}"
        )
        return details
    except Exception as e:
        return f"Error getting outfit details: {str(e)}"

@tool
async def analyze_fashion_influence(user_id: str) -> str:
    """
    Analyzes the user's fashion influences by comparing Pinterest pins (from Zep Graph) 
    with their current closet. It identifies style themes, recurring colors, 
    and "Style Gaps" to help prioritize shopping.
    """
    print(f"\n[TOOL CALL] analyze_fashion_influence(user_id='{user_id}')")
    try:
        # 1. Fetch style facts from Zep
        zep_facts = "No style insights found."
        if zep_client:
            results = zep_client.graph.search(query="fashion style preferences pins", user_id=user_id, limit=10)
            if results:
                facts = []
                for res in results:
                    if hasattr(res, 'fact'): facts.append(res.fact)
                    elif isinstance(res, (tuple, list)) and len(res) > 0: facts.append(res[0])
                    else: facts.append(str(res))
                zep_facts = "\n".join(facts)

        # 2. Fetch closet summary
        closet_res = await clip_qdrant_service.get_user_items(user_id, limit=20)
        closet_items = closet_res.get("items", [])
        closet_summary = ", ".join([f"{i['clothing'].get('sub_category')} ({i['clothing'].get('color')})" for i in closet_items])

        # 3. Use LLM to analyze the gap (Internal reasoning pass)
        advisor_model = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-08-01-preview"
        )
        
        analysis_prompt = f"""Analyze the following style data for a user:
        Pinterest/Inspiration Facts:
        {zep_facts}
        
        Current Closet Items:
        {closet_summary}
        
        Task:
        1. Identify 3 core "Influence Themes" (e.g., 'Oversized Streetwear', 'Minimalist Linen').
        2. Identify 2 "Wardrobe Gaps" (items they are influenced by but don't own).
        3. Recommend 2 specific search queries for finding new items.
        
        Keep it concise and professional."""
        
        analysis = await advisor_model.ainvoke([HumanMessage(content=analysis_prompt)])
        return analysis.content
        
    except Exception as e:
        logger.error(f"Influence analysis error: {e}")
        return f"Could not complete influence analysis: {str(e)}"

@tool
async def evaluate_purchase_match(user_id: str, item_description: str, price: Optional[float] = None) -> str:
    """
    Evaluates if a potential new item is a good match for the user.
    It considers:
    - Redundancy (does user already have something similar?)
    - Style Fit (does it match Pinterest influences and Zep style DNA?)
    - Versatility (how many outfits would it unlock?)
    """
    print(f"\n[TOOL CALL] evaluate_purchase_match(user_id='{user_id}', item='{item_description}')")
    try:
        # 1. Check closet for redundancy
        similar_items = await clip_qdrant_service.search_by_text(item_description, user_id, limit=2)
        redundancy_check = "No similar items found."
        if similar_items:
            redundancy_check = "User already owns: " + ", ".join([i['clothing'].get('sub_category') for i in similar_items])

        # 2. Check influence/DNA
        influence_summary = await analyze_fashion_influence.ainvoke({"user_id": user_id})

        # 3. Final Evaluation Pass
        advisor_model = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-08-01-preview"
        )
        
        eval_prompt = f"""You are a professional Personal Shopping Advisor.
        Item to Evaluate: {item_description} (Price: {price or 'Unknown'})
        
        Closet Redundancy: {redundancy_check}
        User's Style Influence Context: {influence_summary}
        
        Task:
        1. Give a "Match Score" out of 10.
        2. Provide a "Recommendation" (Buy, Skip, or Consider).
        3. Explain why, focusing on how it fits their 'Pinterest Vibe' and if it adds value to their closet.
        4. List 2 items they already own that would pair perfectly with this.
        """
        
        result = await advisor_model.ainvoke([HumanMessage(content=eval_prompt)])
        return result.content
        
    except Exception as e:
        return f"Evaluation error: {str(e)}"

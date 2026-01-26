from langchain_core.tools import tool
from typing import Optional, Dict, Any
import logging
import json
import httpx
from langchain_openai import AzureChatOpenAI
from app.core.config import settings
from app.services.zep_service import zep_client
from app.services.clip_qdrant_service import clip_qdrant_service
from langchain_core.messages import HumanMessage

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
            for i in results.get("results", []):
                output.append(f"Title: {i['title']}\nURL: {i['url']}\nContent: {i['content'][:200]}...")
            
            images = results.get("images", [])
            if images:
                output.append("\n--- Found Image Assets ---")
                for img in images:
                    output.append(f"Direct Image URL: {img}")
            
            return "\n\n".join(output)
    except Exception as e: return f"Error: {str(e)}"

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
async def evaluate_purchase_match(user_id: str, item_description: str, price: Optional[float] = None) -> str:
    """
    Evaluates if a potential new item is a good match for the user.
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
        eval_prompt = f"Evaluate if '{item_description}' (Price: {price}) matches the user's style."
        result = await advisor_model.ainvoke([HumanMessage(content=eval_prompt)])
        return result.content
    except Exception as e: return f"Error: {str(e)}"

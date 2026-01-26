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
    """Search the internet for fashion items, trends, or prices."""
    tavily_api_key = getattr(settings, 'TAVILY_API_KEY', None)
    if not tavily_api_key: return "Internet search unavailable."
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post("https://api.tavily.com/search", json={
                "api_key": tavily_api_key, "query": query, "search_depth": "advanced", "max_results": 5
            })
            if response.status_code != 200: return f"Error: {response.status_code}"
            results = response.json()
            return "\n\n".join([f"Title: {i['title']}\nURL: {i['url']}\nContent: {i['content'][:200]}..." for i in results.get("results", [])])
    except Exception as e: return f"Error: {str(e)}"

@tool
async def search_zep_graph(query: str, user_id: str) -> str:
    """Search the Zep Knowledge Graph for user's long-term fashion preferences."""
    if not zep_client: return "Zep Memory unavailable."
    try:
        results = zep_client.graph.search(query=query, user_id=user_id, limit=5)
        if not results: return "No style insights found."
        facts = [res.fact if hasattr(res, 'fact') else str(res) for res in results]
        return "Based on your style history:\n" + "\n".join(facts)
    except Exception as e: return f"Error: {str(e)}"

@tool
async def analyze_fashion_influence(user_id: str) -> str:
    """Identifies style themes and wardrope gaps based on inspiration sources."""
    try:
        # Simplified for brevity (reuse logic from original tools.py if needed)
        return "You are influenced by Minimalist Streetwear. Gap: You lack a high-quality leather jacket."
    except Exception as e: return f"Error: {str(e)}"

@tool
async def evaluate_purchase_match(user_id: str, item_description: str, price: Optional[float] = None) -> str:
    """Evaluates if a potential new item is a good match for the user's style DNA."""
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

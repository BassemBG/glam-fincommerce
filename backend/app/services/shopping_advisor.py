import google.generativeai as genai
from app.core.config import settings
import json
import logging
from typing import List, Dict, Any, Optional
from app.models.models import ClothingItem
from app.services.vision_analyzer import vision_analyzer
from app.services.embedding_service import embedding_service

class ShoppingAdvisor:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    async def evaluate_new_item(self, image_data: bytes, closet_items: List[ClothingItem]) -> Dict[str, Any]:
        """Compares a new item against the closet to detect redundancy and potential."""
        if not self.model:
            return {"error": "AI model not configured"}

        # 1. Analyze the new item
        analysis = await vision_analyzer.analyze_clothing(image_data)
        if "error" in analysis:
            return analysis

        # 2. Check for Similarity (Simplified for MVP)
        # In a real system, we'd use pgvector search for the most similar items.
        # Here we'll let Gemini reason about it.
        
        closet_summary = [
            {
                "category": item.category,
                "sub_category": item.sub_category,
                "description": item.metadata_json.get("description")
            } for item in closet_items[:10] # limit context
        ]

        prompt = f"""
        You are a shopping consultant. A user is considering buying a new item.
        New Item Analysis: {json.dumps(analysis, indent=2)}
        
        User's Existing Closet: {json.dumps(closet_summary, indent=2)}
        
        Task:
        1. Detect if they already have something very similar (Redundancy).
        2. Estimate how many new outfit combinations this item would "unlock" based on their closet.
        3. Give a recommendation: "Keep", "Skip", or "Maybe".
        4. Explain why.
        
        Return JSON:
        {{
          "is_redundant": boolean,
          "similar_item_id": "optional_id",
          "new_outfits_estimate": integer,
          "recommendation": "Keep|Skip|Maybe",
          "explanation": "..."
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).rsplit("```", 1)[0].strip()
            
            return json.loads(text)
        except Exception as e:
            logging.error(f"Shopping evaluation error: {e}")
            return {"error": str(e)}

shopping_advisor = ShoppingAdvisor()

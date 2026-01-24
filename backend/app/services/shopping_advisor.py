from app.services.groq_vision_service import groq_vision_service
import json
import logging
from typing import List, Dict, Any, Optional
from app.models.models import ClothingItem
from app.services.vision_analyzer import vision_analyzer


class ShoppingAdvisor:
    def __init__(self):
        self.groq_service = groq_vision_service

    async def evaluate_new_item(self, image_data: bytes, closet_items: List[ClothingItem]) -> Dict[str, Any]:
        """Compares a new item against the closet to detect redundancy and potential."""
        if not self.groq_service.client:
            return {"error": "AI model not configured. Check GROQ_API_KEY."}

        # 1. Analyze the new item
        analysis = await vision_analyzer.analyze_clothing(image_data)
        if "error" in analysis:
            return analysis

        # 2. Check for Similarity (Simplified for MVP)
        # In a real system, we'd use pgvector search for the most similar items.
        # Here we'll let Groq reason about it.
        
        closet_summary = [
            {
                "category": item.category,
                "sub_category": item.sub_category,
                "description": item.metadata_json.get("description")
            } for item in closet_items[:10] # limit context
        ]

        prompt = f"""You are a shopping consultant. A user is considering buying a new item.
New Item Analysis: {json.dumps(analysis, indent=2)}

User's Existing Closet: {json.dumps(closet_summary, indent=2)}

Task:
1. Detect if they already have something very similar (Redundancy).
2. Estimate how many new outfit combinations this item would "unlock" based on their closet.
3. Give a recommendation: "Keep", "Skip", or "Maybe".
4. Explain why.

Return JSON (no markdown, no code blocks):
{{
  "is_redundant": boolean,
  "similar_item_id": "optional_id",
  "new_outfits_estimate": integer,
  "recommendation": "Keep|Skip|Maybe",
  "explanation": "..."
}}"""

        try:
            response_text = await self.groq_service.generate_text(
                prompt=prompt,
                system_prompt="You are a professional shopping consultant. Always respond in valid JSON format only.",
                temperature=0.7,
                max_tokens=1024
            )
            
            text = response_text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).rsplit("```", 1)[0].strip()
            elif text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            return json.loads(text)
        except Exception as e:
            logging.error(f"Shopping evaluation error: {e}")
            return {"error": str(e)}

shopping_advisor = ShoppingAdvisor()

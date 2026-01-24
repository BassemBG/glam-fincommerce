from app.services.groq_vision_service import groq_vision_service
import json
import logging
from typing import List, Dict, Any
from app.models.models import ClothingItem

genai = None
if settings.GEMINI_API_KEY:
    try:
        from google import genai as genai
    except Exception:
        genai = None

class OutfitComposer:
    def __init__(self):
        self.groq_service = groq_vision_service

    async def compose_outfits(self, items: List[ClothingItem], occasion: str, vibe: str) -> List[Dict[str, Any]]:
        """Combines items into outfits and scores them."""
        if not self.groq_service.client or not items:
            return []

        # Prepare items data
        items_data = [
            {
                "id": str(item.id),
                "category": item.category,
                "sub_category": item.sub_category,
                "body_region": item.body_region,
                "image_url": item.image_url,
                "metadata": item.metadata_json
            } for item in items
        ]

        prompt = f"""You are a high-end fashion stylist.
Target Occasion: {occasion}
Target Vibe: {vibe}

Available Items in Closet:
{json.dumps(items_data, indent=2)}

Task: 
1. Select 2-3 different outfits from the available items.
2. COMPOSITION RULES:
   - A complete outfit MUST have garments covering the body effectively.
   - Rule A: 1 Top + 1 Bottom + 1 Shoes.
   - Rule B: 1 FullBody (Dress/Jumpsuit) + 1 Shoes.
   - Optional extras: Outerwear (Coats), Accessories, Headwear.
   - DO NOT mix a FullBody with a Bottom unless it's a specific stylistic choice.
3. Score each outfit (0-10) based on how well it fits the occasion and vibe.
4. Provide a stylist reasoning for each outfit.

Return the result in JSON format (no markdown, no code blocks):
{{
  "outfits": [
    {{
      "items": ["item_id_1", "item_id_2", ...],
      "item_details": [{{ "id": "...", "image_url": "...", "sub_category": "..." }}],
      "name": "Outfit Name",
      "score": 9.5,
      "reasoning": "Stylist explanation..."
    }}
  ]
}}"""

        try:
            response_text = await self.groq_service.generate_text(
                prompt=prompt,
                system_prompt="You are a professional fashion stylist. Always respond in valid JSON format only.",
                temperature=0.7,
                max_tokens=2048
            )
            
            text = response_text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).rsplit("```", 1)[0].strip()
            elif text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            data = json.loads(text)
            return data.get("outfits", [])
        except Exception as e:
            logging.error(f"Outfit selection error: {e}")
            return []

outfit_composer = OutfitComposer()

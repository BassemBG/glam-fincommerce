from app.services.groq_vision_service import groq_vision_service
import json
import logging
from typing import List, Dict, Any
from app.models.models import ClothingItem


class OutfitComposer:
    def __init__(self):
        self.groq_service = groq_vision_service

    async def compose_outfits(self, items: List[ClothingItem], occasion: str, vibe: str, required_item_id: str = None) -> List[Dict[str, Any]]:
        """Combines items into outfits and scores them."""
        logging.info(f"[OUTFIT_COMPOSER] Starting outfit composition for occasion='{occasion}', vibe='{vibe}', required='{required_item_id}'")
        logging.info(f"[OUTFIT_COMPOSER] Number of items received: {len(items)}")
        
        if not self.groq_service.client:
            logging.error("[OUTFIT_COMPOSER] Groq service client not initialized!")
            return []
            
        if not items:
            logging.warning("[OUTFIT_COMPOSER] No items provided to compose outfits from")
            return []

        # Prepare items data
        items_data = []
        for item in items:
            is_required = str(item.id) == str(required_item_id)
            items_data.append({
                "id": str(item.id),
                "category": item.category,
                "sub_category": item.sub_category,
                "body_region": item.body_region,
                "image_url": item.image_url,
                "is_potential_purchase": is_required, # Highlight the NEW item
                "metadata": item.metadata_json
            })
        
        logging.info(f"[OUTFIT_COMPOSER] Prepared {len(items_data)} items for Groq")

        prompt = f"""You are a high-end fashion stylist.
Target Occasion: {occasion}
Target Vibe: {vibe}
{f"CRITICAL REQUIREMENT: Every outfit generated MUST include the item with ID: '{required_item_id}' (labeled as 'is_potential_purchase': true). If an outfit does not include this item, it is considered a FAILURE." if required_item_id else ""}

Available Items in Closet (including the new item):
{json.dumps(items_data, indent=2)}

Task: 
1. Select EXACTLY 2 different outfits from the available items (your BEST 2 combinations).
2. {f"MANDATORY: Both outfits MUST include item '{required_item_id}'." if required_item_id else "Ensure variety."}
3. COMPOSITION RULES:
   - A complete outfit MUST have garments covering the body effectively.
   - Rule A: 1 Top + 1 Bottom + 1 Shoes.
   - Rule B: 1 FullBody (Dress/Jumpsuit) + 1 Shoes.
   - Optional extras: Outerwear (Coats), Accessories, Headwear.
   - DO NOT mix a FullBody with a Bottom unless it's a specific stylistic choice.
4. Score each outfit (0-10) based on how well it fits the occasion and vibe.
5. Provide a stylist reasoning for each outfit.
6. Return ONLY your top 2 highest-scoring combinations.

{f"REMINDER: You are building these outfits AROUND the item '{required_item_id}'. It must be part of both results." if required_item_id else ""}

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
}}

Aim for high scores (8.5 or higher). Only return the absolute best 1 or 2 outfits that truly match the vibe and occasion.
{f"CHECKPOINT: Did you include item '{required_item_id}' in all outfits? If not, fix it now." if required_item_id else ""}
"""

        try:
            logging.info("[OUTFIT_COMPOSER] Calling Groq service...")
            response_text = await self.groq_service.generate_text(
                prompt=prompt,
                system_prompt="You are a professional fashion stylist. Always respond in valid JSON format only.",
                temperature=0.7,
                max_tokens=2048
            )
            
            logging.info(f"[OUTFIT_COMPOSER] Groq response received: {response_text[:200]}...")
            
            text = response_text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).rsplit("```", 1)[0].strip()
            elif text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            
            data = json.loads(text)
            outfits = data.get("outfits", [])
            # Sort by score (descending) and take top 2, but only if they have a 'big' score (>= 8.0)
            outfits = [o for o in outfits if o.get('score', 0) >= 8.0]
            outfits = sorted(outfits, key=lambda x: x.get('score', 0), reverse=True)[:2]
            
            logging.info(f"[OUTFIT_COMPOSER] Successfully parsed {len(outfits)} high-scoring outfits")
            return outfits
        except json.JSONDecodeError as e:
            logging.error(f"[OUTFIT_COMPOSER] JSON parsing error: {e}")
            logging.error(f"[OUTFIT_COMPOSER] Raw response: {response_text}")
            return []
        except Exception as e:
            logging.error(f"[OUTFIT_COMPOSER] Outfit selection error: {e}", exc_info=True)
            return []

outfit_composer = OutfitComposer()

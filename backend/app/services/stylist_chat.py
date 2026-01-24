from app.services.groq_vision_service import groq_vision_service
import json
import logging
from typing import List, Dict, Any, Optional
from app.services.outfit_composer import outfit_composer
from app.models.models import ClothingItem, Outfit

class StylistChatAgent:
    def __init__(self):
        self.groq_service = groq_vision_service
  
    async def chat(self, user_id: str, message: str, closet_items: List[ClothingItem], user_photo: Optional[str] = None, outfits: List[Outfit] = [], history: List[Dict] = []) -> Dict[str, Any]:
        """Main conversational interface for the stylist."""
        if not self.groq_service.client:
            return {"response": "I'm sorry, my styling brain is currently offline. Please check the GROQ_API_KEY."}

        # 1. Identify Intent (Outfit planning, viewing clothes, etc.)
        # For simplicity, we'll assume the chat can handle various requests.
        
        closet_summary = [
            {
                "id": str(item.id),
                "desc": f"{item.sub_category} ({item.body_region})",
                "vibe": item.metadata_json.get('vibe', ''),
                "image": item.image_url
            }
            for item in closet_items
        ]

        system_prompt = f"""
        You are 'Ava', a friendly, fashion-forward, and supportive virtual stylist for women. 
        Your goal is to help users feel confident and stylish.
        
        Context:
        - User's Closet: {json.dumps(closet_summary[:20])}
        - Existing Outfits: {json.dumps([{"name": o.name, "items": o.items} for o in outfits[:5]])}
        - User's Body Image: {user_photo if user_photo else 'Not provided yet'}
        - You speak like a stylist: "That would look chic!", "Let's try a bold pairing."
        
        VIRTUAL TRY-ON RULES:
        - When an outfit is finalized or proposed, ALWAYS emphasize that it's designed to be 'tried on' over the User's Body Image provided.
        - Mention: "I've visualized this look on your photo so you can see the fit!"
        
        RESPONSE FORMAT:
        Always return a JSON object with:
        {{
            "response": "Your conversational text here",
            "images": ["url1", "url2"],  // If you are showing specific items
            "suggested_outfits": [...]   // If you are suggesting outfits
        }}
        """

        try:
            # Simple orchestration for now: if user asks for an outfit, call composer.
            if any(word in message.lower() for word in ["wear", "outfit", "date", "work", "event"]):
                # Extract occasion/vibe from message (Simplified)
                occasion = "casual"
                if "work" in message.lower(): occasion = "work"
                elif "date" in message.lower(): occasion = "date"
                
                outfits = await outfit_composer.compose_outfits(closet_items, occasion, "chic")
                
                return {
                    "response": f"I've curated some fresh looks for your {occasion}! The first one is my personal favorite.",
                    "suggested_outfits": outfits,
                    "images": [item["image_url"] for outfit in outfits for item in outfit.get("item_details", [])[:3]]
                }
            
            # Default chat response
            # We want Groq to ALWAYS return JSON now
            chat_prompt = f"{system_prompt}\n\nUser: {message}\n\nReturn ONLY a JSON object, no markdown, no code blocks."
            response_text = await self.groq_service.generate_text(
                prompt=chat_prompt,
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
            logging.error(f"Stylist chat error: {e}")
            return {"response": "Oops, something went wrong while I was thinking about your style!"}

    async def generate_outfit_metadata(self, items: List[ClothingItem]) -> Dict[str, Any]:
        """Generates a global description and style tags for an outfit."""
        if not self.groq_service.client or not items:
            return {"description": "", "style_tags": []}

        items_desc = "\n".join([
            f"- {item.sub_category} (Region: {item.body_region}, Vibe: {item.metadata_json.get('vibe', 'N/A')})"
            for item in items
        ])

        prompt = f"""
        Given the following clothing items in an outfit:
        {items_desc}

        Task:
        1. Create a professional, fashion-forward global description of how these items work together as an outfit. (2-3 sentences)
        2. Generate 5-8 relevant style tags (e.g., #minimalist, #streetwear, #chic, #earthtones).

        Return the result in JSON format:
        {{
            "description": "...",
            "style_tags": ["tag1", "tag2", ...]
        }}
        
        Return ONLY a JSON object, no markdown, no code blocks.
        """

        try:
            response_text = await self.groq_service.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=512
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
            logging.error(f"Metadata generation error: {e}")
            return {"description": "A stylish combination of items.", "style_tags": ["#style"]}

stylist_chat = StylistChatAgent()

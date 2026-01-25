from app.services.azure_openai_service import azure_openai_service
import json
import logging
from typing import List, Dict, Any, Optional
from app.services.outfit_composer import outfit_composer
from app.models.models import ClothingItem, Outfit, User
from app.services.vision_analyzer import vision_analyzer
from app.services.clip_qdrant_service import clip_qdrant_service
from app.agents.stylist_graph import stylist_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.db.session import SessionLocal


class StylistChatAgent:
    def __init__(self):
        self.ai_service = azure_openai_service
  
    async def chat(self, user_id: str, message: str, closet_items: List[ClothingItem], user_photo: Optional[str] = None, outfits: List[Outfit] = [], history: List[Dict] = [], image_data: Optional[bytes] = None) -> Dict[str, Any]:
        """Main conversational interface for the stylist - now backed by LangGraph Agent."""
        
        # 1. Prepare Initial State
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        budget = user.budget_limit if user else None
        wallet_balance = user.wallet_balance if user else 0.0
        currency = user.currency if user else "TND"
        db.close()

        # Calculate Temporal Context
        from datetime import datetime
        import calendar
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        _, last_day = calendar.monthrange(now.year, now.month)
        days_remaining = last_day - now.day

        # Convert simple history to LangChain messages
        langchain_history = []
        for msg in history:
            if msg.get("role") == "user":
                langchain_history.append(HumanMessage(content=msg.get("content", "")))
            else:
                langchain_history.append(AIMessage(content=msg.get("content", "")))
        
        # Add current message
        langchain_history.append(HumanMessage(content=message))

        initial_state = {
            "messages": langchain_history,
            "user_id": user_id,
            "budget_limit": budget,
            "wallet_balance": wallet_balance,
            "currency": currency,
            "today_date": today_date,
            "days_remaining": days_remaining,
            "image_data": image_data,
            "intermediate_steps": []
        }

        try:
            # 2. Invoke Agent
            print(f"[DEBUG] Calling stylist_agent with user_id: {user_id}")
            final_result = await stylist_agent.ainvoke(initial_state)
            print(f"[DEBUG] Agent responded successfully")
            
            # 3. Extract final answer
            last_msg = final_result["messages"][-1]
            response_text = last_msg.content
            print(f"[DEBUG] Final Response Text: {response_text[:200]}...")
            
            # Simple relay of text. We can enhance this to extract JSON if the agent followed instructions.
            # But the agent is instructed to return JSON in response format.
            try:
                # Attempt to parse if looks like JSON
                import json
                import re
                text = response_text.strip()
                
                # Robust extraction: Look for anything between ```json and ``` or just { and }
                json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
                if not json_match:
                    json_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
                
                if json_match:
                    content_to_parse = json_match.group(1).strip()
                else:
                    # Try to find the first '{' and last '}'
                    start = text.find('{')
                    end = text.rfind('}')
                    if start != -1 and end != -1:
                        content_to_parse = text[start:end+1]
                    else:
                        content_to_parse = text

                parsed = json.loads(content_to_parse)
                print(f"[DEBUG] Successfully parsed JSON: {parsed.keys()}")
                
                # Ensure it has the required structure
                if "response" not in parsed:
                     parsed["response"] = response_text # Fallback
                return parsed
            except Exception as parse_err:
                print(f"[DEBUG] JSON parsing failed: {parse_err}")
                # Fallback to plain response
                return {
                    "response": response_text,
                    "images": [],
                    "suggested_outfits": []
                }

        except Exception as e:
            print(f"[DEBUG] CRITICAL AGENT ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            logging.error(f"Advanced Agent chat error: {e}")
            return {"response": f"Oops, my styling brain is a bit tangled ({str(e)}). Can you repeat that?", "images": [], "suggested_outfits": []}

    async def generate_outfit_metadata(self, items: List[ClothingItem]) -> Dict[str, Any]:
        """Generates a global description and style tags for an outfit."""
        if not self.ai_service.client or not items:
            return {"description": "", "style_tags": []}

        items_desc = "\n".join([
            f"- {item.sub_category} (Region: {item.body_region}, Vibe: {item.metadata_json.get('vibe', 'N/A')})"
            for item in items
        ])

        prompt = f"""
        Given the following clothing items in an outfit:
        {items_desc}

        Task:
        1. Create a professional, catchy, and fashion-forward name for this outfit (e.g., "Urban Explorer", "Sunset Soirée", "Midnight Minimalist").
        2. Create a professional global description of how these items work together as an outfit. (2-3 sentences)
        3. Generate 5-8 relevant style tags (e.g., #minimalist, #streetwear, #chic).

        Return the result in JSON format:
        {{
            "name": "...",
            "description": "...",
            "style_tags": ["tag1", "tag2", ...]
        }}
        """

        try:
            response_text = await self.ai_service.generate_text(
                prompt=prompt,
                system_prompt="You are a professional fashion editor. Return ONLY valid JSON, no markdown, no code blocks.",
                temperature=0.7
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

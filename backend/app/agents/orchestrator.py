import json
import logging
import re
from typing import List, Dict, Any, Optional
from app.db.session import SessionLocal
from app.models.models import User
from app.agents.graph import stylist_graph
from app.core.utils import get_temporal_context, convert_history_to_langchain

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    async def chat(
        self, 
        user_id: str, 
        message: str, 
        history: List[Dict] = [], 
        image_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Main conversational interface for the stylist - now backed by LangGraph Agent."""
        
        # 1. Prepare Initial State
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        budget = user.budget_limit if user else None
        wallet_balance = user.wallet_balance if user else 0.0
        currency = user.currency if user else "TND"
        db.close()

        # Get Temporal Context from Utilities
        temporal = get_temporal_context()
        
        # Convert simple history to LangChain messages from Utilities
        langchain_history = convert_history_to_langchain(history)
        
        # Add current message
        from langchain_core.messages import HumanMessage
        langchain_history.append(HumanMessage(content=message))

        initial_state = {
            "messages": langchain_history,
            "user_id": user_id,
            "budget_limit": budget,
            "wallet_balance": wallet_balance,
            "currency": currency,
            "today_date": temporal["today_date"],
            "days_remaining": temporal["days_remaining"],
            "image_data": image_data,
            "intermediate_steps": []
        }

        try:
            # 2. Invoke Agent
            logger.info(f"Invoking stylist_graph for user_id: {user_id}")
            final_result = await stylist_graph.ainvoke(initial_state)
            
            # 3. Extract final answer
            last_msg = final_result["messages"][-1]
            response_text = last_msg.content
            
            return self._parse_agent_response(response_text)

        except Exception as e:
            logger.error(f"Agent orchestration error: {e}", exc_info=True)
            return {
                "response": f"Oops, my styling brain is a bit tangled ({str(e)}). Can you repeat that?", 
                "images": [], 
                "suggested_outfits": []
            }

    def _parse_agent_response(self, text: str) -> Dict[str, Any]:
        """Robustly extracts and parses JSON from the agent's response."""
        text = text.strip()
        try:
            # Look for code blocks first
            json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if not json_match:
                json_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
            
            if json_match:
                content_to_parse = json_match.group(1).strip()
            else:
                # Fallback: Extract everything between first { and last }
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    content_to_parse = text[start:end+1]
                else:
                    content_to_parse = text

            parsed = json.loads(content_to_parse)
            if "response" not in parsed:
                parsed["response"] = text
            return parsed
        except Exception as e:
            logger.warning(f"Failed to parse agent JSON: {e}")
            return {
                "response": text,
                "images": [],
                "suggested_outfits": []
            }

agent_orchestrator = AgentOrchestrator()

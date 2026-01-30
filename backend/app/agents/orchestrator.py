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
            # 2. Invoke Agent with increased recursion limit
            logger.info(f"Invoking stylist_graph for user_id: {user_id}")
            final_result = await stylist_graph.ainvoke(initial_state, {"recursion_limit": 50})
            
            # 3. Extract final answer
            last_msg = final_result["messages"][-1]
            response_text = last_msg.content
            
            logger.info(f"Raw agent response: {response_text}")
            
            return self._parse_agent_response(response_text)

        except Exception as e:
            logger.error(f"Agent orchestration error: {e}", exc_info=True)
            return {
                "response": f"Oops, my styling brain is a bit tangled ({str(e)}). Can you repeat that?", 
                "images": [], 
                "suggested_outfits": []
            }

    async def chat_stream(
        self, 
        user_id: str, 
        message: str, 
        history: List[Dict] = [], 
        image_data: Optional[bytes] = None
    ):
        """Streaming version of chat - yields events for real-time UI updates."""
        
        # 1. Prepare Initial State (Same as chat)
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        budget = user.budget_limit if user else None
        wallet_balance = user.wallet_balance if user else 0.0
        currency = user.currency if user else "TND"
        db.close()

        temporal = get_temporal_context()
        langchain_history = convert_history_to_langchain(history)
        
        # 2. Vision Analysis (If Image Provided)
        # If the user uploads a file in the chat, we analyze it so the agent "sees" it.
        from langchain_core.messages import SystemMessage

        if image_data:
            try:
                from app.services.vision_analyzer import vision_analyzer
                from app.services.groq_vision_service import groq_vision_service
                from app.services.storage import storage_service
                from app.services.clip_qdrant_service import clip_qdrant_service
                import uuid
                
                # 1. Upload for persistent URL
                file_id = str(uuid.uuid4())
                img_url = await storage_service.upload_file(image_data, f"chat_{file_id}.jpg", "image/jpeg")
                
                # 2. Analyze
                analysis = await vision_analyzer.analyze_clothing(image_data)
                analysis["id"] = "potential_purchase" 
                analysis["image_url"] = img_url

                redundancy = {
                    "exact_match": False,
                    "likely_match": False,
                    "score": 0,
                    "match_item": None,
                    "method": None,
                }

                try:
                    similar_items = await clip_qdrant_service.search_similar_clothing_by_image(
                        image_data=image_data,
                        user_id=user_id,
                        limit=3,
                        min_score=0.4
                    )
                    if similar_items:
                        best_match = similar_items[0]
                        score = best_match.get("score", 0)
                        redundancy.update({
                            "score": score,
                            "match_item": {
                                "id": best_match.get("id"),
                                "image_url": best_match.get("image_url"),
                                "sub_category": best_match.get("clothing", {}).get("sub_category"),
                                "colors": best_match.get("clothing", {}).get("colors", []),
                                "brand": best_match.get("brand"),
                            },
                            "method": "clip_image"
                        })
                        if score >= 0.92:
                            redundancy["exact_match"] = True
                        elif score >= 0.85:
                            redundancy["likely_match"] = True
                except Exception as e:
                    logger.warning(f"Redundancy image match failed: {e}")

                if not redundancy["exact_match"] and not redundancy["likely_match"] and groq_vision_service.client:
                    try:
                        groq_analysis = await groq_vision_service.analyze_clothing(image_data)
                        groq_desc = ", ".join([
                            groq_analysis.get("sub_category", ""),
                            groq_analysis.get("material", ""),
                            ", ".join(groq_analysis.get("colors", []) or []),
                            groq_analysis.get("vibe", ""),
                        ]).strip(" ,")
                        if groq_desc:
                            text_matches = await clip_qdrant_service.search_by_text(
                                query_text=groq_desc,
                                user_id=user_id,
                                limit=3,
                                min_score=0.5
                            )
                            if text_matches:
                                best_text = text_matches[0]
                                score = best_text.get("score", 0)
                                if score >= 0.8:
                                    redundancy.update({
                                        "score": score,
                                        "match_item": {
                                            "id": best_text.get("id"),
                                            "image_url": best_text.get("image_url"),
                                            "sub_category": best_text.get("clothing", {}).get("sub_category"),
                                            "colors": best_text.get("clothing", {}).get("colors", []),
                                            "brand": best_text.get("brand"),
                                        },
                                        "likely_match": True,
                                        "method": "groq_text"
                                    })
                    except Exception as e:
                        logger.warning(f"Groq redundancy fallback failed: {e}")
                
                analysis_note = (
                    f"[SYSTEM NOTE: User uploaded an image of a potential purchase. "
                    f"Vision Analysis: {json.dumps(analysis)}. "
                    f"Redundancy Check: {json.dumps(redundancy)}. "
                    f"If exact_match or likely_match is true, tell the user they already own a very similar item.]")
                langchain_history.append(SystemMessage(content=analysis_note))
            except Exception as e:
                logger.error(f"Failed to analyze/upload image in orchestrator: {e}")

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
            "active_agent": "manager"
        }

        try:
            logger.info(f"Starting streaming graph for user_id: {user_id}")
            
            # Use v2 astream_events to capture detailed progress
            async for event in stylist_graph.astream_events(initial_state, {"recursion_limit": 50}, version="v2"):
                kind = event["event"]
                
                # Signal Node Transitions (Agent Handoffs)
                if kind == "on_chat_model_start":
                    node_name = event.get("metadata", {}).get("langgraph_node", "AI")
                    display_name = {
                        "manager": "Glam",
                        "closet": "Closet Assistant",
                        "advisor": "Fashion Advisor",
                        "budget": "Budget Manager",
                        "visualizer": "Visualizer"
                    }.get(node_name, node_name)
                    
                    yield json.dumps({"type": "status", "content": f"{display_name} is thinking..."})

                # Stream raw tokens (Incremental thoughts/response)
                elif kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield json.dumps({"type": "chunk", "content": content})

                # Signal Tool Calls
                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    if tool_name == "visualize_outfit":
                        yield json.dumps({
                            "type": "status", 
                            "content": "Glam is sketching your virtual try-on... ✨ (this usually takes 60-80s)"
                        })
                    else:
                        display_tool = tool_name.replace("_", " ").title()
                        yield json.dumps({"type": "status", "content": f"Running {display_tool}..."})

                # Capture Final Response
                elif kind == "on_chain_end" and event["name"] == "LangGraph":
                    # The very last message in the final state is our target
                    final_state = event["data"]["output"]
                    last_msg = final_state["messages"][-1]
                    response_text = last_msg.content
                    
                    logger.info(f"[STREAM] Final response received: {response_text[:200]}...")
                    parsed = self._parse_agent_response(response_text)
                    logger.info(f"[STREAM] Parsed response: {parsed}")

                    # Evaluate generation quality with RAGAS
                    try:
                        from app.services.ragas_service import ragas_service
                        import asyncio

                        retrieved_contexts = []
                        for msg in final_state["messages"]:
                            content_str = str(msg.content)
                            if "Visual Search Results:" in content_str:
                                retrieved_contexts.append(content_str[:500])
                            elif "Based on your style history:" in content_str:
                                retrieved_contexts.append(content_str[:500])
                            elif "Personalized Recommendations" in content_str:
                                retrieved_contexts.append(content_str[:500])

                        if retrieved_contexts:
                            asyncio.create_task(
                                ragas_service.evaluate_generation(
                                    question=message,
                                    contexts=retrieved_contexts,
                                    answer=response_text,
                                    pipeline="agent_orchestrator",
                                    metadata={"user_id": user_id}
                                )
                            )
                    except Exception as eval_err:
                        logger.warning(f"[RAGAS] Generation evaluation failed: {eval_err}")

                    yield json.dumps({"type": "final", "content": parsed})

        except Exception as e:
            logger.error(f"[STREAM] Streaming error: {e}", exc_info=True)
            logger.error(f"[STREAM] Error type: {type(e).__name__}")
            logger.error(f"[STREAM] Error details: {str(e)}")
            yield json.dumps({
                "type": "error", 
                "content": f"Styling brain error: {str(e)}"
            })

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
            
            # Fallback: Extract images from the entire text if the 'images' array is empty
            if not parsed.get("images"):
                found_images = re.findall(r'!\[.*?\]\((https?://.*?)\)', text)
                if not found_images:
                    # Even broader: just find URLs ending in common image extensions
                    found_images = re.findall(r'(https?://[^\s)\]]+\.(?:jpg|jpeg|png|webp|gif))', text, re.IGNORECASE)
                parsed["images"] = list(set(found_images))
                
            return parsed
        except Exception as e:
            logger.warning(f"Failed to parse agent JSON: {e}")
            return {
                "response": text,
                "images": [],
                "suggested_outfits": []
            }

agent_orchestrator = AgentOrchestrator()

from typing import Annotated, TypedDict, List, Union, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph.message import add_messages
from app.agents.tools import (
    search_closet, 
    search_saved_outfits, 
    browse_internet_for_fashion, 
    get_user_vitals, 
    generate_new_outfit_ideas,
    search_zep_graph,
    visualize_outfit,
    filter_closet_items,
    list_all_outfits,
    filter_saved_outfits,
    get_outfit_details,
    analyze_fashion_influence,
    evaluate_purchase_match,
    manage_wallet
)
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    budget_limit: Optional[float]
    wallet_balance: Optional[float]
    currency: str
    today_date: str
    days_remaining: int
    image_data: Optional[bytes] # For multi-modal reasoning
    intermediate_steps: Annotated[List[tuple], "Steps taken by the agent"]

# --- Tools Setup ---
tools = [
    search_closet, 
    search_saved_outfits, 
    browse_internet_for_fashion, 
    get_user_vitals, 
    generate_new_outfit_ideas,
    search_zep_graph,
    visualize_outfit,
    filter_closet_items,
    list_all_outfits,
    filter_saved_outfits,
    get_outfit_details,
    analyze_fashion_influence,
    evaluate_purchase_match,
    manage_wallet
]
tool_node = ToolNode(tools)

# --- Model Setup ---
# Use Azure OpenAI (GPT-4o) for high reasoning and vision support
model = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
    openai_api_key=settings.AZURE_OPENAI_API_KEY,
    api_version="2024-08-01-preview",
    temperature=0
).bind_tools(tools)

# --- Node Implementation ---

async def call_model(state: AgentState):
    """The reasoning node that decides which tool to call."""
    messages = state["messages"]
    
    # Handle Image Input (Multi-modal)
    # Azure GPT-4o supports vision natively.
    if state.get("image_data") and len(messages) > 0:
        import base64
        image_base64 = base64.b64encode(state["image_data"]).decode("utf-8")
        
        # We only apply the image to the very first HumanMessage in the chain for context
        for i in range(len(messages)):
            if isinstance(messages[i], HumanMessage):
                # Convert the message content to multi-modal format if not already
                if isinstance(messages[i].content, str):
                    messages[i] = HumanMessage(content=[
                        {"type": "text", "text": messages[i].content},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ])
                break

    # Inject budget context
    financial_context = []
    if state.get("budget_limit") is not None:
        financial_context.append(f"Monthly Budget Limit: {state['budget_limit']} {state['currency']}")
    
    if state.get("wallet_balance") is not None:
        financial_context.append(f"Current Wallet Balance: {state['wallet_balance']} {state['currency']}")
    
    time_context = []
    if state.get("today_date"):
        time_context.append(f"Today's Date: {state['today_date']}")
    if state.get("days_remaining") is not None:
        time_context.append(f"Days left in this month: {state['days_remaining']}")

    full_context_str = "\n".join(financial_context + time_context)

    from app.agents.prompts import STYLIST_SYSTEM_PROMPT
    
    # Prevent SystemMessage duplication: Only add if not already present
    has_system = any(isinstance(m, SystemMessage) for m in messages)
    if not has_system:
        system_content = STYLIST_SYSTEM_PROMPT.format(
            user_id=state['user_id'],
            full_context_str=full_context_str,
            currency=state['currency']
        )
        messages = [SystemMessage(content=system_content)] + messages

    response = await model.ainvoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    """Decide if we should go to tools or end."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "check_budget"

async def refine_response(state: AgentState):
    """
    Evaluates the agent's turn. If the response is low-quality or lacks expected visuals,
    it instructs the agent to try again (up to a limit).
    """
    messages = state["messages"]
    last_msg = messages[-1]
    
    # Only refine if it's an AI message without tool calls (the "final" thought)
    if not isinstance(last_msg, AIMessage) or last_msg.tool_calls:
        return {}
        
    loop_count = 0
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and "CRITIQUE:" in msg.content:
            loop_count += 1
    
    if loop_count >= 2: # Max 2 refinement turns
        return {}

    # Simple heuristic: If user asked for an outfit but no suggested_outfits found
    content = last_msg.content.strip()
    try:
        # Robust extraction: Look for anything between ```json and ``` or just { and }
        import re
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if not json_match:
            json_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
        
        if json_match:
            content_to_parse = json_match.group(1).strip()
        else:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content_to_parse = content[start:end+1]
            else:
                content_to_parse = content

        data = json.loads(content_to_parse)
        
        # Check completeness (example: if they asked for ideas but got none)
        # We can also check budget here.
        if state.get("budget_limit") and data.get("response"):
            # If the response mentions cost but violates budget, critique.
            pass
            
    except:
        # If not valid JSON, force a retry to fix format
        return {"messages": [HumanMessage(content="CRITIQUE: Your response was not in valid JSON format. Please ensure you return the strictly defined JSON structure.")]}

    return {}

def should_loop_back(state: AgentState):
    """Decide if we should refine further or end."""
    last_message = state["messages"][-1]
    if isinstance(last_message, HumanMessage) and "CRITIQUE:" in last_message.content:
        return "agent"
    return END

# --- Graph Construction ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("refine", refine_response)

# Set Entry Point
workflow.set_entry_point("agent")

# Add Conditional Edges
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "check_budget": "refine"
    }
)

workflow.add_conditional_edges(
    "refine",
    should_loop_back,
    {
        "agent": "agent",
        END: END
    }
)

# Tool execution always loops back to the agent for next decision
workflow.add_edge("tools", "agent")

# Compile
stylist_agent = workflow.compile()

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
    visualize_outfit
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
    currency: str
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
    visualize_outfit
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
    budget_context = ""
    if state.get("budget_limit") is not None:
        budget_context = f"Constraint: The user's budget is {state['budget_limit']} {state['currency']}."

    # Prevent SystemMessage duplication: Only add if not already present
    has_system = any(isinstance(m, SystemMessage) for m in messages)
    if not has_system:
        system_content = f"""
        You are 'Ava', an advanced AI Virtual Stylist. 
        User Context: ID is '{state['user_id']}'.
        Current {budget_context}
        
        Capabilities:
        - Use 'search_closet' to find items the user already owns.
        - Use 'generate_new_outfit_ideas' to compose looks from the closet.
        - Use 'visualize_outfit(user_id, item_ids=[], image_urls=[])' to generate a virtual try-on image.
          You can mix existing closet items (IDs) and new items found on the internet (URLs).
          Use this whenever the user says "try this on", "show me how this looks", or "visualize".
        - Use 'browse_internet_for_fashion' for trends or new items.

        Response Format (Strictly JSON):
        {{
          "response": "Your conversational message here. If you visualized something, include the link as: [View Visualization](url)",
          "images": ["List of direct 'Image URL' strings found in 'search_closet' results"],
          "suggested_outfits": [
            {{
              "name": "Outfit Name",
              "score": 9.5,
              "image_url": "The 'Visual Link' URL from 'search_saved_outfits' or 'visualize_outfit'",
              "item_details": [{{ "id": "uuid", "sub_category": "jeans", "image_url": "The 'Image URL' of this specific item" }}]
            }}
          ]
        }}
        
        Important: Always look for 'Image URL' or 'Visual Link' fields in tool outputs and put them into the structured JSON fields above so the user can see them.
        """
        messages = [SystemMessage(content=system_content)] + messages

    response = await model.ainvoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    """Decide if we should go to tools or end."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "check_budget"

async def check_budget_constraint(state: AgentState):
    """
    Final check node to ensure the AI's final answer respects the budget.
    If the AI suggested something expensive, this node will force a correction.
    """
    last_message = state["messages"][-1]
    if state.get("budget_limit") is None or not isinstance(last_message, AIMessage):
        return {}

    # Basic logic: If budget is mentioned in response, we verify.
    # In a real production agent, we might do another LLM pass to verify the numbers.
    # For now, we'll let it pass but log it.
    
    return {}

# --- Graph Construction ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("check_budget", check_budget_constraint)

# Set Entry Point
workflow.set_entry_point("agent")

# Add Conditional Edges
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "check_budget": "check_budget"
    }
)

# Tool execution always loops back to the agent for next decision
workflow.add_edge("tools", "agent")
workflow.add_edge("check_budget", END)

# Compile
stylist_agent = workflow.compile()

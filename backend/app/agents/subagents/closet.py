from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.config import settings
from app.agents.state import AgentState
from app.agents.prompts.closet import CLOSET_SYSTEM_PROMPT
from app.agents.tools_sets.closet_tools import (
    search_closet, filter_closet_items, list_all_outfits, 
    get_outfit_details, generate_new_outfit_ideas
)
from app.agents.tools_sets.handoff_tools import transfer_back_to_manager

closet_tools = [
    search_closet, filter_closet_items, list_all_outfits, 
    get_outfit_details, generate_new_outfit_ideas, transfer_back_to_manager
]

model = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
    openai_api_key=settings.AZURE_OPENAI_API_KEY,
    api_version="2024-08-01-preview",
    temperature=0
).bind_tools(closet_tools)

async def closet_node(state: AgentState):
    """Closet Assistant Node."""
    messages = state["messages"]
    # We strip previous system messages to keep it focused
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    messages = [SystemMessage(content=CLOSET_SYSTEM_PROMPT)] + filtered_messages
    
    response = await model.ainvoke(messages)
    return {"messages": [response], "active_agent": "closet"}

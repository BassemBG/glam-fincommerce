from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.config import settings
from app.agents.state import AgentState
from app.agents.prompts.closet import CLOSET_SYSTEM_PROMPT
from app.agents.tools_sets.closet_tools import (
    search_closet, filter_closet_items, list_all_outfits, 
    get_outfit_details, generate_new_outfit_ideas, search_saved_outfits, filter_saved_outfits
)
from app.agents.tools_sets.handoff_tools import transfer_back_to_manager

closet_tools = [
    search_closet, filter_closet_items, list_all_outfits, 
    get_outfit_details, generate_new_outfit_ideas, search_saved_outfits, filter_saved_outfits, transfer_back_to_manager
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
    print(f"\n[NODE] --- CLOSET ASSISTANT ---")
    messages = state["messages"]
    # We strip previous system messages to keep it focused
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    formatted_prompt = CLOSET_SYSTEM_PROMPT.format(user_id=state["user_id"])
    messages = [SystemMessage(content=formatted_prompt)] + filtered_messages
    
    print(f"[CLOSET] Last user message: {filtered_messages[-1].content if filtered_messages else 'None'}")
    
    # Identify as 'closet_assistant'
    response = await model.ainvoke(messages)
    response.name = "closet_assistant"
    
    # Log what tools the assistant is calling
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"[CLOSET] Tool calls: {[tc['name'] for tc in response.tool_calls]}")
    else:
        print(f"[CLOSET] No tool calls, response: {response.content[:100] if response.content else 'Empty'}")
    
    return {"messages": [response], "active_agent": "closet"}

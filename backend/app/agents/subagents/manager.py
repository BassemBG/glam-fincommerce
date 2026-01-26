from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.config import settings
from app.agents.state import AgentState
from app.agents.prompts.manager import MANAGER_SYSTEM_PROMPT
from app.agents.tools_sets.handoff_tools import (
    transfer_to_closet, transfer_to_advisor, transfer_to_budget, transfer_to_visualizer
)
from app.agents.tools_sets.common_tools import get_user_vitals

manager_tools = [
    get_user_vitals, transfer_to_closet, transfer_to_advisor, 
    transfer_to_budget, transfer_to_visualizer
]

model = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
    openai_api_key=settings.AZURE_OPENAI_API_KEY,
    api_version="2024-08-01-preview",
    temperature=0
).bind_tools(manager_tools)

async def manager_node(state: AgentState):
    """The Manager (Ava) hub node."""
    messages = state["messages"]
    
    # Simple check for system message
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=MANAGER_SYSTEM_PROMPT)] + messages
        
    response = await model.ainvoke(messages)
    return {"messages": [response], "active_agent": "manager"}

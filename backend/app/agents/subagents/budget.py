from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.config import settings
from app.agents.state import AgentState
from app.agents.prompts.budget import BUDGET_SYSTEM_PROMPT
from app.agents.tools_sets.budget_tools import manage_wallet
from app.agents.tools_sets.handoff_tools import transfer_back_to_manager

budget_tools = [manage_wallet, transfer_back_to_manager]

model = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
    openai_api_key=settings.AZURE_OPENAI_API_KEY,
    api_version="2024-08-01-preview",
    temperature=0
).bind_tools(budget_tools)

async def budget_node(state: AgentState):
    """Budget Manager Node."""
    messages = state["messages"]
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    messages = [SystemMessage(content=BUDGET_SYSTEM_PROMPT)] + filtered_messages
    
    response = await model.ainvoke(messages)
    return {"messages": [response], "active_agent": "budget"}

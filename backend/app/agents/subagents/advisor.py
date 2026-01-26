from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.config import settings
from app.agents.state import AgentState
from app.agents.prompts.advisor import ADVISOR_SYSTEM_PROMPT
from app.agents.tools_sets.advisor_tools import (
    browse_internet_for_fashion, search_zep_graph, 
    analyze_fashion_influence, evaluate_purchase_match
)
from app.agents.tools_sets.handoff_tools import transfer_back_to_manager

advisor_tools = [
    browse_internet_for_fashion, search_zep_graph, 
    analyze_fashion_influence, evaluate_purchase_match, transfer_back_to_manager
]

model = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
    openai_api_key=settings.AZURE_OPENAI_API_KEY,
    api_version="2024-08-01-preview",
    temperature=0
).bind_tools(advisor_tools)

async def advisor_node(state: AgentState):
    """Fashion Advisor Node."""
    print(f"\n[NODE] --- FASHION ADVISOR ---")
    messages = state["messages"]

    # Financial context from state
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
    
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    formatted_prompt = ADVISOR_SYSTEM_PROMPT.format(
        user_id=state.get("user_id", "Unknown"),
        full_context_str=full_context_str
    )
    messages = [SystemMessage(content=formatted_prompt)] + filtered_messages
    
    response = await model.ainvoke(messages)
    response.name = "fashion_advisor"
    return {"messages": [response], "active_agent": "advisor"}

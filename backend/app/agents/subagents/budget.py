from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.config import settings
from app.agents.state import AgentState
from app.agents.prompts.budget import BUDGET_SYSTEM_PROMPT
from app.agents.tools_sets.budget_tools import manage_wallet, convert_currency
from app.agents.tools_sets.handoff_tools import transfer_back_to_manager

budget_tools = [manage_wallet, convert_currency, transfer_back_to_manager]

model = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
    openai_api_key=settings.AZURE_OPENAI_API_KEY,
    api_version="2024-08-01-preview",
    temperature=0
).bind_tools(budget_tools)

async def budget_node(state: AgentState):
    """Budget Manager Node."""
    print(f"\n[NODE] --- BUDGET MANAGER ---")
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
    formatted_prompt = BUDGET_SYSTEM_PROMPT.format(
        user_id=state.get("user_id", "Unknown"),
        full_context_str=full_context_str
    )
    messages = [SystemMessage(content=formatted_prompt)] + filtered_messages
    
    response = await model.ainvoke(messages)
    response.name = "budget_manager"
    return {"messages": [response], "active_agent": "budget"}

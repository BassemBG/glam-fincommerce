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
    print(f"\n[NODE] --- MANAGER (AVA) ---")
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
    
    # Format the prompt with state data
    formatted_prompt = MANAGER_SYSTEM_PROMPT.format(
        user_id=state.get("user_id", "Unknown"),
        full_context_str=full_context_str
    )
    
    # Ensure system message is present and updated
    new_messages = []
    has_system = False
    for m in messages:
        if isinstance(m, SystemMessage):
            new_messages.append(SystemMessage(content=formatted_prompt))
            has_system = True
        else:
            # Add sender identification to AI messages in history if possible
            new_messages.append(m)
            
    if not has_system:
        new_messages = [SystemMessage(content=formatted_prompt)] + new_messages
        
    print(f"   (Active Agent in state: {state.get('active_agent')})")
    response = await model.ainvoke(new_messages)
    
    # We don't set a name for the Manager as she is the main interface
    return {"messages": [response], "active_agent": "manager"}

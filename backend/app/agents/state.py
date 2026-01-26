from typing import Annotated, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    State for the Multi-Agent Stylist Graph.
    """
    # Messages in the conversation (shared context)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User Context
    user_id: str
    budget_limit: Optional[float]
    wallet_balance: Optional[float]
    currency: str
    today_date: str
    days_remaining: int
    
    # Optional image data for multi-modal reasoning
    image_data: Optional[bytes]
    
    # Tracking handoffs and execution path
    handoff_history: Annotated[List[str], add_messages]
    active_agent: str
    
    # Specialized outputs from sub-agents
    intermediate_steps: Annotated[List[tuple], "Steps taken by the agents"]

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.config import settings
from app.agents.state import AgentState
from app.agents.prompts.visualizer import VISUALIZER_SYSTEM_PROMPT
from app.agents.tools_sets.visual_tools import visualize_outfit
from app.agents.tools_sets.handoff_tools import transfer_back_to_manager

visual_tools = [visualize_outfit, transfer_back_to_manager]

model = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
    openai_api_key=settings.AZURE_OPENAI_API_KEY,
    api_version="2024-08-01-preview",
    temperature=0
).bind_tools(visual_tools)

async def visualizer_node(state: AgentState):
    """Visualizer Node."""
    print(f"\n[NODE] --- VISUALIZER ---")
    messages = state["messages"]
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    messages = [SystemMessage(content=VISUALIZER_SYSTEM_PROMPT)] + filtered_messages
    
    response = await model.ainvoke(messages)
    return {"messages": [response], "active_agent": "visualizer"}

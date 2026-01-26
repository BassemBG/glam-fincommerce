from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage

# Import State
from app.agents.state import AgentState

# Import Nodes
from app.agents.subagents.manager import manager_node, manager_tools
from app.agents.subagents.closet import closet_node, closet_tools
from app.agents.subagents.advisor import advisor_node, advisor_tools
from app.agents.subagents.budget import budget_node, budget_tools
from app.agents.subagents.visualizer import visualizer_node, visual_tools

# --- Tool Nodes ---
# Each agent has its own tool node to maintain isolation
manager_tool_node = ToolNode(manager_tools)
closet_tool_node = ToolNode(closet_tools)
advisor_tool_node = ToolNode(advisor_tools)
budget_tool_node = ToolNode(budget_tools)
visual_tool_node = ToolNode(visual_tools)

# --- Routing Logic ---

def route_manager(state: AgentState):
    """Routes after Manager node."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "manager_tools"
    return END

def route_manager_tools(state: AgentState):
    """Decides which specialized agent to go to based on handoff tool result."""
    last_msg = state["messages"][-1] # This is the ToolMessage content
    content = last_msg.content
    
    if "TRANSFER_TO_CLOSET" in content: return "closet"
    if "TRANSFER_TO_ADVISOR" in content: return "advisor"
    if "TRANSFER_TO_BUDGET" in content: return "budget"
    if "TRANSFER_TO_VISUALIZER" in content: return "visualizer"
    
    # If it was just a regular tool like get_user_vitals, go back to manager for next thought
    return "manager"

def route_subagent(state: AgentState):
    """Routes after a specialized agent node."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        # Specialized agent might want to call its own tools
        active = state.get("active_agent")
        return f"{active}_tools"
    return "manager" # Default: return to manager

def route_subagent_tools(state: AgentState):
    """Routes after a specialized tool is called."""
    last_msg = state["messages"][-1]
    if "TRANSFER_BACK_TO_MANAGER" in last_msg.content:
        return "manager"
    # Otherwise, go back to the subagent to see if it has more to do
    return state.get("active_agent")

# --- Graph Assembly ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("manager", manager_node)
workflow.add_node("manager_tools", manager_tool_node)

workflow.add_node("closet", closet_node)
workflow.add_node("closet_tools", closet_tool_node)

workflow.add_node("advisor", advisor_node)
workflow.add_node("advisor_tools", advisor_tool_node)

workflow.add_node("budget", budget_node)
workflow.add_node("budget_tools", budget_tool_node)

workflow.add_node("visualizer", visualizer_node)
workflow.add_node("visualizer_tools", visual_tool_node)

# Entry Point
workflow.set_entry_point("manager")

# --- Edges ---

# Manager Flow
workflow.add_conditional_edges("manager", route_manager, {"manager_tools": "manager_tools", END: END})
workflow.add_conditional_edges("manager_tools", route_manager_tools, {
    "closet": "closet",
    "advisor": "advisor",
    "budget": "budget",
    "visualizer": "visualizer",
    "manager": "manager"
})

# Closet Flow
workflow.add_conditional_edges("closet", route_subagent, {"closet_tools": "closet_tools", "manager": "manager"})
workflow.add_conditional_edges("closet_tools", route_subagent_tools, {"manager": "manager", "closet": "closet"})

# Advisor Flow
workflow.add_conditional_edges("advisor", route_subagent, {"advisor_tools": "advisor_tools", "manager": "manager"})
workflow.add_conditional_edges("advisor_tools", route_subagent_tools, {"manager": "manager", "advisor": "advisor"})

# Budget Flow
workflow.add_conditional_edges("budget", route_subagent, {"budget_tools": "budget_tools", "manager": "manager"})
workflow.add_conditional_edges("budget_tools", route_subagent_tools, {"manager": "manager", "budget": "budget"})

# Visualizer Flow
workflow.add_conditional_edges("visualizer", route_subagent, {"visualizer_tools": "visualizer_tools", "manager": "manager"})
workflow.add_conditional_edges("visualizer_tools", route_subagent_tools, {"manager": "manager", "visualizer": "visualizer"})

# Compile
stylist_graph = workflow.compile()

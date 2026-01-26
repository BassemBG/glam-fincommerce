from langchain_core.tools import tool
from typing import Dict, Any

@tool
def transfer_to_closet(task: str) -> str:
    """Handoff to the Closet Assistant. Specify exactly what items or outfits to search for."""
    return f"TRANSFER_TO_CLOSET: {task}"

@tool
def transfer_to_advisor(task: str) -> str:
    """Handoff to the Fashion Advisor. Specify the trend, style question, or brand to research."""
    return f"TRANSFER_TO_ADVISOR: {task}"

@tool
def transfer_to_budget(task: str) -> str:
    """Handoff to the Budget Manager. Specify if checking balance or proposing a specific purchase."""
    return f"TRANSFER_TO_BUDGET: {task}"

@tool
def transfer_to_visualizer(task: str) -> str:
    """Handoff to the Visualizer. Specify exactly which items/urls to visualize together."""
    return f"TRANSFER_TO_VISUALIZER: {task}"

@tool
def transfer_back_to_manager() -> str:
    """Return control to the Manager (Ava) once your specialized task is complete."""
    return "TRANSFER_BACK_TO_MANAGER"

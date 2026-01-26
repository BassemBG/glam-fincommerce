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
def transfer_back_to_manager(summary: str, clarification_needed: str = "") -> str:
    """
    Return control to Glam (the Manager). 
    - summary: A detailed report of what you found or did.
    - clarification_needed: Use this ONLY if you are blocked because you are missing info (like price, color preference, etc.). 
      State exactly what the user needs to provide.
    """
    if clarification_needed:
        return f"TRANSFER_BACK_TO_MANAGER | BLOCKED: {clarification_needed} | SUMMARY: {summary}"
    return f"TRANSFER_BACK_TO_MANAGER | SUMMARY: {summary}"

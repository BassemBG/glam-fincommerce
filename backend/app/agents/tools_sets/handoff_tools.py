from langchain_core.tools import tool
from typing import Dict, Any

@tool
def transfer_to_closet() -> str:
    """Handoff to the Closet Assistant for inventory, outfits, and wardrobe questions."""
    return "TRANSFER_TO_CLOSET"

@tool
def transfer_to_advisor() -> str:
    """Handoff to the Fashion Advisor for trends, internet search, and style matching."""
    return "TRANSFER_TO_ADVISOR"

@tool
def transfer_to_budget() -> str:
    """Handoff to the Budget Manager for wallet, balance, and purchase confirmation."""
    return "TRANSFER_TO_BUDGET"

@tool
def transfer_to_visualizer() -> str:
    """Handoff to the Visualizer for try-ons and image generation."""
    return "TRANSFER_TO_VISUALIZER"

@tool
def transfer_back_to_manager() -> str:
    """Return control to the Manager (Ava) once your specialized task is complete."""
    return "TRANSFER_BACK_TO_MANAGER"

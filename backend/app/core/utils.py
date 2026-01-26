from datetime import datetime
import calendar
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage

def get_temporal_context() -> Dict[str, Any]:
    """Calculates current date and days remaining in the month."""
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    _, last_day = calendar.monthrange(now.year, now.month)
    days_remaining = last_day - now.day
    return {
        "today_date": today_date,
        "days_remaining": days_remaining
    }

def convert_history_to_langchain(history: List[Dict[str, str]]) -> List[Any]:
    """Converts simple history list to LangChain message objects."""
    langchain_history = []
    for msg in history:
        if msg.get("role") == "user":
            langchain_history.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant" or msg.get("role") == "ai":
            langchain_history.append(AIMessage(content=msg.get("content", "")))
    return langchain_history
